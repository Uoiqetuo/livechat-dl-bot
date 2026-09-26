FROM node:22-bookworm-slim AS node-runtime

FROM python:3.12-slim-bookworm AS builder
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir --no-compile --prefix=/install .

FROM python:3.12-slim-bookworm
WORKDIR /app
COPY --from=node-runtime /usr/local/bin/node /usr/local/bin/node
COPY --from=builder /install /usr/local
RUN mkdir -p /data/jobs
RUN mkdir -p /cookies
ENV DATA_DIR=/data \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
CMD ["python", "-m", "livechat_bot"]
