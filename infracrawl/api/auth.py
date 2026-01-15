import os
import logging
import secrets
from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

logger = logging.getLogger(__name__)

# Simple HTTP Bearer token auth for admin operations.
# Set ADMIN_TOKEN env var to enable.
# SECURITY: No ADMIN_TOKEN must fail-closed (deny by default).
# Set ADMIN_TOKEN="your-secret-token" in env.
# TODO: Single static token - no expiration, no rotation, no user attribution
# CLAUDE: Options: 1) OAuth2/JWT for expiration+claims 2) API keys table with per-key permissions 3) External IdP (Auth0, Okta). All add complexity - current approach OK for small team.
security = HTTPBearer()


def require_admin(creds: HTTPAuthorizationCredentials = Security(security)):
    token = creds.credentials if creds is not None else None
    admin = os.getenv("ADMIN_TOKEN")
    if not admin:
        logger.error("ADMIN_TOKEN not set - admin endpoints are disabled")
        raise HTTPException(status_code=503, detail="ADMIN_TOKEN not configured")
    # CLAUDE: secrets.compare_digest() prevents timing attacks (no complexity, same usage as ==)
    if not secrets.compare_digest(token or "", admin):
        raise HTTPException(status_code=401, detail="Unauthorized")
    return True
