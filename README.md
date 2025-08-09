# SUPER - India Local Commerce Platform

> Enable any local business (kirana, barber, garage, water purifier, etc.) to sell to nearby consumers with no payment/logistics headaches.

## 🚀 Quick Start

```bash
# Clone and setup
git clone <repo-url>
cd Super

# Start development environment
make dev-up

# Access applications
# Admin: http://localhost:3000
# Merchant: http://localhost:3001
# API: http://localhost:8000/api/
# Docs: http://localhost:8000/docs/
```

## 📁 Repository Structure

```
super/
├── backend/super_core/     # Django 5 backend API
├── admin-web/             # React admin dashboard
├── midadmin-web/          # React mobile moderation
├── merchant-web/          # React merchant portal
├── consumer-app/          # Flutter consumer app
├── rider-app/             # Flutter rider app
├── ops/                   # Docker, K8s, CI/CD
├── docs/                  # Documentation & ERD
└── Makefile              # Development commands
```

## 🏗️ Architecture

- **Backend**: Django 5 + DRF + Channels + Celery + PostgreSQL + PostGIS
- **Frontend**: React + Vite + TypeScript + Tailwind + shadcn/ui
- **Mobile**: Flutter (Riverpod, Dio, auto_route)
- **Payments**: Own UPI rails (intent/collect/QR, mandates)
- **Logistics**: Own fleet + Porter integration
- **Routing**: OSRM for ETAs and navigation

## 🎯 Core Features

- **Multi-vertical flows**: Barber, Kirana, Garage, Water Purifier
- **UPI Payments**: Platform-managed with auto-settlements
- **Flow Designer**: No-code JSON flows per vertical
- **Rewards**: Universal SuperCash points system
- **Dispatch**: Auto-assignment with batching and zones
- **Ads**: CPC/CPM campaigns with geo-targeting
- **Multi-language**: Regional language support

## 🔧 Development

```bash
# Backend
cd backend && python manage.py runserver

# Admin Web
cd admin-web && npm run dev

# Merchant Web  
cd merchant-web && npm run dev

# Mobile Apps
cd consumer-app && flutter run
cd rider-app && flutter run
```

## 🚢 Deployment

- **Development**: Docker Compose
- **Production**: Kubernetes with auto-scaling
- **CI/CD**: GitHub Actions

## 📊 KPIs

- Merchant activation %
- Time-to-first-listing
- On-time delivery %
- Repeat rate 30d
- Rewards redemption %
- Ads ROAS

## 🛡️ Security

- JWT with rotational refresh
- Device binding for risky flows
- Rate limits and audit logging
- PII encryption and signed URLs

---

**Status**: 🏗️ Under active development