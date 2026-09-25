.PHONY: dev test check doctor up down migrate audit backfill node-report sync-hub failover-test

dev:
	python manage.py runserver

test:
	python manage.py test media_engine

check:
	python manage.py check

doctor:
	python manage.py media_engine_doctor

up:
	docker compose up -d --build

down:
	docker compose down

migrate:
	docker compose exec django python manage.py migrate

audit:
	docker compose exec django python manage.py audit_media_engine --fail-on-incomplete

backfill:
	docker compose exec django python manage.py backfill_responsive_images

node-report:
	docker compose exec django python manage.py media_engine_node_report

sync-hub:
	docker compose exec django python manage.py sync_media_engine_hub --force

failover-test:
	docker compose exec django sh scripts/test_control_plane_failover.sh
