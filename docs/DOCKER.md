# Docker / GHCR deployment

Media Optimization Engineer publishes a multi-architecture container image to GitHub Container Registry.

## Pull the image

~~~bash
docker pull ghcr.io/kabasele754/media-optimization-engine:1.4.1
~~~

The moving convenience tag is also available:

~~~bash
docker pull ghcr.io/kabasele754/media-optimization-engine:latest
~~~

For production, pin an explicit version instead of `latest`.

## Run one container

The image exposes port 8000 and includes a container health check.

~~~bash
docker run --rm -p 8000:8000 \
  --env-file .env \
  ghcr.io/kabasele754/media-optimization-engine:1.4.1
~~~

A real production deployment normally also needs PostgreSQL and Redis/Celery according to the selected task mode.

## Docker Compose

A ready-to-use example is provided:

~~~bash
cp .env.example .env
docker compose -f docker-compose.ghcr.yml pull
docker compose -f docker-compose.ghcr.yml up -d
~~~

Override the image version without editing Compose:

~~~bash
MOE_IMAGE_TAG=1.4.1 docker compose -f docker-compose.ghcr.yml up -d
~~~

## Migrations

After the first deployment or an upgrade:

~~~bash
docker compose -f docker-compose.ghcr.yml exec django python manage.py migrate
docker compose -f docker-compose.ghcr.yml exec django python manage.py media_engine_doctor
~~~

## Published architectures

The official GHCR image is built for:

- linux/amd64
- linux/arm64

This covers common x86-64 VPS hosts and ARM64 servers.

## Tags

MOE publishes:

~~~text
ghcr.io/kabasele754/media-optimization-engine:<version>
ghcr.io/kabasele754/media-optimization-engine:latest
ghcr.io/kabasele754/media-optimization-engine:sha-<commit>
~~~

Use the immutable version tag in production.
