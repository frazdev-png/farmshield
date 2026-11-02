"""
Live Verification Script for FarmShield AI Step 6.2
Verifies:
1. Farmer Role Authentication & RBAC rejection on Admin routes.
2. Admin Role Authentication & RBAC access to Admin routes.
3. Real Open-Meteo API Connectivity using registered farm coordinates.
4. Data Isolation between distinct farmers.
5. Session restoration & JWT validity.
"""
import sys
import json
from pathlib import Path
import httpx

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

BASE_URL = "http://127.0.0.1:8000"

def run_verification():
    print("=" * 70)
    print("FARMSHIELD AI - STEP 6.2 LIVE VERIFICATION PASS")
    print("=" * 70)

    client = httpx.Client(base_url=BASE_URL, timeout=15.0)

    # ---------------------------------------------------------
    # 1. Farmer Registration, Authentication & Role Isolation
    # ---------------------------------------------------------
    print("\n[1] Verifying Farmer Registration & Role Isolation...")
    import random
    unique_id = random.randint(100000, 999999)
    farmer_email = f"farmer_test_{unique_id}@shieldfarm.org"
    
    # Register genuine farmer with actual location coordinates
    reg_resp = client.post("/api/v1/auth/register", json={
        "full_name": f"Farmer Verification {unique_id}",
        "email": farmer_email,
        "phone_number": f"+92300{unique_id}",
        "password": "Password123!",
        "farm_name": "Verified Indus Basin Farm",
        "district": "Lahore",
        "village": "Raiwind Green Sector",
        "latitude": 31.5204,
        "longitude": 74.3587,
        "acreage": "30",
        "primary_crops": "Basmati Rice, Wheat",
    })
    assert reg_resp.status_code == 201, f"Farmer registration failed: {reg_resp.text}"
    print(f"  [OK] Farmer registered successfully with genuine farm coordinates (31.5204, 74.3587).")

    farmer_login = client.post("/api/v1/auth/login", json={
        "email": farmer_email,
        "password": "Password123!"
    })
    assert farmer_login.status_code == 200, f"Farmer login failed: {farmer_login.text}"
    farmer_data = farmer_login.json()
    farmer_token = farmer_data["access_token"]
    farmer_user = farmer_data["user"]
    assert farmer_user["role"] == "farmer", f"Expected role 'farmer', got '{farmer_user['role']}'"
    print(f"  [OK] Farmer logged in successfully. User: {farmer_user['full_name']} (Role: {farmer_user['role']})")

    farmer_headers = {"Authorization": f"Bearer {farmer_token}"}
    me_res = client.get("/api/v1/auth/me", headers=farmer_headers)
    assert me_res.status_code == 200 and me_res.json()["role"] == "farmer"
    print(f"  [OK] Session verification /auth/me confirmed role: {me_res.json()['role']}")

    # Confirm admin endpoints are strictly 403 Forbidden for farmer
    admin_endpoints = [
        "/api/v1/admin/overview",
        "/api/v1/admin/farmers",
        "/api/v1/admin/risks",
        "/api/v1/admin/agent-activity",
    ]
    for ep in admin_endpoints:
        blocked_res = client.get(ep, headers=farmer_headers)
        assert blocked_res.status_code == 403, f"Security leak! Farmer accessed {ep} with status {blocked_res.status_code}"
    print("  [OK] All Admin endpoints returned 403 Forbidden for Farmer token.")

    # ---------------------------------------------------------
    # 2. Admin Role Navigation & Endpoints
    # ---------------------------------------------------------
    print("\n[2] Verifying Admin Authentication & Operations...")
    admin_login = client.post("/api/v1/auth/login", json={
        "email": "admin@farmshield.ai",
        "password": "Password123!"
    })
    assert admin_login.status_code == 200, f"Admin login failed: {admin_login.text}"
    admin_data = admin_login.json()
    admin_token = admin_data["access_token"]
    admin_user = admin_data["user"]
    assert admin_user["role"] == "admin", f"Expected role 'admin', got '{admin_user['role']}'"
    print(f"  [OK] Admin logged in successfully. User: {admin_user['full_name']} (Role: {admin_user['role']})")

    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    admin_overview = client.get("/api/v1/admin/overview", headers=admin_headers)
    assert admin_overview.status_code == 200
    ov_data = admin_overview.json()
    print(f"  [OK] Admin Overview Metrics: Total Farmers={ov_data['total_farmers']}, Total Monitored Acres={ov_data['total_monitored_acres']}")

    admin_farmers = client.get("/api/v1/admin/farmers", headers=admin_headers)
    assert admin_farmers.status_code == 200
    f_list = admin_farmers.json()
    assert len(f_list) > 0
    print(f"  [OK] Admin Farmers Directory: {len(f_list)} registered farmers retrieved (Masked Phone sample: {f_list[0]['masked_phone']})")

    admin_risks = client.get("/api/v1/admin/risks", headers=admin_headers)
    assert admin_risks.status_code == 200
    print(f"  [OK] Admin Risk Surveillance: {len(admin_risks.json())} risk records retrieved.")

    # ---------------------------------------------------------
    # 3. Real Open-Meteo Integration with Farm Coordinates
    # ---------------------------------------------------------
    print("\n[3] Verifying Live Open-Meteo Weather API Integration...")
    # Fetch registered farm for David Sterling
    farms_res = client.get("/api/v1/farms", headers=farmer_headers)
    assert farms_res.status_code == 200
    farms = farms_res.json()
    assert len(farms) > 0, "No farms found for farmer!"
    dev_farm = farms[0]
    farm_id = dev_farm["id"]
    lat = dev_farm["latitude"]
    lon = dev_farm["longitude"]
    print(f"  [OK] Using registered farm: '{dev_farm['farm_name']}' at ({lat}, {lon})")

    # Direct outbound test to Open-Meteo
    open_meteo_url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": round(lat, 4),
        "longitude": round(lon, 4),
        "current": "temperature_2m,relative_humidity_2m,precipitation,weather_code,wind_speed_10m",
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m_max",
        "timezone": "UTC"
    }
    ext_resp = client.get(open_meteo_url, params=params)
    assert ext_resp.status_code == 200, f"Open-Meteo API unreachable: {ext_resp.text}"
    ext_data = ext_resp.json()
    print(f"  [OK] Direct Open-Meteo HTTP 200 response received.")
    print(f"       Current Temp: {ext_data['current']['temperature_2m']} C, Wind: {ext_data['current']['wind_speed_10m']} km/h, Code: {ext_data['current']['weather_code']}")

    # Backend Weather endpoint test
    weather_res = client.get(f"/api/v1/farms/{farm_id}/weather/current", headers=farmer_headers)
    assert weather_res.status_code == 200, f"Backend weather retrieval failed: {weather_res.text}"
    w_data = weather_res.json()
    assert w_data["temperature"] is not None
    assert w_data["weather_condition"] is not None
    print(f"  [OK] Backend farm weather returned live data:")
    print(f"       Condition: '{w_data['weather_condition']}', Temp: {w_data['temperature']} C, Humidity: {w_data['relative_humidity']} %")

    # Forecast endpoint test
    forecast_res = client.get(f"/api/v1/farms/{farm_id}/weather/forecast", headers=farmer_headers)
    assert forecast_res.status_code == 200
    fc_data = forecast_res.json()
    assert len(fc_data.get("forecast", [])) >= 5
    print(f"  [OK] Backend 7-day forecast retrieved: {len(fc_data['forecast'])} daily forecast items.")

    # ---------------------------------------------------------
    # 4. Data Isolation Between Farmers
    # ---------------------------------------------------------
    print("\n[4] Verifying Strict Farmer Data Isolation...")
    # Register an independent Farmer B
    import random
    suffix = random.randint(100000, 999999)
    farmer_b_email = f"farmer_b_{suffix}@shieldfarm.org"
    reg_b = client.post("/api/v1/auth/register", json={
        "full_name": f"Farmer B {suffix}",
        "email": farmer_b_email,
        "phone_number": f"+1555{suffix}",
        "password": "Password123!"
    })
    assert reg_b.status_code == 201, f"Registration of Farmer B failed: {reg_b.text}"
    login_b = client.post("/api/v1/auth/login", json={
        "email": farmer_b_email,
        "password": "Password123!"
    })
    assert login_b.status_code == 200
    token_b = login_b.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # Farmer B attempts to access Farmer A's farm
    cross_access = client.get(f"/api/v1/farms/{farm_id}", headers=headers_b)
    assert cross_access.status_code in [403, 404], f"Data leak! Farmer B accessed Farmer A's farm with status {cross_access.status_code}"
    print("  [OK] Farmer B cannot access Farmer A's farm records (404/403 isolation enforced).")

    # Farmer B attempts to access Farmer A's weather
    cross_weather = client.get(f"/api/v1/farms/{farm_id}/weather/current", headers=headers_b)
    assert cross_weather.status_code in [403, 404]
    print("  [OK] Farmer B cannot access Farmer A's weather telemetry.")

    # Cleanup temporary test users from dev db
    from app.core.database import SessionLocal
    from app.models.user import User
    from sqlalchemy import select, delete, or_
    cleanup_db = SessionLocal()
    try:
        cleanup_db.execute(
            delete(User).where(
                or_(
                    User.email.like("farmer_b_%"),
                    User.email.like("farmer_test_%")
                )
            )
        )
        cleanup_db.commit()
    finally:
        cleanup_db.close()

    print("\n" + "=" * 70)
    print("ALL VERIFICATION CHECKS PASSED SUCCESSFULLY (100%)")
    print("=" * 70)

if __name__ == "__main__":
    run_verification()
