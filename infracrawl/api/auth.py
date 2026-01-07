import os
from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# Simple HTTP Bearer token auth for admin operations.
# Set ADMIN_TOKEN env var to enable.
security = HTTPBearer()


def require_admin(creds: HTTPAuthorizationCredentials = Security(security)):
    token = creds.credentials if creds is not None else None
    admin = os.getenv("ADMIN_TOKEN")
    if not admin:
        # no admin token configured — treat as open (no-op)
        return True
    if token != admin:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return True
