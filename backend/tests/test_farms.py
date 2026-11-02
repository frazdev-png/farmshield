import random
import uuid
import pytest
from fastapi.testclient import TestClient


def create_authenticated_farmer(client: TestClient, name_prefix: str = "Farmer"):
    """Helper to register and login a farmer, returning (user_data, auth_headers)."""
    unique_suffix = uuid.uuid4().hex[:8]
    phone_digits = random.randint(1000000, 9999999)
    email = f"{name_prefix.lower()}_{unique_suffix}@shieldfarm.org"
    password = "SecurePassword123!"

    reg_payload = {
        "full_name": f"{name_prefix} {unique_suffix}",
        "email": email,
        "phone_number": f"+1555{phone_digits}",
        "password": password,
    }
    client.post("/api/v1/auth/register", json=reg_payload)

    login_res = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    return login_res.json()["user"], headers


def test_unauthenticated_farm_access_rejected(client: TestClient):
    """Verify unauthenticated requests cannot access farm endpoints."""
    res1 = client.get("/api/v1/farms")
    assert res1.status_code == 401

    res2 = client.post("/api/v1/farms", json={"farm_name": "Test Farm"})
    assert res2.status_code == 401


def test_farm_creation_and_listing(client: TestClient):
    """Verify creating a farm and retrieving the list of farms."""
    _, headers = create_authenticated_farmer(client, "Creator")

    farm_payload = {
        "farm_name": "Sunset Acres",
        "district": "Story County",
        "village": "Ames",
        "address": "1200 Field Road",
        "latitude": 42.0308,
        "longitude": -93.6319,
        "total_area": 120.5,
        "area_unit": "acres",
        "soil_type": "Clarion Loam",
    }

    create_res = client.post("/api/v1/farms", json=farm_payload, headers=headers)
    assert create_res.status_code == 201
    created_farm = create_res.json()
    assert created_farm["farm_name"] == "Sunset Acres"
    assert created_farm["total_area"] == 120.5
    assert created_farm["area_unit"] == "acres"
    assert created_farm["latitude"] == 42.0308
    assert created_farm["longitude"] == -93.6319
    assert created_farm["crops_count"] == 0
    assert created_farm["total_cultivated_area"] == 0.0

    # List farms
    list_res = client.get("/api/v1/farms", headers=headers)
    assert list_res.status_code == 200
    farms = list_res.json()
    assert len(farms) == 1
    assert farms[0]["id"] == created_farm["id"]


def test_farm_update_and_deletion(client: TestClient):
    """Verify updating farm details and deleting a farm."""
    _, headers = create_authenticated_farmer(client, "Updater")

    create_res = client.post("/api/v1/farms", json={
        "farm_name": "Old Oak Farm",
        "district": "Polk County",
        "village": "Ankeny",
        "latitude": 41.7297,
        "longitude": -93.6057,
        "total_area": 80.0,
        "area_unit": "acres",
    }, headers=headers)
    farm_id = create_res.json()["id"]

    # Update farm
    update_res = client.put(f"/api/v1/farms/{farm_id}", json={
        "farm_name": "New Oak Agro-Enterprise",
        "total_area": 100.0,
        "soil_type": "Silty Clay Loam",
    }, headers=headers)
    assert update_res.status_code == 200
    updated_farm = update_res.json()
    assert updated_farm["farm_name"] == "New Oak Agro-Enterprise"
    assert updated_farm["total_area"] == 100.0
    assert updated_farm["soil_type"] == "Silty Clay Loam"

    # Delete farm
    del_res = client.delete(f"/api/v1/farms/{farm_id}", headers=headers)
    assert del_res.status_code == 204

    # Verify not found
    get_res = client.get(f"/api/v1/farms/{farm_id}", headers=headers)
    assert get_res.status_code == 404


