import random
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.user import User
from app.core.security import hash_password, verify_password


def test_password_hashing_verification():
    """Verify password hashing creates valid Argon2id hash and verify function works."""
    raw_pwd = "StrongFarmingPassword2026!"
    hashed = hash_password(raw_pwd)

    # Argon2id hashes start with $argon2id$
    assert hashed.startswith("$argon2id$")
    assert hashed != raw_pwd
    assert verify_password(raw_pwd, hashed) is True
    assert verify_password("WrongPassword!", hashed) is False


def test_farmer_registration_success(client: TestClient):
    """Verify that a farmer can be successfully registered."""
    unique_suffix = uuid.uuid4().hex[:8]
    r_digits = random.randint(1000000, 9999999)
    payload = {
        "full_name": f"Farmer John {unique_suffix}",
        "email": f"farmer_{unique_suffix}@shieldfarm.org",
        "phone_number": f"+1555{r_digits}",
        "password": "SecurePassword123!",
    }

    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == payload["email"].lower()
    assert data["full_name"] == payload["full_name"]
    assert data["role"] == "farmer"
    assert data["is_active"] is True
    assert "id" in data
    assert "password" not in data
    assert "password_hash" not in data


def test_farmer_registration_duplicate_email(client: TestClient):
    """Verify duplicate email registration is rejected."""
    unique_suffix = uuid.uuid4().hex[:8]
    email = f"duplicate_{unique_suffix}@shieldfarm.org"
    r1 = random.randint(1000000, 9999999)
    r2 = random.randint(1000000, 9999999)
    payload1 = {
        "full_name": "First Farmer",
        "email": email,
        "phone_number": f"+15551{r1}",
        "password": "PasswordOne123!",
    }
    payload2 = {
        "full_name": "Second Farmer",
        "email": email.upper(),  # Test case-insensitivity
        "phone_number": f"+15552{r2}",
        "password": "PasswordTwo123!",
    }

    res1 = client.post("/api/v1/auth/register", json=payload1)
    assert res1.status_code == 201

    res2 = client.post("/api/v1/auth/register", json=payload2)
    assert res2.status_code == 400
    assert "email" in res2.json()["error"]["message"].lower()


def test_farmer_registration_duplicate_phone(client: TestClient):
    """Verify duplicate phone registration is rejected."""
    unique_suffix = uuid.uuid4().hex[:8]
    phone = f"+15553{random.randint(1000000, 9999999)}"
    payload1 = {
        "full_name": "Phone Farmer One",
        "email": f"phone1_{unique_suffix}@shieldfarm.org",
        "phone_number": phone,
        "password": "PasswordOne123!",
    }
    payload2 = {
        "full_name": "Phone Farmer Two",
        "email": f"phone2_{unique_suffix}@shieldfarm.org",
        "phone_number": phone,
        "password": "PasswordTwo123!",
    }

    res1 = client.post("/api/v1/auth/register", json=payload1)
    assert res1.status_code == 201

    res2 = client.post("/api/v1/auth/register", json=payload2)
    assert res2.status_code == 400
    assert "phone" in res2.json()["error"]["message"].lower()


def test_public_registration_cannot_create_admin(client: TestClient):
    """Verify that public registration ignores any role parameter and forces role='farmer'."""
    unique_suffix = uuid.uuid4().hex[:8]
    payload = {
        "full_name": "Hacker Trying Admin",
        "email": f"fake_admin_{unique_suffix}@shieldfarm.org",
        "phone_number": f"+15554{random.randint(1000000, 9999999)}",
        "password": "HackerPassword123!",
        "role": "admin",  # Maliciously attempt privilege escalation
    }

    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["role"] == "farmer"  # Must strictly remain 'farmer'


def test_login_successful(client: TestClient):
    """Verify that valid credentials return a JWT token and user info."""
    unique_suffix = uuid.uuid4().hex[:8]
    email = f"login_user_{unique_suffix}@shieldfarm.org"
    password = "MySafePassword2026!"

    reg_payload = {
        "full_name": "Login Tester",
        "email": email,
        "phone_number": f"+15555{random.randint(1000000, 9999999)}",
        "password": password,
    }
    client.post("/api/v1/auth/register", json=reg_payload)

    login_payload = {
        "email": email,
        "password": password,
    }
    response = client.post("/api/v1/auth/login", json=login_payload)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == email.lower()
    assert "password_hash" not in data["user"]


