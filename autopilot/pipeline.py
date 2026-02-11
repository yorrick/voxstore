"""Autopilot Pipeline - Orchestrates the full self-healing flow.

Sentry issue → worktree → fix agent → PR → CI → code review → security → auto-merge
"""

import asyncio
import logging
import time
import uuid

from autopilot.agents.code_fix_agent import run_code_fix_agent
from autopilot.agents.code_review_agent import run_code_review_agent
from autopilot.agents.security_agent import run_security_agent
from autopilot.models.sentry_issue import SentryIssue
from autopilot.modules.github_ops import (
    add_pr_comment,
    get_pr_checks,
    get_pr_diff,
    get_pr_number_for_branch,
    merge_pr,
)
from autopilot.modules.logging import save_run_result, setup_logger
from autopilot.modules.worktree_ops import create_worktree, remove_worktree


async def run_pipeline(issue: SentryIssue, repo_root: str) -> dict:
    """Run the full self-healing pipeline for a Sentry issue.

    Steps:
    1. Create worktree for isolated fix
    2. Run code fix agent (Claude Code SDK + Sentry MCP) — agent creates PR
    3. Cleanup worktree
    4. Wait for CI checks to pass
    5. Run code review agent on the PR
    6. Run security agent on the PR diff
    7. Auto-merge if everything passes
    """
    run_id = f"run-{uuid.uuid4().hex[:8]}"
    logger = setup_logger(run_id)
    result: dict = {"run_id": run_id, "issue_title": issue.title, "steps": {}}

    logger.info(f"Starting pipeline for issue: {issue.title}")
    logger.info(f"  Issue ID: {issue.id} | Short ID: {issue.short_id}")
    logger.info(f"  Culprit: {issue.culprit}")
    logger.info(f"  Level: {issue.level} | Status: {issue.status}")
    logger.info(f"  Occurrences: {issue.count}")
    logger.info(f"  First seen: {issue.first_seen} | Last seen: {issue.last_seen}")
    logger.info(f"  Sentry URL: {issue.permalink or '(none)'}")
    logger.info(f"  Metadata: {issue.metadata}")

    # Step 1: Create worktree
    logger.info(f"Creating worktree for issue {issue.id}...")
    success, worktree_path, err = create_worktree(issue.id, repo_root)
    if not success:
        logger.error(f"Failed to create worktree: {err}")
        result["steps"]["worktree"] = {"success": False, "error": err}
        save_run_result(run_id, result)
        return result
    result["steps"]["worktree"] = {"success": True, "path": worktree_path}
    logger.info(f"Worktree created at: {worktree_path}")

    # Step 2: Run code fix agent (creates PR)
    logger.info("Running code fix agent...")
    fix_result = await run_code_fix_agent(issue, worktree_path, logger=logger)
    result["steps"]["fix_agent"] = fix_result
    logger.info(f"Fix agent result: success={fix_result['success']}")

    # Step 3: Cleanup worktree (always, even if fix failed)
    logger.info("Cleaning up worktree...")
    cleanup_ok, cleanup_err = remove_worktree(worktree_path, repo_root)
    if not cleanup_ok:
        logger.warning(f"Worktree cleanup failed: {cleanup_err}")

    if not fix_result["success"]:
        logger.error("Fix agent failed, aborting pipeline")
        save_run_result(run_id, result)
        return result

    pr_url = fix_result.get("pr_url")
    if not pr_url:
        logger.error("Fix agent did not create a PR")
        save_run_result(run_id, result)
        return result

    result["steps"]["create_pr"] = {"success": True, "url": pr_url}
    logger.info(f"PR created: {pr_url}")

    # Get PR number from branch
    branch_name = f"autopilot/fix-{issue.id}"
    pr_number = get_pr_number_for_branch(branch_name)
    if not pr_number:
        logger.error("Could not find PR number for branch")
        save_run_result(run_id, result)
        return result

    # Step 4: Wait for CI checks (poll for up to 5 minutes)
    logger.info("Waiting for CI checks...")
    ci_passed = await _wait_for_ci(pr_number, logger, timeout=300)
    result["steps"]["ci_checks"] = {"passed": ci_passed}

    if not ci_passed:
        logger.warning("CI checks did not pass, continuing with review anyway")
        add_pr_comment(
            pr_number,
            "**Autopilot:** CI checks did not pass. Proceeding with review.",
        )

    # Step 5: Run code review agent
    logger.info("Running code review agent...")
    review_result = await run_code_review_agent(
        pr_number, repo_root, branch_name=branch_name, logger=logger
    )
    result["steps"]["review"] = review_result
    logger.info(f"Review result: approved={review_result['approved']}")

    # Step 6: Run security agent
    logger.info("Running security agent...")
    pr_diff = get_pr_diff(pr_number) or ""
    security_result = await run_security_agent(
        pr_diff, repo_root, branch_name=branch_name, logger=logger
    )
    result["steps"]["security"] = security_result
    logger.info(f"Security result: passed={security_result['passed']}")

    add_pr_comment(
        pr_number,
        f"**Autopilot Security Audit:**\n\n{security_result['summary']}",
    )

    # Step 7: Auto-merge if all checks pass
    all_passed = ci_passed and review_result["approved"] and security_result["passed"]

    if all_passed:
        logger.info("All checks passed, merging PR...")
        merge_success, merge_err = merge_pr(pr_number)
        result["steps"]["merge"] = {"success": merge_success, "error": merge_err}

        if merge_success:
            logger.info("PR merged successfully!")
            add_pr_comment(
                pr_number,
                "**Autopilot:** All checks passed. PR merged automatically.",
            )
        else:
            logger.error(f"Failed to merge: {merge_err}")
            add_pr_comment(
                pr_number,
                f"**Autopilot:** Failed to auto-merge: {merge_err}",
            )
    else:
        reasons = _build_failure_reasons(ci_passed, review_result, security_result)
        logger.warning(f"Not merging: {', '.join(reasons)}")
        add_pr_comment(
            pr_number,
            f"**Autopilot:** Not auto-merging. Reasons: {', '.join(reasons)}."
            " Manual review required.",
        )
        result["steps"]["merge"] = {"success": False, "reasons": reasons}

    save_run_result(run_id, result)
    logger.info(f"Pipeline complete. Run ID: {run_id}")
    return result


