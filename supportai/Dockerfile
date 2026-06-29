# === Build stage ===
FROM python:3.11-slim AS builder

WORKDIR /build

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir --prefix=/install -r requirements.txt

# === Runtime stage ===
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc g++ && \
    rm -rf /var/lib/apt/lists/*

COPY --from=builder /install /usr/local

COPY . .

RUN mkdir -p data

EXPOSE 8000
EXPOSE 8501

CMD ["sh", "-c", "uvicorn supportai.api.main:app --host 0.0.0.0 --port ${PORT:-8000} & streamlit run supportai/dashboard/app.py --server.port ${STREAMLIT_SERVER_PORT:-8501} --server.headless true"]
