# Makefile for Team Scheduler CI/CD

.PHONY: help install test test-python test-node lint format type-check coverage clean

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install all dependencies
	pip install -r requirements.txt -r requirements-dev.txt
	npm install

test: test-python test-node ## Run all tests

test-python: ## Run Python tests with coverage
	pytest --cov=. --cov-report=term-missing --cov-fail-under=90

test-node: ## Run Node.js tests with coverage
	npm run test:coverage

test-e2e: ## Run E2E tests
	npm run test:e2e

lint: ## Run all linters
	ruff check .
	npm run lint

format: ## Format all code
	ruff format .
	npm run lint:fix

type-check: ## Run type checking
	mypy .
	npm run type-check

coverage: ## Generate coverage reports
	pytest --cov=. --cov-report=html --cov-report=xml
	npm run test:coverage

clean: ## Clean build artifacts and cache
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf coverage.xml
	rm -rf .coverage
	rm -rf node_modules/.cache/
	rm -rf .next/
	rm -rf coverage/
	rm -rf test-results/
	rm -rf playwright-report/

ci: lint type-check test ## Run full CI pipeline locally