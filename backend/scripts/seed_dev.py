"""
Safe Development Seeding Script for FarmShield AI.
Strictly prohibited from running in staging or production environments.
"""
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.user import User
from app.models.farm import Farm, FarmCrop
from app.models.risk import RiskAssessment
from sqlalchemy import select


def seed_development_database(with_farmer: bool = False):
    if settings.APP_ENV != "development":
        print(f"[SECURITY ERROR] Refusing to seed database: APP_ENV is '{settings.APP_ENV}', not 'development'.")
        sys.exit(1)

    print(f"[*] Seeding development database ({settings.DATABASE_URL})...")
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        default_pwd_hash = hash_password("Password123!")

        # 1. Seed or Update Admin Account
        admin_email = "admin@farmshield.ai"
        admin_user = db.scalar(select(User).where(User.email == admin_email))
        if not admin_user:
            admin_user = User(
                full_name="Platform Administrator",
                email=admin_email,
                phone_number="+15550009999",
                password_hash=default_pwd_hash,
                role="admin",
                is_active=True,
            )
            db.add(admin_user)
            print(f"[+] Created admin user: {admin_email}")
        else:
            admin_user.password_hash = default_pwd_hash
            admin_user.is_active = True
            print(f"[*] Verified admin user: {admin_email}")

        # 2. Only seed demo farmer if explicitly requested with --with-farmer
        if with_farmer:
            farmer_email = "david.sterling@farmshield.demo"
            farmer_user = db.scalar(select(User).where(User.email == farmer_email))
            if not farmer_user:
                farmer_user = User(
                    full_name="David Sterling",
                    email=farmer_email,
                    phone_number="+15558881234",
                    password_hash=default_pwd_hash,
                    role="farmer",
                    is_active=True,
                )
                db.add(farmer_user)
                db.flush()
                print(f"[+] Created demo farmer: {farmer_email}")
            else:
                farmer_user.password_hash = default_pwd_hash
                farmer_user.is_active = True
                db.flush()
                print(f"[*] Verified demo farmer: {farmer_email}")

            farm = db.scalar(select(Farm).where(Farm.farmer_id == farmer_user.id))
            if not farm:
                farm = Farm(
                    farmer_id=farmer_user.id,
                    farm_name="Green Oasis Farm",
                    district="Multan",
                    village="Jalalpur",
                    latitude=30.1575,
                    longitude=71.5249,
                    total_area=25.0,
                    area_unit="acres",
                    soil_type="Clay Loam",
                )
                db.add(farm)
                db.flush()
                crop = FarmCrop(
                    farm_id=farm.id,
                    crop_name="Wheat",
                    variety="Galaxy-13",
                    cultivated_area=20.0,
                    area_unit="acres",
                    sowing_date="2026-03-01",
                )
                db.add(crop)

        db.commit()
        print("[OK] Development seeding completed successfully.")

    except Exception as e:
        db.rollback()
        print(f"[!] Seeding failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    include_farmer = "--with-farmer" in sys.argv
    seed_development_database(with_farmer=include_farmer)
