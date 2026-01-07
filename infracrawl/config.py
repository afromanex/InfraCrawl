from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
USER_AGENT = os.getenv("USER_AGENT", "InfraCrawl/0.1")
CRAWL_DELAY = float(os.getenv("CRAWL_DELAY", "1"))
DEFAULT_DEPTH = int(os.getenv("DEFAULT_DEPTH", "2"))
