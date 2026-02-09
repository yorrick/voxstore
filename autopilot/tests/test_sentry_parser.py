import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from autopilot.modules.sentry_parser import (
    _format_event_stacktrace,
    _format_issue_stacktrace,
    parse_sentry_webhook,
)


def test_parse_event_format():
    payload = {
        "url": "https://sentry.io/issues/123",
        "project_slug": "voxstore",
        "data": {
            "event": {
                "title": "TypeError: Cannot read property 'price' of undefined",
                "message": "Cannot read property 'price' of undefined",
                "culprit": "app.js in renderProducts",
                "level": "error",
                "platform": "javascript",
                "event_id": "abc12345",
                "exception": {
                    "values": [
                        {
                            "type": "TypeError",
                            "value": "Cannot read property 'price' of undefined",
                            "stacktrace": {
                                "frames": [
                                    {
                                        "filename": "app.js",
                                        "lineno": 42,
                                        "function": "renderProducts",
                                        "context_line": "var price = product.price.toFixed(2);",
                                    }
                                ]
                            },
                        }
                    ]
                },
            }
        },
    }

    error = parse_sentry_webhook(payload)
    assert error is not None
    assert error.title == "TypeError: Cannot read property 'price' of undefined"
    assert error.culprit == "app.js in renderProducts"
    assert error.level == "error"
    assert error.platform == "javascript"
    assert error.event_id == "abc12345"
    assert error.project == "voxstore"
    assert "renderProducts" in error.stacktrace
    assert "app.js" in error.stacktrace


def test_parse_issue_format():
    payload = {
        "data": {
            "issue": {
                "id": "issue-456",
                "title": "ZeroDivisionError: division by zero",
                "culprit": "server.py in calculate_discount",
                "level": "error",
                "platform": "python",
                "permalink": "https://sentry.io/issues/456",
                "metadata": {
                    "type": "ZeroDivisionError",
                    "value": "division by zero",
                },
                "project": {"slug": "voxstore-backend"},
            }
        }
    }

    error = parse_sentry_webhook(payload)
    assert error is not None
    assert error.title == "ZeroDivisionError: division by zero"
    assert error.culprit == "server.py in calculate_discount"
    assert error.platform == "python"
    assert error.event_id == "issue-456"
    assert error.project == "voxstore-backend"
    assert "ZeroDivisionError" in error.stacktrace


def test_parse_empty_payload():
    error = parse_sentry_webhook({})
    assert error is None


def test_parse_no_event_no_issue():
    payload = {"data": {"something_else": {}}}
    error = parse_sentry_webhook(payload)
    assert error is None


def test_format_event_stacktrace_with_frames():
    event = {
        "exception": {
            "values": [
                {
                    "type": "ValueError",
                    "value": "invalid literal",
                    "stacktrace": {
                        "frames": [
                            {
                                "filename": "core/db.py",
                                "lineno": 10,
                                "function": "get_connection",
                                "context_line": "conn = sqlite3.connect(path)",
                            },
                            {
                                "filename": "server.py",
                                "lineno": 55,
                                "function": "list_products",
                            },
                        ]
                    },
                }
            ]
        }
    }

    result = _format_event_stacktrace(event)
    assert "ValueError: invalid literal" in result
    assert "core/db.py" in result
    assert "server.py" in result
    assert "get_connection" in result
    assert "conn = sqlite3.connect(path)" in result


def test_format_event_stacktrace_no_exception():
    result = _format_event_stacktrace({})
    assert result == "No stacktrace available"


def test_format_issue_stacktrace():
    issue = {
        "culprit": "app.js in handleClick",
        "metadata": {
            "type": "ReferenceError",
            "value": "x is not defined",
        },
    }

    result = _format_issue_stacktrace(issue)
    assert "ReferenceError: x is not defined" in result
    assert "app.js in handleClick" in result


def test_format_issue_stacktrace_no_culprit():
    issue = {
        "metadata": {"type": "Error", "value": "something broke"},
    }

    result = _format_issue_stacktrace(issue)
    assert "Error: something broke" in result
