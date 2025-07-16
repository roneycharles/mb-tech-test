include .env
export

DOCKER_SERVICES := db banking

.PHONY: install start stop shutdown restart seed test-coverage test

install:
	@echo "Installing requirements..."
	python3 -m venv .venv && \
	source .venv/bin/activate && \
	pip install -r requirements.txt
	@echo "✅ Installation complete! Run 'source .venv/bin/activate' to activate environment."

start:
	@echo "Starting docker services"
	docker compose up --build -d

stop:
	@echo "Stopping docker services"
	docker compose down

shutdown:
	@echo "Stop docker services and delete volumes"
	docker compose down -v

restart:
	$(eval SERVICES := $(or $(filter-out restart, $(MAKECMDGOALS)),$(DOCKER_SERVICES)))
	@echo "Restarting the following docker services: $(SERVICES)"
	docker compose restart $(SERVICES)

seed:
	@echo "Running database seed..."
	docker exec -i exchange-db psql -U ${DB_USER} -d ${DB_NAME} < ./sql/seed.sql
	@echo "Seed completed!"

test:
	pytest tests/ -v

test-coverage:
	pytest tests/ --cov=services --cov-report=html --cov-report=term-missing -v



