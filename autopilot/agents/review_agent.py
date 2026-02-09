"""Review Agent - Uses Claude Agent SDK to review a PR diff for correctness."""

from claude_agent_sdk import AssistantMessage, ClaudeAgentOptions, ResultMessage, TextBlock, query

REVIEW_SYSTEM_PROMPT = """You are a code reviewer for the VoxStore application.

You will receive a PR diff. Your job is to review it for:
1. Correctness — does the fix actually address the reported error?
2. Code quality — is the code clean and following project conventions?
3. Regressions — could this change break anything else?
4. Completeness — is anything missing?

Respond with a structured review:
- VERDICT: APPROVE or REQUEST_CHANGES
- SUMMARY: 2-3 sentence summary
- ISSUES: list any problems found (empty if none)

Be pragmatic. If the fix is correct and safe, approve it. Do not nitpick style.
"""


async def run_review_agent(pr_diff: str, error_context: str, repo_path: str) -> dict:
    """Run the review agent on a PR diff.

    Returns a dict with:
        - approved: bool
        - summary: str
        - issues: list[str]
    """
    prompt = f"""Review this PR that fixes a production error.

**Original error context:**
{error_context}

**PR Diff:**
```diff
{pr_diff}
```

Provide your review with VERDICT, SUMMARY, and ISSUES.
"""

    options = ClaudeAgentOptions(
        system_prompt=REVIEW_SYSTEM_PROMPT,
        allowed_tools=["Read", "Glob", "Grep"],
        cwd=repo_path,
        max_turns=10,
    )

    review_text: str = ""
    async for message in query(prompt=prompt, options=options):
        if isinstance(message, ResultMessage):
            result = message.result if hasattr(message, "result") else str(message)
            review_text = result if isinstance(result, str) else str(result)
        elif isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    review_text = block.text

    # Parse verdict from response
    approved = "APPROVE" in review_text.upper() and "REQUEST_CHANGES" not in review_text.upper()

    return {
        "approved": approved,
        "summary": review_text,
    }
