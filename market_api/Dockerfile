# Market simulator image (Cloud Run service: jusara-market-api)
#
# Build context is THIS directory, so `gcloud run deploy --source market_api`
# finds this file at the context root.
#
# Intentionally minimal: no AI SDKs, no data files. Prices are generated
# in-process from a fixed seed, so the container carries no state.
FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the package into /app/market_api so `market_api.main` imports cleanly.
COPY . ./market_api

EXPOSE 8080
ENV PORT=8080

CMD ["sh", "-c", "uvicorn market_api.main:app --host 0.0.0.0 --port ${PORT}"]
