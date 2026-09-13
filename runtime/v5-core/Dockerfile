# Stage 1: build L1 Guardian (release, lto=false to avoid OOM on constrained runners)
FROM rust:slim AS rust-builder
WORKDIR /build
COPY l1-guardian/ ./l1-guardian/
RUN cd l1-guardian && cargo build --release

# Stage 2: Python demo server
FROM python:3.11-slim
WORKDIR /app
COPY --from=rust-builder /build/l1-guardian/target/release/l1-guardian /app/l1_binary
RUN chmod +x /app/l1_binary
COPY l2-orchestrator/ /l2-orchestrator/
COPY demo-server/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY demo-server/app.py ./app.py
ENV L1_BINARY=/app/l1_binary
EXPOSE 8080
CMD uvicorn app:app --host 0.0.0.0 --port ${PORT:-8080}
