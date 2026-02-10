from autopilot.models.sentry_issue import SentryIssue


def test_from_api_response():
    data = {
        "id": "12345",
        "title": "TypeError: Cannot read property 'price' of undefined",
        "culprit": "app.js in renderProducts",
        "level": "error",
        "status": "unresolved",
        "firstSeen": "2026-02-10T10:00:00Z",
        "lastSeen": "2026-02-10T12:00:00Z",
        "count": 42,
        "permalink": "https://sentry.io/organizations/test/issues/12345/",
        "shortId": "VOXSTORE-1A",
        "metadata": {"type": "TypeError", "value": "Cannot read property 'price'"},
    }

    issue = SentryIssue.from_api_response(data)
    assert issue.id == "12345"
    assert issue.title == "TypeError: Cannot read property 'price' of undefined"
    assert issue.culprit == "app.js in renderProducts"
    assert issue.level == "error"
    assert issue.status == "unresolved"
    assert issue.count == 42
    assert issue.short_id == "VOXSTORE-1A"
    assert "TypeError" in issue.metadata["type"]


def test_from_api_response_missing_fields():
    data = {
        "id": "99999",
    }

    issue = SentryIssue.from_api_response(data)
    assert issue.id == "99999"
    assert issue.title == "Unknown error"
    assert issue.culprit == "unknown"
    assert issue.level == "error"
    assert issue.status == "unresolved"
    assert issue.count == 0
    assert issue.permalink == ""
    assert issue.short_id == ""
    assert issue.metadata == {}
