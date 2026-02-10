import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from autopilot.models.sentry_issue import SentryIssue
from autopilot.poller import (
    load_processed_issues,
    mark_issue_processed,
)


@pytest.fixture
def temp_data_dir(monkeypatch):
    """Use a temporary directory for processed issues data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        data_dir = Path(tmpdir) / "data"
        data_dir.mkdir()
        processed_file = data_dir / "processed_issues.json"
        monkeypatch.setattr("autopilot.poller.DATA_DIR", data_dir)
        monkeypatch.setattr("autopilot.poller.PROCESSED_FILE", processed_file)
        yield data_dir, processed_file


def test_load_processed_issues_empty(temp_data_dir):
    result = load_processed_issues()
    assert result == {}


def test_mark_and_load_processed(temp_data_dir):
    mark_issue_processed("123")
    mark_issue_processed("456")

    result = load_processed_issues()
    assert "123" in result
    assert "456" in result
    assert len(result) == 2


def test_mark_processed_creates_dir(temp_data_dir):
    data_dir, _ = temp_data_dir
    # Remove dir to test creation
    import shutil

    shutil.rmtree(data_dir)

    mark_issue_processed("789")
    result = load_processed_issues()
    assert "789" in result


@pytest.mark.asyncio
async def test_poll_once_no_new_issues(temp_data_dir):
    """poll_once should skip already-processed issues."""
    mark_issue_processed("existing-1")

    mock_issues = [
        SentryIssue(
            id="existing-1",
            title="Old error",
            culprit="test.py",
            level="error",
            status="unresolved",
            first_seen="2026-01-01",
            last_seen="2026-01-01",
            count=1,
            permalink="https://sentry.io/1",
            short_id="TEST-1",
            metadata={},
        ),
    ]

    with (
        patch("autopilot.poller.fetch_unresolved_issues", new_callable=AsyncMock) as mock_fetch,
        patch("autopilot.poller.run_pipeline", new_callable=AsyncMock) as mock_pipeline,
    ):
        mock_fetch.return_value = mock_issues
        from autopilot.poller import poll_once

        await poll_once()

        mock_pipeline.assert_not_called()


@pytest.mark.asyncio
async def test_poll_once_processes_new_issue(temp_data_dir):
    """poll_once should trigger pipeline for new issues."""
    mock_issues = [
        SentryIssue(
            id="new-1",
            title="New error",
            culprit="app.py",
            level="error",
            status="unresolved",
            first_seen="2026-02-10",
            last_seen="2026-02-10",
            count=5,
            permalink="https://sentry.io/new-1",
            short_id="TEST-2",
            metadata={},
        ),
    ]

    with (
        patch("autopilot.poller.fetch_unresolved_issues", new_callable=AsyncMock) as mock_fetch,
        patch("autopilot.poller.run_pipeline", new_callable=AsyncMock) as mock_pipeline,
    ):
        mock_fetch.return_value = mock_issues
        mock_pipeline.return_value = {"run_id": "run-test"}
        from autopilot.poller import poll_once

        await poll_once()

        mock_pipeline.assert_called_once()
        # Issue should now be marked as processed
        processed = load_processed_issues()
        assert "new-1" in processed
