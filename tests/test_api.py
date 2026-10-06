"""
Unit and integration tests for Vercel-compatible FastAPI application and endpoints.
"""
from fastapi.testclient import TestClient
import pytest

from api.index import app

client = TestClient(app)


def test_health_check_endpoint():
    """Verify GET /api/health returns 200 with service information."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data.get("status") == "healthy"
    assert "app_name" in data
    assert "version" in data


def test_root_serves_dashboard():
    """Verify GET / returns HTML content for the dashboard."""
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert "DataScrape" in response.text or "<!DOCTYPE html>" in response.text


def test_summary_endpoint():
    """Verify GET /api/summary returns valid summary report metrics."""
    response = client.get("/api/summary")
    assert response.status_code == 200
    data = response.json()
    assert "overall" in data or "status" in data
    if "overall" in data:
        assert "final_record_count" in data["overall"]


def test_dataset_endpoint():
    """Verify GET /api/dataset supports pagination and returns structured records."""
    response = client.get("/api/dataset?page=1&page_size=10")
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "page" in data
    assert data["page"] == 1
    assert "records" in data
    assert len(data["records"]) <= 10


def test_data_alias_endpoint():
    """Verify GET /api/data works identically for frontend compatibility."""
    response = client.get("/api/data?page=1&page_size=5")
    assert response.status_code == 200
    data = response.json()
    assert "records" in data
    assert len(data["records"]) <= 5


def test_logs_endpoint():
    """Verify GET /api/logs returns log response payload."""
    response = client.get("/api/logs")
    assert response.status_code == 200
    data = response.json()
    assert "logs" in data


def test_export_endpoint():
    """Verify GET /api/export provides CSV attachment download."""
    response = client.get("/api/export")
    assert response.status_code == 200
    assert "text/csv" in response.headers.get("content-type", "")
