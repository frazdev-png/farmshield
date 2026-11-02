from datetime import datetime, timezone
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.errors import register_error_handlers
from app.api.v1.router import api_v1_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Auto-initialize database tables and verify default platform admin on startup
    try:
        from app.core.database import engine, Base, SessionLocal
        import app.models  # ensure all models are registered in metadata
        Base.metadata.create_all(bind=engine)

        from app.models.user import User
        from app.core.security import hash_password
        db = SessionLocal()
        try:
            admin_user = db.query(User).filter(User.email == "admin@farmshield.ai").first()
            if not admin_user:
                admin_user = User(
                    full_name="Platform Administrator",
                    email="admin@farmshield.ai",
                    phone_number="+923000000000",
                    password_hash=hash_password("Password123!"),
                    role="admin",
                    is_active=True,
                )
                db.add(admin_user)
                db.commit()
        finally:
            db.close()
    except Exception as exc:
        import logging
        logging.getLogger("farmshield.startup").warning("Database startup hook warning: %s", exc)

    yield
    # Shutdown tasks


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="FarmShield AI backend API - Resilient agriculture risk monitoring and advisory service",
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

# CORS Middleware configuration
cors_allow_origins = settings.CORS_ORIGINS if settings.CORS_ORIGINS else ["*"]
allow_all_origins = "*" in cors_allow_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if allow_all_origins else cors_allow_origins,
    allow_credentials=not allow_all_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register central error handling
register_error_handlers(app)

# Include API v1 router
app.include_router(api_v1_router, prefix=settings.API_V1_PREFIX)


@app.get("/", tags=["Root"], summary="Root Landing Status")
def root_index():
    return {
        "status": "online",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "health": "/health",
        "api_v1": settings.API_V1_PREFIX,
    }


@app.get("/health", tags=["Health"], summary="Root Infrastructure Health Check")
def root_health():
    """
    AWS Application Load Balancer (ALB) and container orchestrator friendly health check.
    """
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.APP_ENV,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

