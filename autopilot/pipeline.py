"""Autopilot Pipeline - Orchestrates the full self-healing flow.

Sentry error → fix → PR → CI → review → security → auto-merge
"""

import asyncio
import time
import uuid

from autopilot.agents.fix_agent import run_fix_agent
from autopilot.agents.review_agent import run_review_agent
from autopilot.agents.security_agent import run_security_agent
from autopilot.modules.git_ops import checkout_branch, commit_changes, create_branch, push_branch
from autopilot.modules.github_ops import (
    add_pr_comment,
    create_pr,
    get_pr_checks,
    get_pr_diff,
    get_pr_number_for_branch,
    merge_pr,
)
from autopilot.modules.logging import save_run_result, setup_logger
from autopilot.modules.sentry_parser import SentryError


async def run_pipeline(error: SentryError, repo_path: str) -> dict:
    """Run the full self-healing pipeline for a Sentry error.

    Steps:
    1. Create fix branch
    2. Run fix agent (Claude Agent SDK) to apply the fix
    3. Commit and push, create PR
    4. Wait for CI checks to pass
    5. Run review agent on the PR diff
    6. Run security agent on the PR diff
    7. Auto-merge if everything passes
    """
    run_id = f"run-{uuid.uuid4().hex[:8]}"
    logger = setup_logger(run_id)
    result = {"run_id": run_id, "error_title": error.title, "steps": {}}

    logger.info(f"Starting pipeline for error: {error.title}")
    logger.info(f"Sentry URL: {error.url}")

    # Step 1: Create fix branch
    branch_name = f"autopilot/fix-{error.event_id[:8]}-{int(time.time())}"
    logger.info(f"Creating branch: {branch_name}")

    success, err = create_branch(branch_name, cwd=repo_path)
    if not success:
        logger.error(f"Failed to create branch: {err}")
        result["steps"]["create_branch"] = {"success": False, "error": err}
        save_run_result(run_id, result)
        return result
    result["steps"]["create_branch"] = {"success": True, "branch": branch_name}

    # Step 2: Run fix agent
    logger.info("Running fix agent...")
    fix_result = await run_fix_agent(error, repo_path)
    result["steps"]["fix_agent"] = fix_result
    logger.info(f"Fix agent result: success={fix_result['success']}")

    if not fix_result["success"]:
        logger.error("Fix agent failed, aborting pipeline")
        checkout_branch("main", cwd=repo_path)
        save_run_result(run_id, result)
        return result

    # Step 3: Commit, push, and create PR
    logger.info("Committing and pushing fix...")
    commit_msg = f"fix: auto-heal {error.title}\n\nFixed by VoxStore Autopilot\nSentry: {error.url}"
    success, err = commit_changes(commit_msg, cwd=repo_path)
    if not success:
        logger.error(f"Failed to commit: {err}")
        result["steps"]["commit"] = {"success": False, "error": err}
        save_run_result(run_id, result)
        return result

    success, err = push_branch(branch_name, cwd=repo_path)
    if not success:
        logger.error(f"Failed to push: {err}")
        result["steps"]["push"] = {"success": False, "error": err}
        save_run_result(run_id, result)
        return result

    pr_title = f"fix: auto-heal {error.title}"
    pr_body = (
        f"## Autopilot Fix\n\n"
        f"**Error:** {error.title}\n"
        f"**Sentry:** {error.url}\n\n"
        f"### Fix Summary\n{fix_result['summary']}\n\n"
        f"---\n*Created automatically by VoxStore Autopilot*"
    )
    pr_url, err = create_pr(branch_name, pr_title, pr_body, cwd=repo_path)
    if not pr_url:
        logger.error(f"Failed to create PR: {err}")
        result["steps"]["create_pr"] = {"success": False, "error": err}
        save_run_result(run_id, result)
        return result

    logger.info(f"PR created: {pr_url}")
    result["steps"]["create_pr"] = {"success": True, "url": pr_url}

    # Get PR number
    pr_number = get_pr_number_for_branch(branch_name)
    if not pr_number:
        logger.error("Could not find PR number")
        save_run_result(run_id, result)
        return result

    # Step 4: Wait for CI checks (poll for up to 5 minutes)
    logger.info("Waiting for CI checks...")
    ci_passed = await _wait_for_ci(pr_number, logger, timeout=300)
    result["steps"]["ci_checks"] = {"passed": ci_passed}

    if not ci_passed:
        logger.warning("CI checks did not pass, continuing with review anyway")
        add_pr_comment(pr_number, "**Autopilot:** CI checks did not pass. Proceeding with review.")

    # Step 5: Run review agent
    logger.info("Running review agent...")
    pr_diff = get_pr_diff(pr_number) or ""
    error_context = f"{error.title}: {error.message}\n{error.stacktrace}"
    review_result = await run_review_agent(pr_diff, error_context, repo_path)
    result["steps"]["review"] = review_result
    logger.info(f"Review result: approved={review_result['approved']}")

    add_pr_comment(pr_number, f"**Autopilot Review:**\n\n{review_result['summary']}")

    # Step 6: Run security agent
    logger.info("Running security agent...")
    security_result = await run_security_agent(pr_diff, repo_path)
    result["steps"]["security"] = security_result
    logger.info(f"Security result: passed={security_result['passed']}")

    add_pr_comment(pr_number, f"**Autopilot Security Audit:**\n\n{security_result['summary']}")

    # Step 7: Auto-merge if all checks pass
    all_passed = ci_passed and review_result["approved"] and security_result["passed"]

    if all_passed:
        logger.info("All checks passed, merging PR...")
        merge_success, merge_err = merge_pr(pr_number)
        result["steps"]["merge"] = {"success": merge_success, "error": merge_err}

        if merge_success:
            logger.info("PR merged successfully!")
            add_pr_comment(pr_number, "**Autopilot:** All checks passed. PR merged automatically.")
        else:
            logger.error(f"Failed to merge: {merge_err}")
            add_pr_comment(pr_number, f"**Autopilot:** Failed to auto-merge: {merge_err}")
    else:
        reasons = []
        if not ci_passed:
            reasons.append("CI checks failed")
        if not review_result["approved"]:
            reasons.append("Review requested changes")
        if not security_result["passed"]:
            reasons.append("Security audit found issues")

        logger.warning(f"Not merging: {', '.join(reasons)}")
        add_pr_comment(
            pr_number,
            f"**Autopilot:** Not auto-merging. Reasons: {', '.join(reasons)}."
            " Manual review required.",
        )
        result["steps"]["merge"] = {"success": False, "reasons": reasons}

    # Return to main branch
    checkout_branch("main", cwd=repo_path)

    save_run_result(run_id, result)
    logger.info(f"Pipeline complete. Run ID: {run_id}")
    return result


async def _wait_for_ci(pr_number: str, logger, timeout: int = 300) -> bool:
    """Poll GitHub for CI check results. Returns True if all checks pass."""
    start = time.time()
    while time.time() - start < timeout:
        checks = get_pr_checks(pr_number)

        if not checks:
            await asyncio.sleep(15)
            continue

        # Check if all complete
        all_complete = all(c.get("state") == "completed" for c in checks)
        if not all_complete:
            logger.info("CI still running, waiting...")
            await asyncio.sleep(15)
            continue

        # Check if all passed
        all_passed = all(c.get("conclusion") == "success" for c in checks)
        if all_passed:
            logger.info("All CI checks passed")
            return True
        else:
            failed = [c["name"] for c in checks if c.get("conclusion") != "success"]
            logger.warning(f"CI checks failed: {', '.join(failed)}")
            return False

    logger.warning("CI check timeout reached")
    return False
