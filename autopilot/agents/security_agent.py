"""Security Agent - Uses Claude Agent SDK to audit PR changes for vulnerabilities."""

from claude_agent_sdk import AssistantMessage, ClaudeAgentOptions, ResultMessage, TextBlock, query

SECURITY_SYSTEM_PROMPT = """\
You are a security engineer auditing code changes for the VoxStore application.

VoxStore is a web application with a FastAPI backend and vanilla JS frontend.

Review the PR diff for:
1. SQL injection vulnerabilities
2. XSS (cross-site scripting) in the frontend
3. Path traversal or file access issues
4. Authentication/authorization bypasses
5. Sensitive data exposure (API keys, secrets in code)
6. Command injection
7. SSRF (server-side request forgery)
8. Insecure deserialization

Respond with a structured assessment:
- VERDICT: PASS or FAIL
- RISK_LEVEL: LOW, MEDIUM, HIGH, or CRITICAL
- FINDINGS: list any security issues found (empty if none)
- SUMMARY: 1-2 sentence overall assessment

Be thorough but avoid false positives. Only flag real security concerns.
"""


async def run_security_agent(pr_diff: str, repo_path: str) -> dict:
    """Run the security agent on a PR diff.

    Returns a dict with:
        - passed: bool
        - risk_level: str
        - summary: str
        - findings: list[str]
    """
    prompt = f"""Audit these code changes for security vulnerabilities:

```diff
{pr_diff}
```

Also read any files that the diff touches to understand the full context.
Provide your assessment with VERDICT, RISK_LEVEL, FINDINGS, and SUMMARY.
"""

    options = ClaudeAgentOptions(
        system_prompt=SECURITY_SYSTEM_PROMPT,
        allowed_tools=["Read", "Glob", "Grep"],
        cwd=repo_path,
        max_turns=10,
        permission_mode="bypassPermissions",
    )

    audit_text: str = ""
    async for message in query(prompt=prompt, options=options):
        if isinstance(message, ResultMessage):
            result = message.result if hasattr(message, "result") else str(message)
            audit_text = result if isinstance(result, str) else str(result)
        elif isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    audit_text = block.text

    passed = "PASS" in audit_text.upper() and "FAIL" not in audit_text.upper()

    return {
        "passed": passed,
        "summary": audit_text,
    }
