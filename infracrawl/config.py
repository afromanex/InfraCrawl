import os
import logging
from pathlib import Path

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