def test_login_incorrect_password(client: TestClient):
    """Verify generic error on invalid password to prevent account enumeration."""
    unique_suffix = uuid.uuid4().hex[:8]
    email = f"wrong_pwd_{unique_suffix}@shieldfarm.org"
    password = "CorrectPassword123!"

    reg_payload = {
        "full_name": "Wrong Password Tester",
        "email": email,
        "phone_number": f"+15556{random.randint(1000000, 9999999)}",
        "password": password,
    }
    client.post("/api/v1/auth/register", json=reg_payload)

    # Wrong password
    response = client.post("/api/v1/auth/login", json={"email": email, "password": "BadPassword999!"})
    assert response.status_code == 401
    assert "invalid email or password" in response.json()["error"]["message"].lower()

    # Non-existent email should give identical error message
    response_no_user = client.post("/api/v1/auth/login", json={"email": "nonexistent@nowhere.com", "password": "AnyPassword!"})
    assert response_no_user.status_code == 401
    assert "invalid email or password" in response_no_user.json()["error"]["message"].lower()


def test_auth_me_authenticated(client: TestClient):
    """Verify /me returns user data when authenticated with Bearer token."""
    unique_suffix = uuid.uuid4().hex[:8]
    email = f"me_{unique_suffix}@shieldfarm.org"
    password = "ValidPassword123!"

    client.post("/api/v1/auth/register", json={
        "full_name": "Me User",
        "email": email,
        "phone_number": f"+15557{random.randint(1000000, 9999999)}",
        "password": password,
    })

    login_res = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    token = login_res.json()["access_token"]

    # Call /me with Bearer token
    me_res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    data = me_res.json()
    assert data["email"] == email.lower()
    assert data["role"] == "farmer"
    assert "password_hash" not in data


def test_auth_me_missing_or_invalid_token(client: TestClient):
    """Verify missing or forged tokens are rejected."""
    # Missing token
    res1 = client.get("/api/v1/auth/me")
    assert res1.status_code == 401

    # Invalid / forged token
    res2 = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer totally-forged-invalid-jwt-token"})
    assert res2.status_code == 401


def test_admin_only_access_restriction(client: TestClient, test_db: Session):
    """Verify role-checking dependency blocks farmer from accessing admin endpoints."""
    from app.main import app
    from fastapi import Depends
    from app.api.deps import require_admin

    # Add a temporary test admin endpoint if not already registered
    route_path = "/api/v1/test-admin-gate"
    if not any(getattr(route, "path", None) == route_path for route in app.routes):
        @app.get(route_path)
        def test_admin_gate(admin=Depends(require_admin)):
            return {"admin": True, "user_id": str(admin.id)}

    unique_suffix = uuid.uuid4().hex[:8]

    # 1. Register a regular farmer and get token
    farmer_email = f"farmer_gate_{unique_suffix}@shieldfarm.org"
    pwd = "FarmerPassword123!"
    client.post("/api/v1/auth/register", json={
        "full_name": "Regular Farmer",
        "email": farmer_email,
        "phone_number": f"+15558{random.randint(1000000, 9999999)}",
        "password": pwd,
    })
    farmer_login = client.post("/api/v1/auth/login", json={"email": farmer_email, "password": pwd})
    farmer_token = farmer_login.json()["access_token"]

    # Farmer attempts to access admin gate -> 403 Forbidden
    forbidden_res = client.get(route_path, headers={"Authorization": f"Bearer {farmer_token}"})
    assert forbidden_res.status_code == 403
    assert "forbidden" in forbidden_res.json()["error"]["message"].lower()

    # 2. Provision an admin directly in isolated test DB and verify access is allowed
    admin_email = f"admin_gate_{unique_suffix}@shieldfarm.org"
    admin_user = User(
        full_name="True Admin",
        email=admin_email,
        phone_number=f"+15559{random.randint(1000000, 9999999)}",
        password_hash=hash_password(pwd),
        role="admin",
        is_active=True,
    )
    test_db.add(admin_user)
    test_db.commit()

    admin_login = client.post("/api/v1/auth/login", json={"email": admin_email, "password": pwd})
    admin_token = admin_login.json()["access_token"]

    allowed_res = client.get(route_path, headers={"Authorization": f"Bearer {admin_token}"})
    assert allowed_res.status_code == 200
    assert allowed_res.json()["admin"] is True
