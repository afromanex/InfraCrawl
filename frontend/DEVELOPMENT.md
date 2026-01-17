# Frontend Development Environment

## Docker Setup

The frontend runs in its own container with hot-reload enabled. When you edit files in `frontend/src/`, changes are automatically reflected in the browser.

### Volume Mounts

- `./frontend/src:/app/src` - Source code (watched for changes)
- `./frontend/public:/app/public` - Public assets
- `/app/node_modules` - Node modules (anonymous volume to avoid conflicts)

### Running

```bash
# Start all services including frontend
docker compose up

# Frontend will be available at: http://localhost:4200
# Backend API at: http://localhost:8002
```

### Hot Reload

Any changes to files in `frontend/src/` will automatically trigger Angular's dev server to rebuild and reload your browser.

### Backend Proxy

The Angular dev server is configured to proxy API calls to the backend at `http://app:8002`.

