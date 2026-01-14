from typing import Optional
import json

from fastapi import APIRouter, HTTPException, BackgroundTasks
from starlette.responses import StreamingResponse
from pydantic import BaseModel

from infracrawl.services.config_service import ConfigService
from infracrawl.services.crawl_registry import InMemoryCrawlRegistry
from infracrawl.repository.crawls import CrawlsRepository


class CrawlRequest(BaseModel):
    config: str


class ReloadRequest(BaseModel):
    config: str


class RemoveRequest(BaseModel):
    config: str


class CrawlersRouter:
    """Router class for crawler control endpoints.
    
    Encapsulates dependencies and endpoint logic, avoiding closure-based function factory.
    """
    # TODO: OCP - CrawlersRouter instantiates CrawlsRepository() directly in __init__. Concrete risk: cannot inject test/mock repo; couples router to production DB. Minimal fix: accept crawls_repo parameter in __init__ with default=None; set self.crawls_repo = crawls_repo or CrawlsRepository().
    # RESPONSE: Repository should be injected. 
    
    def __init__(self, pages_repo, links_repo, config_service: ConfigService,
                 start_crawl_callback, crawl_registry: Optional[InMemoryCrawlRegistry] = None):
        self.pages_repo = pages_repo
        self.links_repo = links_repo
        self.config_service = config_service
        self.start_crawl_callback = start_crawl_callback
        self.crawl_registry = crawl_registry
        self.crawls_repo = CrawlsRepository()
    
    def create_router(self) -> APIRouter:
        """Create and configure the FastAPI router with all endpoints."""
        router = APIRouter(prefix="/crawlers", tags=["Crawlers"])
        
        router.add_api_route(
            "/export",
            self.export,
            methods=["GET"],
            responses={
                200: {
                    "content": {
                        "application/x-ndjson": {
                            "schema": {"type": "string", "format": "binary"}
                        }
                    },
                    "description": "NDJSON stream (one JSON object per line)"
                }
            }
        )
        router.add_api_route("/crawl", self.crawl, methods=["POST"], status_code=202)
        router.add_api_route("/active", self.list_active_crawls, methods=["GET"])
        router.add_api_route("/active/{crawl_id}", self.get_crawl, methods=["GET"])
        router.add_api_route("/cancel/{crawl_id}", self.cancel_crawl, methods=["POST"])
        router.add_api_route("/remove", self.remove, methods=["DELETE"])
        router.add_api_route("/runs", self.list_runs, methods=["GET"])
        
        return router
    
    def export(self, config: Optional[str] = None, limit: Optional[int] = None):
        config_id = None
        if config:
            cfg = self.config_service.get_config(config)
            if not cfg:
                raise HTTPException(status_code=404, detail="config not found")
            config_id = cfg.config_id
        pages = self.pages_repo.fetch_pages(full=True, limit=limit, config_id=config_id)

        def gen_ndjson():
            for p in pages:
                yield (json.dumps(p.__dict__, default=str) + "\n").encode("utf-8")

        return StreamingResponse(gen_ndjson(), media_type="application/x-ndjson")
    
    def crawl(self, req: CrawlRequest, background_tasks: BackgroundTasks):
        if not req.config:
            raise HTTPException(status_code=400, detail="missing config")
        cfg = self.config_service.get_config(req.config)
        if not cfg:
            raise HTTPException(status_code=404, detail="config not found")
        
        crawl_id = None
        if self.crawl_registry is not None:
            crawl_id = self.crawl_registry.start(config_name=cfg.config_path, config_id=cfg.config_id)

        stop_event = self.crawl_registry.get_stop_event(crawl_id) if self.crawl_registry is not None else None

        run_id = None
        try:
            run_id = self.crawls_repo.create_run(cfg.config_id)
        except Exception:
            import logging
            logging.exception("Could not create crawl run record")

        def _run_and_track(cfg, cid=None, stop_event=None, run_id=None):
            try:
                # TODO: Clever ternary with conditional call - just use simple if/else: if stop_event: callback(cfg, stop_event) else: callback(cfg)
                self.start_crawl_callback(cfg, stop_event) if stop_event is not None else self.start_crawl_callback(cfg)
                if cid and self.crawl_registry is not None:
                    self.crawl_registry.finish(cid, status="finished")
                if run_id is not None:
                    try:
                        self.crawls_repo.finish_run(run_id)
                    except Exception:
                        import logging
                        logging.exception("Could not finish crawl run record")
            except Exception as e:
                if cid and self.crawl_registry is not None:
                    self.crawl_registry.finish(cid, status="failed", error=str(e))
                if run_id is not None:
                    try:
                        self.crawls_repo.finish_run(run_id, exception=str(e))
                    except Exception:
                        import logging
                        logging.exception("Could not finish crawl run record (failed)")
                raise

        background_tasks.add_task(_run_and_track, cfg, crawl_id, stop_event, run_id)
        return {"status": "started", "crawl_id": crawl_id, "run_id": run_id}
    
    def list_active_crawls(self):
        if self.crawl_registry is None:
            return {"active": []}
        return {"active": self.crawl_registry.list_active()}
    
    def get_crawl(self, crawl_id: str):
        if self.crawl_registry is None:
            raise HTTPException(status_code=404, detail="no registry configured")
        rec = self.crawl_registry.get(crawl_id)
        if not rec:
            raise HTTPException(status_code=404, detail="crawl not found")
        return rec
    
    def cancel_crawl(self, crawl_id: str):
        if self.crawl_registry is None:
            raise HTTPException(status_code=404, detail="no registry configured")
        ok = self.crawl_registry.cancel(crawl_id)
        if not ok:
            raise HTTPException(status_code=404, detail="crawl not found or cannot cancel")
        return {"status": "cancelling", "crawl_id": crawl_id}
    
    def remove(self, req: RemoveRequest):
        config_name = req.config
        if not config_name:
            raise HTTPException(status_code=400, detail="missing config")

        cfg = self.config_service.get_config(config_name)
        if not cfg:
            raise HTTPException(status_code=404, detail="config not found")

        try:
            page_ids = self.pages_repo.get_page_ids_by_config(cfg.config_id)
            deleted_links = 0
            deleted_pages = 0
            if page_ids:
                deleted_links = self.links_repo.delete_links_for_page_ids(page_ids)
                deleted_pages = self.pages_repo.delete_pages_by_ids(page_ids)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"error removing data: {e}")

        return {"status": "removed", "deleted_pages": deleted_pages, "deleted_links": deleted_links}
    
    def list_runs(self, limit: Optional[int] = 20):
        """Return the last `limit` crawl runs (most recent first)."""
        try:
            runs = self.crawls_repo.list_runs(limit=limit)
        except Exception:
            raise HTTPException(status_code=500, detail="could not list runs")

        def r_to_dict(r):
            return {
                "run_id": r.run_id,
                "config_id": r.config_id,
                "config_path": r.config_path,
                "start_timestamp": r.start_timestamp,
                "end_timestamp": r.end_timestamp,
                "exception": r.exception,
            }

        return [r_to_dict(r) for r in runs]


def create_crawlers_router(pages_repo, links_repo, config_service: ConfigService, start_crawl_callback, crawl_registry: InMemoryCrawlRegistry = None) -> APIRouter:
    """Factory function to create crawlers router for backwards compatibility."""
    router_instance = CrawlersRouter(pages_repo, links_repo, config_service, start_crawl_callback, crawl_registry)
    return router_instance.create_router()