def _build_failure_reasons(
    ci_passed: bool,
    review_result: dict,
    security_result: dict,
) -> list[str]:
    reasons = []
    if not ci_passed:
        reasons.append("CI checks failed")
    if not review_result["approved"]:
        reasons.append("Review requested changes")
    if not security_result["passed"]:
        reasons.append("Security audit found issues")
    return reasons


async def _wait_for_ci(
    pr_number: str,
    logger: logging.Logger,
    timeout: int = 300,
) -> bool:
    """Poll GitHub for CI check results. Returns True if all checks pass."""
    start = time.time()
    while time.time() - start < timeout:
        checks = get_pr_checks(pr_number)

        if not checks:
            await asyncio.sleep(15)
            continue

        # gh pr checks --json: SUCCESS/FAILURE/PENDING/IN_PROGRESS/etc.
        terminal_states = {"SUCCESS", "FAILURE", "CANCELLED", "SKIPPED", "STARTUP_FAILURE"}
        all_complete = all(c.get("state") in terminal_states for c in checks)
        if not all_complete:
            logger.info("CI still running, waiting...")
            await asyncio.sleep(15)
            continue

        all_passed = all(c.get("state") == "SUCCESS" for c in checks)
        if all_passed:
            logger.info("All CI checks passed")
            return True
        else:
            failed = [c["name"] for c in checks if c.get("state") != "SUCCESS"]
            logger.warning(f"CI checks failed: {', '.join(failed)}")
            return False

    logger.warning("CI check timeout reached")
    return False
