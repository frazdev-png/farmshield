from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.config import settings
from app.core.database import get_db

router = APIRouter()


@router.get("/health", summary="V1 API Health & Readiness Check")
def get_v1_health(db: Session = Depends(get_db)):
    """
    Returns API v1 system health, database connectivity status, and operational metadata.
    """
    db_status = "operational"
    try:
        # Verify active database connectivity via lightweight query
        db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"unreachable: {str(e)}"

    return {
        "status": "healthy" if db_status == "operational" else "degraded",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.APP_ENV,
        "database": db_status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

