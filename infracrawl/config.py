import os
try:
	from dotenv import load_dotenv
	load_dotenv()
except Exception:
	# python-dotenv not installed in this environment; rely on environment variables
	import sys
	print("Warning: python-dotenv not available, using environment variables only", file=sys.stderr)
	pass

DATABASE_URL = os.getenv("DATABASE_URL")
USER_AGENT = os.getenv("USER_AGENT", "InfraCrawl/0.1")
CRAWL_DELAY = float(os.getenv("CRAWL_DELAY", "1"))
DEFAULT_DEPTH = int(os.getenv("DEFAULT_DEPTH", "2"))
