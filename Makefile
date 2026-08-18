.PHONY: dev dev-web dev-api db seed install lint test

install:
	cd apps/web && npm install
	cd apps/api && pip install -r requirements.txt

dev-db:
	docker compose up -d postgres redis

dev-web:
	cd apps/web && npm run dev

dev-api:
	cd apps/api && uvicorn app.main:app --reload --port 8000

seed:
	cd apps/api && python -m scripts.seed

migrate:
	cd apps/api && alembic upgrade head

migrate-make:
	cd apps/api && alembic revision --autogenerate -m "$(MSG)"

lint:
	cd apps/web && npm run lint
	cd apps/api && ruff check .

test:
	cd apps/api && pytest tests/ -v

push:
	git add . && git commit -m "$(MSG)" && git push origin main
