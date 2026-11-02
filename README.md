# FarmShield AI

**FarmShield AI** is an intelligent agricultural resilience platform providing automated micro-climate alerts, predictive pest and disease detection, and generative agronomy advisory to protect crop yields before risks turn into losses.

---

## Architecture Overview (Step 1 Foundation)

- **Frontend**: React 19, TypeScript, Vite, Tailwind CSS v4, Lucide React
- **Backend**: Python 3.11+, FastAPI, Pydantic v2 Settings, SQLAlchemy 2.x, Alembic, Pytest
- **Deployment**: AWS-ready containerization (Docker, ECS Fargate, ALB health checks, RDS PostgreSQL architecture)

---

## Project Structure

```
farmshield/
├── backend/
│   ├── alembic/              # Alembic database migration environment
│   ├── app/
│   │   ├── api/
│   │   │   └── v1/
│   │   │       ├── endpoints/
│   │   │       │   └── health.py    # GET /api/v1/health (DB connectivity & status)
│   │   │       └── router.py        # Central API v1 router
│   │   ├── core/
│   │   │   ├── config.py            # Pydantic BaseSettings & CORS validation
│   │   │   ├── database.py          # SQLAlchemy 2.x engine & sessionmaker
│   │   │   └── errors.py            # Global exception handlers (404, 422, 500)
│   │   └── main.py                  # Root FastAPI application & /health endpoint
│   ├── tests/
│   │   ├── conftest.py              # Pytest fixtures & TestClient configuration
│   │   └── test_health.py           # Health endpoint & error tests
│   ├── alembic.ini                  # Alembic CLI configuration
│   ├── Dockerfile                   # Multi-stage production container
│   ├── requirements.txt             # Locked Python dependencies
│   ├── .env.example                 # Environment variable templates
│   └── .env                         # Local runtime settings
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── common/              # Navbar, BackendStatusBadge, DemoBanner
│   │   │   └── layouts/             # FarmerLayout, AdminLayout
│   │   ├── pages/
│   │   │   ├── public/              # LandingPage, LoginPage, RegisterPage
│   │   │   ├── farmer/              # FarmerOverview, WeatherPlaceholder,
│   │   │   │                        # CropFarmPlaceholder, RiskAlerts,
│   │   │   │                        # FarmerNotifications, AIAssistantChat,
│   │   │   │                        # FarmProfile
│   │   │   └── admin/               # AdminOverview, FarmersManagement,
│   │   │                            # RiskMonitoring, AdminNotifications,
│   │   │                            # AgentActivity
│   │   ├── services/
│   │   │   └── api.ts               # Central API client & health check
│   │   ├── types/
│   │   │   └── index.ts             # Domain & layout TypeScript types
│   │   ├── App.tsx                  # Root layout & route switcher
│   │   ├── main.tsx
│   │   └── index.css                # Tailwind CSS v4 styling
│   ├── .env.example                 # Frontend env templates
│   ├── package.json
│   └── vite.config.ts
├── docs/
│   └── AWS_DEPLOYMENT.md            # AWS Architecture, ECS, ALB, RDS, Secrets
└── .gitignore
```

---

## Quick Start Commands

### Backend Setup & Execution
```bash
cd backend
python -m venv venv
.\venv\Scripts\activate       # On Windows (or 'source venv/bin/activate' on Linux/macOS)
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Backend Tests
```bash
cd backend
.\venv\Scripts\pytest -v
```

### Frontend Setup & Execution
```bash
cd frontend
npm install
npm run dev
```

### Frontend Production Build
```bash
cd frontend
npm run build
```

