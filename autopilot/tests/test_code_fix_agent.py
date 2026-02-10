from autopilot.agents.code_fix_agent import _extract_pr_url


def test_extract_pr_url_from_text():
    text = """I've created the PR:
https://github.com/yorrick/voxstore/pull/42

The fix addresses the TypeError by adding a null check."""
    assert _extract_pr_url(text) == "https://github.com/yorrick/voxstore/pull/42"


def test_extract_pr_url_markdown_link():
    text = "PR created: [#42](https://github.com/yorrick/voxstore/pull/42)"
    assert _extract_pr_url(text) == "https://github.com/yorrick/voxstore/pull/42"


def test_extract_pr_url_none_when_missing():
    text = "I was unable to create the PR due to an error."
    assert _extract_pr_url(text) is None


def test_extract_pr_url_empty():
    assert _extract_pr_url("") is None
