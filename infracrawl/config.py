import os
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

try:
	from dotenv import load_dotenv
except ImportError:
	logger.warning("python-dotenv not available; using environment variables only")
else:
	loaded = load_dotenv()
	if not loaded and Path(".env").exists():
		raise RuntimeError(".env file present but failed to load")


def get_str_env(name: str, default: str) -> str:
	raw = os.getenv(name)
	if raw is None:
		return default
	return raw


def get_optional_str_env(name: str) -> Optional[str]:
	raw = os.getenv(name)
	if raw is None or raw == "":
		return None
	return raw


def get_int_env(name: str, default: int) -> int:
	raw = os.getenv(name)
	if raw is None or raw == "":
		return default
	try:
		return int(raw)
	except Exception:
		logger.exception("Invalid %s: %r", name, raw)
		return default


def get_float_env(name: str, default: float) -> float:
	raw = os.getenv(name)
	if raw is None or raw == "":
		return default
	try:
		return float(raw)
	except Exception:
		logger.exception("Invalid %s: %r", name, raw)
		return default


def get_optional_int_env(name: str) -> Optional[int]:
	raw = os.getenv(name)
	if raw is None or raw == "":
		return None
	try:
		return int(raw)
	except Exception:
		logger.exception("Invalid %s: %r", name, raw)
		return None
