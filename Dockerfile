FROM python:3.12-slim

ARG MOE_VERSION=1.4.1

LABEL org.opencontainers.image.title="Media Optimization Engineer" \
      org.opencontainers.image.description="Django/Python media optimization engine with responsive AVIF/WebP delivery and 360 media support." \
      org.opencontainers.image.source="https://github.com/Kabasele754/media-optimization-engine" \
      org.opencontainers.image.version="${MOE_VERSION}" \
      org.opencontainers.image.licenses="MIT"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MEDIA_ENGINE_VERSION=${MOE_VERSION}

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libjpeg62-turbo-dev zlib1g-dev libwebp-dev libavif-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN python -m compileall media_engine

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=5 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/system/health/', timeout=3).read()" || exit 1

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "60"]
