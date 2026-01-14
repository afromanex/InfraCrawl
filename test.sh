#!/bin/bash
set -e

# Run tests in Docker using docker compose (v2 syntax)
echo "Running tests in Docker container..."
docker compose run --rm test pytest "$@"
