FROM python:3.11-slim
WORKDIR /app

# Install OS packages needed for migrations (psql, pg_isready)
RUN apt-get update && apt-get install -y postgresql-client && rm -rf /var/lib/apt/lists/*
# Install main and dev requirements
COPY requirements.txt ./
COPY requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements.txt && \
	pip install --no-cache-dir -r requirements-dev.txt

COPY . .

COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD ["python", "run.py"]
