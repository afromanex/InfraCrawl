# InfraCrawl

Minimal web crawler scaffold that stores raw HTML bodies in Postgres. Dockerized with a Postgres service in `docker-compose.yml`.

Quick start (Docker):

```bash
docker-compose up --build
```

The app uses `DATABASE_URL` environment variable. See `.env.example` for defaults.
