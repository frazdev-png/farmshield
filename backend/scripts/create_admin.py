import os
import sys
import getpass
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from sqlalchemy import select
from app.core.database import SessionLocal, Base, engine
from app.core.security import hash_password
from app.models.user import User


def create_admin():
    """
    Secure administrative account provisioning script.
    Reads credentials from environment variables or interactive user prompts.
    Never creates a default/hardcoded password.
    """
    print("=" * 60)
    print(" FarmShield AI - Secure Administrator Account Provisioning")
    print("=" * 60)

    # Ensure tables exist
    Base.metadata.create_all(bind=engine)

    full_name = os.getenv("ADMIN_FULL_NAME")
    email = os.getenv("ADMIN_EMAIL")
    phone = os.getenv("ADMIN_PHONE")
    password = os.getenv("ADMIN_PASSWORD")

    if not full_name:
        try:
            full_name = input("Enter Admin Full Name: ").strip()
        except EOFError:
            pass
    if not full_name or len(full_name) < 2:
        print("Error: Full name is required (minimum 2 characters).")
        sys.exit(1)

    if not email:
        try:
            email = input("Enter Admin Email: ").strip()
        except EOFError:
            pass
    if not email or "@" not in email:
        print("Error: A valid email address is required.")
        sys.exit(1)
    email = email.lower()

    if not phone:
        try:
            phone = input("Enter Admin Phone Number: ").strip()
        except EOFError:
            pass
    if not phone or len(phone) < 7:
        print("Error: A valid phone number is required (minimum 7 characters).")
        sys.exit(1)

    if not password:
        try:
            password = getpass.getpass("Enter Admin Password (min 8 chars): ").strip()
            confirm = getpass.getpass("Confirm Admin Password: ").strip()
            if password != confirm:
                print("Error: Passwords do not match.")
                sys.exit(1)
        except EOFError:
            pass

    if not password or len(password) < 8:
        print("Error: Password must be at least 8 characters long.")
        sys.exit(1)

    db = SessionLocal()
    try:
        # Prevent accidental duplicate admin accounts
        existing_user = db.scalar(select(User).where((User.email == email) | (User.phone_number == phone)))
        if existing_user:
            print(f"Error: An account with email '{email}' or phone '{phone}' already exists.")
            sys.exit(1)

        admin = User(
            full_name=full_name,
            email=email,
            phone_number=phone,
            password_hash=hash_password(password),
            role="admin",
            is_active=True,
        )

        db.add(admin)
        db.commit()
        db.refresh(admin)

        print("\n[SUCCESS] Administrator account provisioned successfully.")
        print(f"  User ID: {admin.id}")
        print(f"  Email:   {admin.email}")
        print(f"  Role:    {admin.role}")
        print(f"  Active:  {admin.is_active}")
    finally:
        db.close()


if __name__ == "__main__":
    create_admin()
