from fastapi import APIRouter
from app.api.v1.endpoints import health, auth, farms, weather, risks, assistant, notifications, admin

api_v1_router = APIRouter()
api_v1_router.include_router(health.router, tags=["Health"])
api_v1_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_v1_router.include_router(farms.router, prefix="/farms", tags=["Farms & Crops"])
api_v1_router.include_router(weather.router, prefix="/farms", tags=["Weather"])
api_v1_router.include_router(risks.router, prefix="/farms", tags=["Agro-Climatic Risks"])
api_v1_router.include_router(assistant.router, prefix="/assistant", tags=["AI Advisor"])
api_v1_router.include_router(notifications.router, prefix="/notifications", tags=["Notifications"])
api_v1_router.include_router(notifications.admin_router, prefix="/admin/notifications", tags=["Admin Notifications"])
api_v1_router.include_router(admin.router, prefix="/admin", tags=["Admin Operations"])
