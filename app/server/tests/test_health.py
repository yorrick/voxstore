from core.db import SEED_PRODUCTS


def test_health_check(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["products_count"] == len(SEED_PRODUCTS)
    assert data["uptime_seconds"] >= 0


def test_categories(client):
    res = client.get("/api/categories")
    assert res.status_code == 200
    categories = res.json()
    assert isinstance(categories, list)
    assert "Electronics" in categories
    assert "Clothing" in categories
    assert "Home" in categories
    assert "Books" in categories
    assert "Sports" in categories
    assert len(categories) == 5
