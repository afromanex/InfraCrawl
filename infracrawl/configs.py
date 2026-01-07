import os
import yaml


def load_configs_from_dir(path: str | None = None):
    """Load YAML config files from `path` (default ./configs) and return list of dicts.

    Each config must contain:
      - name: string
      - root_urls: string or list of strings
      - max_depth: integer
    """
    base = path or os.path.join(os.getcwd(), "configs")
    configs = []
    if not os.path.isdir(base):
        return configs

    for fname in os.listdir(base):
        if not (fname.endswith(".yml") or fname.endswith(".yaml")):
            continue
        full = os.path.join(base, fname)
        try:
            with open(full, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except Exception:
            continue
        if not data:
            continue
        name = data.get("name")
        root_urls = data.get("root_urls")
        max_depth = data.get("max_depth")
        robots = data.get("robots", True)
        refresh_days = data.get("refresh_days")
        if not name or not root_urls or max_depth is None:
            continue
        if isinstance(root_urls, str):
            root_urls = [root_urls]
        cfg = {"name": name, "root_urls": root_urls, "max_depth": int(max_depth), "robots": bool(robots)}
        if refresh_days is not None:
            try:
                cfg["refresh_days"] = int(refresh_days)
            except Exception:
                cfg["refresh_days"] = None
        configs.append(cfg)

    return configs