def test_crop_creation_listing_update_deletion(client: TestClient):
    """Verify adding crops to a farm, listing crops, updating and removing them."""
    _, headers = create_authenticated_farmer(client, "CropGrower")

    # Create farm of 100 acres
    farm_res = client.post("/api/v1/farms", json={
        "farm_name": "Cedar Valley Farm",
        "district": "Black Hawk County",
        "village": "Waterloo",
        "latitude": 42.4928,
        "longitude": -92.3426,
        "total_area": 100.0,
        "area_unit": "acres",
    }, headers=headers)
    farm_id = farm_res.json()["id"]

    # Add Crop 1 (Maize 40 acres)
    crop1_res = client.post(f"/api/v1/farms/{farm_id}/crops", json={
        "crop_name": "Field Corn",
        "variety": "Pioneer P1197",
        "cultivated_area": 40.0,
        "area_unit": "acres",
        "sowing_date": "2026-05-10",
    }, headers=headers)
    assert crop1_res.status_code == 201
    crop1 = crop1_res.json()
    assert crop1["crop_name"] == "Field Corn"
    assert crop1["cultivated_area"] == 40.0

    # Add Crop 2 (Soybeans 35 acres)
    crop2_res = client.post(f"/api/v1/farms/{farm_id}/crops", json={
        "crop_name": "Soybeans",
        "variety": "Asgrow 27XF1",
        "cultivated_area": 35.0,
        "area_unit": "acres",
        "sowing_date": "2026-06-01",
    }, headers=headers)
    assert crop2_res.status_code == 201
    crop2_id = crop2_res.json()["id"]

    # List crops
    crops_res = client.get(f"/api/v1/farms/{farm_id}/crops", headers=headers)
    assert crops_res.status_code == 200
    crops = crops_res.json()
    assert len(crops) == 2

    # Check farm metrics updated
    farm_get = client.get(f"/api/v1/farms/{farm_id}", headers=headers)
    assert farm_get.json()["crops_count"] == 2
    assert farm_get.json()["total_cultivated_area"] == 75.0

    # Update crop 2 cultivated area from 35 to 45 acres (total will be 40+45=85 <= 100)
    update_crop_res = client.put(f"/api/v1/farms/{farm_id}/crops/{crop2_id}", json={
        "cultivated_area": 45.0,
        "variety": "Asgrow Enhanced 28XF",
    }, headers=headers)
    assert update_crop_res.status_code == 200
    assert update_crop_res.json()["cultivated_area"] == 45.0
    assert update_crop_res.json()["variety"] == "Asgrow Enhanced 28XF"

    # Delete Crop 2
    del_crop_res = client.delete(f"/api/v1/farms/{farm_id}/crops/{crop2_id}", headers=headers)
    assert del_crop_res.status_code == 204

    # Verify only 1 crop remains
    crops_after = client.get(f"/api/v1/farms/{farm_id}/crops", headers=headers).json()
    assert len(crops_after) == 1
    assert crops_after[0]["id"] == crop1["id"]


def test_invalid_coordinates_validation(client: TestClient):
    """Verify coordinates outside [-90, 90] and [-180, 180] are rejected."""
    _, headers = create_authenticated_farmer(client, "CoordTester")

    # Invalid latitude > 90
    res1 = client.post("/api/v1/farms", json={
        "farm_name": "Invalid Lat Farm",
        "district": "North",
        "village": "Pole",
        "latitude": 91.5,
        "longitude": 0.0,
        "total_area": 50.0,
    }, headers=headers)
    assert res1.status_code == 422

    # Invalid longitude < -180
    res2 = client.post("/api/v1/farms", json={
        "farm_name": "Invalid Lng Farm",
        "district": "West",
        "village": "Edge",
        "latitude": 10.0,
        "longitude": -185.0,
        "total_area": 50.0,
    }, headers=headers)
    assert res2.status_code == 422


def test_invalid_acreage_validation(client: TestClient):
    """Verify total area and cultivated area <= 0 are rejected."""
    _, headers = create_authenticated_farmer(client, "AreaTester")

    # Total area zero or negative
    res1 = client.post("/api/v1/farms", json={
        "farm_name": "Zero Area Farm",
        "district": "Central",
        "village": "Plains",
        "latitude": 40.0,
        "longitude": -90.0,
        "total_area": 0.0,
    }, headers=headers)
    assert res1.status_code == 422

    res_neg = client.post("/api/v1/farms", json={
        "farm_name": "Negative Area Farm",
        "district": "Central",
        "village": "Plains",
        "latitude": 40.0,
        "longitude": -90.0,
        "total_area": -15.0,
    }, headers=headers)
    assert res_neg.status_code == 422


