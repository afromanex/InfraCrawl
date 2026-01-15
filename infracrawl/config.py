import os
import logging
from pathlib import Path
from typing import Optional

try:
	from dotenv import load_dotenv
except ImportError:
	logging.warning("python-dotenv not available; using environment variables only")
else:
	loaded = load_dotenv()
	if not loaded and Path(".env").exists():
		raise RuntimeError(".env file present but failed to load")

DATABASE_URL = os.getenv("DATABASE_URL")
USER_AGENT = os.getenv("USER_AGENT", "InfraCrawl/0.1")
CRAWL_DELAY = float(os.getenv("CRAWL_DELAY", "1"))
DEFAULT_DEPTH = int(os.getenv("DEFAULT_DEPTH", "2"))


def _get_int_env(name: str, default: int) -> int:
	raw = os.getenv(name)
	if raw is None or raw == "":
		return default
	try:
		return int(raw)
	except Exception:
		logging.exception("Invalid %s: %r", name, raw)
		return default


def _get_optional_int_env(name: str) -> Optional[int]:
	raw = os.getenv(name)
	if raw is None or raw == "":
		return None
	try:
		return int(raw)
	except Exception:
		logging.exception("Invalid %s: %r", name, raw)
		return None


def scheduler_config_watch_interval_seconds() -> int:
	return _get_int_env("INFRACRAWL_CONFIG_WATCH_INTERVAL", 60)


def recovery_mode() -> str:
	return (os.getenv("INFRACRAWL_RECOVERY_MODE", "restart") or "restart").strip().lower()


def recovery_within_seconds() -> Optional[int]:
	return _get_optional_int_env("INFRACRAWL_RECOVERY_WITHIN_SECONDS")


def recovery_message() -> str:
	return os.getenv("INFRACRAWL_RECOVERY_MESSAGE", "job found incomplete on startup")
