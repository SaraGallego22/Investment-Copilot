FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml ./
COPY collaborative_partner ./collaborative_partner

RUN pip install --no-cache-dir .

EXPOSE 8080

CMD ["adk", "web", "collaborative_partner", "--host", "0.0.0.0", "--port", "8080"]
