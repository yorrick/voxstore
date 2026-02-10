from unittest.mock import patch


def _mock_semantic_search(query, threshold=0.3):
    """Mock semantic search that simulates vector matching with simple keyword logic."""
    query_lower = query.lower()

    # Simulate semantic matches based on keywords
    matches = {
        "headphones": [(1, 0.9)],
        "electronics": [(1, 0.8), (2, 0.8), (3, 0.8), (4, 0.7), (5, 0.7), (6, 0.7)],
        "battery": [(1, 0.7), (3, 0.6), (5, 0.6)],
        "keyboard": [(2, 0.9)],
    }

    for keyword, results in matches.items():
        if keyword in query_lower:
            return results
    return []


@patch("core.search.is_available", return_value=True)
@patch("core.search.semantic_search", side_effect=_mock_semantic_search)
def test_search_by_name(mock_search, mock_avail, client):
    res = client.get("/api/search?q=headphones")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] > 0
    assert data["query"] == "headphones"
    assert any("Headphones" in p["name"] for p in data["products"])


@patch("core.search.is_available", return_value=True)
@patch("core.search.semantic_search", side_effect=_mock_semantic_search)
def test_search_by_category(mock_search, mock_avail, client):
    res = client.get("/api/search?q=Electronics")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] > 0


@patch("core.search.is_available", return_value=True)
@patch("core.search.semantic_search", side_effect=_mock_semantic_search)
def test_search_by_description(mock_search, mock_avail, client):
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


@patch("core.search.is_available", return_value=True)
@patch("core.search.semantic_search", return_value=[])
def test_search_no_results(mock_search, mock_avail, client):
    res = client.get("/api/search?q=xyznonexistent")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 0


@patch("core.search.is_available", return_value=True)
@patch("core.search.semantic_search", side_effect=_mock_semantic_search)
def test_search_case_insensitive(mock_search, mock_avail, client):
    res = client.get("/api/search?q=KEYBOARD")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] > 0


@patch("core.search.is_available", return_value=False)
def test_search_without_embeddings(mock_avail, client):
    """When embeddings are not available, search returns empty results."""
    res = client.get("/api/search?q=headphones")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 0
