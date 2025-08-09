# SUPER Platform Development Makefile

.PHONY: help dev-up dev-down dev-logs dev-clean install-deps backend-setup frontend-setup mobile-setup test lint format

# Default target
help:
	@echo "SUPER Platform Development Commands"
	@echo "=================================="
	@echo "dev-up          Start development environment"
	@echo "dev-down        Stop development environment" 
	@echo "dev-logs        View development logs"
	@echo "dev-clean       Clean development environment"
	@echo ""
	@echo "install-deps    Install all dependencies"
	@echo "backend-setup   Setup Django backend"
	@echo "frontend-setup  Setup React frontends"
	@echo "mobile-setup    Setup Flutter apps"
	@echo ""
	@echo "test            Run all tests"
	@echo "lint            Run linting"
	@echo "format          Format code"

# Development Environment
dev-up:
	@echo "🚀 Starting SUPER development environment..."
	docker-compose up -d
	@echo "✅ Development environment ready!"
	@echo "   Admin:    http://localhost:3000"
	@echo "   Merchant: http://localhost:3001" 
	@echo "   API:      http://localhost:8000/api/"
	@echo "   Docs:     http://localhost:8000/docs/"

dev-down:
	@echo "🛑 Stopping development environment..."
	docker-compose down

dev-logs:
	docker-compose logs -f

dev-clean:
	@echo "🧹 Cleaning development environment..."
	docker-compose down -v
	docker system prune -f

# Dependencies & Setup
install-deps: backend-setup frontend-setup mobile-setup

backend-setup:
	@echo "🐍 Setting up Django backend..."
	cd backend && python -m venv venv
	cd backend && source venv/bin/activate && pip install -r requirements.txt
	cd backend && source venv/bin/activate && python manage.py migrate
	cd backend && source venv/bin/activate && python manage.py collectstatic --noinput

frontend-setup:
	@echo "⚛️  Setting up React frontends..."
	cd admin-web && npm install
	cd merchant-web && npm install
	cd midadmin-web && npm install

mobile-setup:
	@echo "📱 Setting up Flutter apps..."
	cd consumer-app && flutter pub get
	cd rider-app && flutter pub get

# Testing & Quality
test:
	@echo "🧪 Running tests..."
	cd backend && python manage.py test
	cd admin-web && npm test
	cd merchant-web && npm test
	cd consumer-app && flutter test
	cd rider-app && flutter test

lint:
	@echo "🔍 Running linting..."
	cd backend && flake8 .
	cd admin-web && npm run lint
	cd merchant-web && npm run lint
	cd consumer-app && flutter analyze
	cd rider-app && flutter analyze

format:
	@echo "🎨 Formatting code..."
	cd backend && black .
	cd admin-web && npm run format
	cd merchant-web && npm run format
	cd consumer-app && dart format .
	cd rider-app && dart format .

# Database
migrate:
	cd backend && python manage.py migrate

seed:
	cd backend && python manage.py seed_data

# Production
build:
	@echo "🏗️  Building for production..."
	cd admin-web && npm run build
	cd merchant-web && npm run build
	cd consumer-app && flutter build apk
	cd rider-app && flutter build apk