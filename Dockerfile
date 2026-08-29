# Agent + web UI image (Cloud Run service: jusara-agent)
FROM python:3.13-slim

WORKDIR /app

COPY pyproject.toml ./
COPY collaborative_partner ./collaborative_partner
COPY web ./web

# The RAG corpus, its embeddings index and the seeded profiles are part of
# the image. Without them the container starts with an empty knowledge base
# and no demo users.
COPY data ./data

RUN pip install --no-cache-dir .

EXPOSE 8080

# Cloud Run injects $PORT; default to 8080 for local `docker run`.
ENV PORT=8080
CMD ["sh", "-c", "uvicorn web.app:app --host 0.0.0.0 --port ${PORT}"]
