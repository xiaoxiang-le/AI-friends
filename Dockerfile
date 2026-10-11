# syntax=docker/dockerfile:1

# Build Vue, local VAD assets and the matching Django entry template together.
FROM node:22-bookworm-slim AS frontend-build
WORKDIR /build/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
COPY scripts/ /build/scripts/
COPY backend/web/templates/index.html /build/backend/web/templates/index.html
RUN npm run build

FROM python:3.12-slim-bookworm AS python-build
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 PIP_NO_CACHE_DIR=1
WORKDIR /build
COPY requirements-runtime.txt ./
COPY docker/requirements.txt ./docker/requirements.txt
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install -r docker/requirements.txt

# Used by the Compose gateway. Static/media files come from the shared volume.
FROM nginx:stable-alpine AS nginx
COPY docker/nginx.conf /etc/nginx/conf.d/default.conf

# Default image: Django/Gunicorn; the same image also runs run_jobs and init.
FROM python:3.12-slim-bookworm AS backend
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    DJANGO_DATA_DIR=/data \
    TZ=Asia/Shanghai
RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends libgomp1 tzdata \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 10001 app \
    && useradd --uid 10001 --gid app --no-create-home app
COPY --from=python-build /opt/venv /opt/venv
COPY docker/ /app/docker/
WORKDIR /app/backend
COPY --chown=app:app backend/ ./
COPY --from=frontend-build --chown=app:app /build/backend/static/frontend/ ./static/frontend/
COPY --from=frontend-build --chown=app:app /build/backend/web/templates/index.html ./web/templates/index.html
RUN mkdir -p /data/media/user/photos /data/private_storage /data/staticfiles \
    && cp media/user/photos/default.png /data/media/user/photos/default.png \
    && chown -R app:app /data
USER app
EXPOSE 8000
CMD ["gunicorn", "backend.wsgi:application", "--bind", "0.0.0.0:8000", "--worker-class", "gthread", "--workers", "1", "--threads", "4", "--timeout", "180", "--access-logfile", "-", "--error-logfile", "-"]
