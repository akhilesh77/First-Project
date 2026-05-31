"""Phase 3 API tests."""

from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.data.constants import CANONICAL_COLUMNS
from app.data.repository import RestaurantRepository
from app.main import create_app


def _sample_rows():
    return [
        {
            "restaurant_id": "r1",
            "name": "Spice Villa",
            "city": "Bangalore",
            "listing_area": "Btm",
            "neighborhood": "BTM",
            "address": "BTM, Bangalore",
            "cuisines": "North Indian, Chinese",
            "cuisine_tokens": '["north indian", "chinese"]',
            "aggregate_rating": 4.5,
            "votes": 500,
            "cost_for_two": 800.0,
            "budget_band": "medium",
            "rest_type": "Casual Dining",
            "dish_liked": "Biryani",
            "additional_text": "family-friendly",
            "source_url": "https://example.com/r1",
        },
    ]


@pytest.fixture
def api_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    db = tmp_path / "api_test.db"
    repo = RestaurantRepository(db)
    repo.replace_all(pd.DataFrame(_sample_rows(), columns=CANONICAL_COLUMNS))
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db}")
    monkeypatch.delenv("API_KEY", raising=False)
    monkeypatch.setenv("LLM_ENABLED", "false")

    from app.api import deps

    deps.get_recommendation_service.cache_clear()

    client = TestClient(create_app())
    yield client

    deps.get_recommendation_service.cache_clear()


def test_health_ok(api_client: TestClient):
    response = api_client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"] == "ok"
    assert body["row_count"] == 1


def test_recommendations_success(api_client: TestClient):
    response = api_client.post(
        "/v1/recommendations",
        json={
            "location": "Bengaluru",
            "budget": "medium",
            "cuisine": "North Indian",
            "min_rating": 4.0,
            "recommendation_count": 5,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body["recommendations"]) == 1
    item = body["recommendations"][0]
    assert item["restaurant_id"] == "r1"
    assert item["name"] == "Spice Villa"
    assert item["cuisine"] == "North Indian, Chinese"
    assert item["rating"] == 4.5
    assert item["estimated_cost"] == 800.0
    assert "explanation" in item and len(item["explanation"]) > 0
    assert body["metadata"]["candidates_considered"] == 1
    assert body["metadata"]["model"] == "stub"
    assert body["metadata"]["latency_ms"] >= 0
    assert body.get("summary") is None


def test_recommendations_empty_city(api_client: TestClient):
    response = api_client.post(
        "/v1/recommendations",
        json={
            "location": "Mumbai",
            "budget": "medium",
            "cuisine": "North Indian",
            "min_rating": 4.0,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["recommendations"] == []
    assert body["message"] is not None


def test_validation_invalid_budget(api_client: TestClient):
    response = api_client.post(
        "/v1/recommendations",
        json={
            "location": "Bangalore",
            "budget": "cheap",
            "cuisine": "Italian",
            "min_rating": 4.0,
        },
    )
    assert response.status_code == 400


def test_validation_recommendation_count_too_large(api_client: TestClient):
    response = api_client.post(
        "/v1/recommendations",
        json={
            "location": "Bangalore",
            "budget": "medium",
            "cuisine": "North Indian",
            "min_rating": 4.0,
            "recommendation_count": 100,
        },
    )
    assert response.status_code == 400


def test_api_key_required(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    db = tmp_path / "api_key_test.db"
    repo = RestaurantRepository(db)
    repo.replace_all(pd.DataFrame(_sample_rows(), columns=CANONICAL_COLUMNS))
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db}")
    monkeypatch.setenv("API_KEY", "secret-test-key")
    monkeypatch.setenv("LLM_ENABLED", "false")

    from app.api import deps

    deps.get_recommendation_service.cache_clear()
    client = TestClient(create_app())

    unauthorized = client.post(
        "/v1/recommendations",
        json={
            "location": "Bangalore",
            "budget": "medium",
            "cuisine": "North Indian",
            "min_rating": 4.0,
        },
    )
    assert unauthorized.status_code == 401

    authorized = client.post(
        "/v1/recommendations",
        json={
            "location": "Bangalore",
            "budget": "medium",
            "cuisine": "North Indian",
            "min_rating": 4.0,
        },
        headers={"X-API-Key": "secret-test-key"},
    )
    assert authorized.status_code == 200
    deps.get_recommendation_service.cache_clear()


def test_locations_endpoint(api_client: TestClient):
    """GET /v1/locations returns localities from the database."""
    response = api_client.get("/v1/locations")
    assert response.status_code == 200
    body = response.json()
    assert "locations" in body
    assert "total" in body
    assert body["total"] >= 1
    # The sample data has neighborhood="BTM" and listing_area="Btm"
    localities = [entry["locality"] for entry in body["locations"]]
    assert any("BTM" in loc or "Btm" in loc for loc in localities)


def test_locations_city_filter(api_client: TestClient):
    """GET /v1/locations?city=Bangalore returns only Bangalore localities."""
    response = api_client.get("/v1/locations?city=Bangalore")
    assert response.status_code == 200
    body = response.json()
    for entry in body["locations"]:
        assert entry["city"] == "Bangalore"


def test_locations_unknown_city_returns_empty(api_client: TestClient):
    """GET /v1/locations?city=UnknownCity returns 0 entries."""
    response = api_client.get("/v1/locations?city=UnknownCity")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 0
    assert body["locations"] == []


def test_recommendations_by_locality(api_client: TestClient):
    """POST /v1/recommendations with a locality name should still find results."""
    response = api_client.post(
        "/v1/recommendations",
        json={
            "location": "BTM",
            "budget": "medium",
            "cuisine": "North Indian",
            "min_rating": 4.0,
            "recommendation_count": 5,
        },
    )
    assert response.status_code == 200
    body = response.json()
    # BTM is a known neighborhood in Bangalore in our sample data
    assert len(body["recommendations"]) == 1
    assert body["recommendations"][0]["name"] == "Spice Villa"


def test_database_configuration_error(api_client: TestClient, monkeypatch: pytest.MonkeyPatch):
    """OP-03: Wrong DATABASE_URL in prod should lead to 503 instead of 500."""
    monkeypatch.setenv("DATABASE_URL", "invalid_url")
    
    # Recommendations should return 503
    response = api_client.post(
        "/v1/recommendations",
        json={
            "location": "BTM",
            "budget": "medium",
            "cuisine": "North Indian",
            "min_rating": 4.0,
            "recommendation_count": 5,
        },
    )
    assert response.status_code == 503
    body = response.json()
    assert "Database configuration error" in body["detail"]

    # Health check should return degraded status instead of raising 500
    health_resp = api_client.get("/health")
    assert health_resp.status_code == 200
    health_body = health_resp.json()
    assert health_body["status"] == "degraded"
    assert health_body["database"] == "missing"