def test_crop_area_exceeding_farm_area_rejected(client: TestClient):
    """Verify that a crop area exceeding the farm total area is rejected with clear 400 error."""
    _, headers = create_authenticated_farmer(client, "AcreLimitTester")

    # Create farm of 50 acres
    farm_res = client.post("/api/v1/farms", json={
        "farm_name": "Fifty Acre Homestead",
        "district": "Dallas County",
        "village": "Adel",
        "latitude": 41.6164,
        "longitude": -94.0175,
        "total_area": 50.0,
        "area_unit": "acres",
    }, headers=headers)
    farm_id = farm_res.json()["id"]

    # 1. Single crop exceeds total area (60 acres > 50 acres)
    res_exceed_single = client.post(f"/api/v1/farms/{farm_id}/crops", json={
        "crop_name": "Corn",
        "cultivated_area": 60.0,
        "area_unit": "acres",
    }, headers=headers)
    assert res_exceed_single.status_code == 400
    assert "exceeds" in res_exceed_single.json()["error"]["message"].lower()

    # 2. Add legitimate crop (30 acres)
    client.post(f"/api/v1/farms/{farm_id}/crops", json={
        "crop_name": "Wheat",
        "cultivated_area": 30.0,
        "area_unit": "acres",
    }, headers=headers)

    # 3. Add second crop that pushes cumulative area over 50 (30 + 25 = 55 > 50)
    res_exceed_cumulative = client.post(f"/api/v1/farms/{farm_id}/crops", json={
        "crop_name": "Barley",
        "cultivated_area": 25.0,
        "area_unit": "acres",
    }, headers=headers)
    assert res_exceed_cumulative.status_code == 400
    assert "exceed" in res_exceed_cumulative.json()["error"]["message"].lower()


def test_cross_farmer_farm_access_prevention(client: TestClient):
    """Verify that Farmer A cannot access, edit, or delete Farmer B's farm."""
    _, headers_farmer_a = create_authenticated_farmer(client, "FarmerA")
    _, headers_farmer_b = create_authenticated_farmer(client, "FarmerB")

    # Farmer A creates a farm
    res_a = client.post("/api/v1/farms", json={
        "farm_name": "Farmer A Secret Ranch",
        "district": "Johnson County",
        "village": "Iowa City",
        "latitude": 41.6611,
        "longitude": -91.5302,
        "total_area": 150.0,
        "area_unit": "acres",
    }, headers=headers_farmer_a)
    farm_a_id = res_a.json()["id"]

    # Farmer B attempts to get Farmer A's farm -> 403 Forbidden
    get_res = client.get(f"/api/v1/farms/{farm_a_id}", headers=headers_farmer_b)
    assert get_res.status_code == 403
    assert "denied" in get_res.json()["error"]["message"].lower()

    # Farmer B attempts to update Farmer A's farm -> 403 Forbidden
    put_res = client.put(f"/api/v1/farms/{farm_a_id}", json={"farm_name": "Hijacked Farm"}, headers=headers_farmer_b)
    assert put_res.status_code == 403

    # Farmer B attempts to delete Farmer A's farm -> 403 Forbidden
    del_res = client.delete(f"/api/v1/farms/{farm_a_id}", headers=headers_farmer_b)
    assert del_res.status_code == 403

    # Verify Farmer A's farm is still intact
    assert client.get(f"/api/v1/farms/{farm_a_id}", headers=headers_farmer_a).status_code == 200


def test_cross_farmer_crop_access_prevention(client: TestClient):
    """Verify that Farmer B cannot view, create, edit or delete crops on Farmer A's farm."""
    _, headers_farmer_a = create_authenticated_farmer(client, "CropOwnerA")
    _, headers_farmer_b = create_authenticated_farmer(client, "IntruderB")

    # Farmer A creates farm and crop
    farm_res = client.post("/api/v1/farms", json={
        "farm_name": "Alpha Ag Land",
        "district": "Linn County",
        "village": "Cedar Rapids",
        "latitude": 41.9779,
        "longitude": -91.6656,
        "total_area": 200.0,
    }, headers=headers_farmer_a)
    farm_id = farm_res.json()["id"]

    crop_res = client.post(f"/api/v1/farms/{farm_id}/crops", json={
        "crop_name": "Premium Soybeans",
        "cultivated_area": 50.0,
    }, headers=headers_farmer_a)
    crop_id = crop_res.json()["id"]

    # Farmer B attempts to list crops on Farmer A's farm -> 403
    assert client.get(f"/api/v1/farms/{farm_id}/crops", headers=headers_farmer_b).status_code == 403

    # Farmer B attempts to add crop to Farmer A's farm -> 403
    assert client.post(f"/api/v1/farms/{farm_id}/crops", json={
        "crop_name": "Malicious Weed",
        "cultivated_area": 10.0,
    }, headers=headers_farmer_b).status_code == 403

    # Farmer B attempts to update Farmer A's crop -> 403
    assert client.put(f"/api/v1/farms/{farm_id}/crops/{crop_id}", json={
        "cultivated_area": 60.0,
    }, headers=headers_farmer_b).status_code == 403

    # Farmer B attempts to delete Farmer A's crop -> 403
    assert client.delete(f"/api/v1/farms/{farm_id}/crops/{crop_id}", headers=headers_farmer_b).status_code == 403
