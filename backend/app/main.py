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

            # Seed default demo farmer with farm & crops so login always works across container deploys
            farmer_user = db.query(User).filter(User.email == "farmer@farmshield.ai").first()
            if not farmer_user:
                farmer_user = User(
                    full_name="Muhammad Tariq (Farmer)",
                    email="farmer@farmshield.ai",
                    phone_number="+923116310515",
                    password_hash=hash_password("Password123!"),
                    role="farmer",
                    is_active=True,
                )
                db.add(farmer_user)
                db.flush()

                from app.models.farm import Farm, FarmCrop
                demo_farm = Farm(
                    farmer_id=farmer_user.id,
                    farm_name="Green Acres Farm",
                    district="Multan",
                    village="Chak 42",
                    latitude=30.1575,
                    longitude=71.5249,
                    total_area=12.5,
                    area_unit="acres",
                    soil_type="Loam",
                )
                db.add(demo_farm)
                db.flush()

                crop1 = FarmCrop(
                    farm_id=demo_farm.id,
                    crop_name="Wheat",
                    variety="Faisalabad-2008",
                    cultivated_area=8.0,
                    area_unit="acres",
                )
                crop2 = FarmCrop(
                    farm_id=demo_farm.id,
                    crop_name="Cotton",
                    variety="FH-142",
                    cultivated_area=4.5,
                    area_unit="acres",
                )
                db.add(crop1)
                db.add(crop2)
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

# CORS Middleware configuration - Supports local dev, Render, and AWS Amplify
cors_origins = list(settings.CORS_ORIGINS) if isinstance(settings.CORS_ORIGINS, list) else ["*"]
amplify_origin = "https://main.d3mw37v5rzxeqy.amplifyapp.com"
if amplify_origin not in cors_origins:
    cors_origins.append(amplify_origin)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_origin_regex=r"https://.*\.amplifyapp\.com|https://.*\.onrender\.com|http://localhost.*|http://127\.0\.0\.1.*",
    allow_credentials=True,
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

