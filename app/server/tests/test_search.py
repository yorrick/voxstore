def test_search_by_name(client):
    res = client.get("/api/search?q=headphones")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] > 0
    assert data["query"] == "headphones"
    assert any("Headphones" in p["name"] for p in data["products"])


def test_search_by_category(client):
    res = client.get("/api/search?q=Electronics")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] > 0


def test_search_by_description(client):
    res = client.get("/api/search?q=battery")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] > 0


def test_search_empty_query(client):
    res = client.get("/api/search?q=")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 0
    assert data["products"] == []


def test_search_no_results(client):
    res = client.get("/api/search?q=xyznonexistent")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 0


def test_search_case_insensitive(client):
    res = client.get("/api/search?q=KEYBOARD")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] > 0
