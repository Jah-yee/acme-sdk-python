"""GitHub API rate limit checking and throttling."""

import json
import subprocess
import time
import logging

logger = logging.getLogger(__name__)


def check_rate_limit() -> dict:
    """Check GitHub API rate limit via `gh api rate_limit`.

    Returns dict with 'remaining', 'limit', and 'reset' (unix timestamp).
    """
    try:
        result = subprocess.run(
            ["gh", "api", "rate_limit", "--jq", ".rate"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            return json.loads(result.stdout)
    except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
        pass
    return {"remaining": 5000, "limit": 5000, "reset": 0}


def wait_if_needed(min_remaining: int = 500) -> None:
    """Sleep until rate limit resets if remaining < min_remaining."""
    info = check_rate_limit()
    remaining = info.get("remaining", 5000)
    reset_at = info.get("reset", 0)

    if remaining < min_remaining:
        wait_seconds = max(0, reset_at - time.time()) + 5
        logger.warning(
            "Rate limit low (%d remaining). Sleeping %.0fs until reset.",
            remaining, wait_seconds,
        )
        time.sleep(wait_seconds)


def throttled_reset(repo: str, script_dir: str) -> None:
    """Run setup_github.sh with rate limit check + 60s post-delay."""
    wait_if_needed(min_remaining=500)

    logger.info("Resetting repo state via setup_github.sh for %s...", repo)
    # Ensure we're on main before running setup — a previous failed run
    # may have left the repo on a feature branch.
    subprocess.run(
        ["git", "checkout", "main"],
        capture_output=True, text=True, timeout=10, cwd=script_dir,
    )
    result = subprocess.run(
        ["bash", f"{script_dir}/setup_github.sh", repo],
        capture_output=True, text=True, timeout=600,
    )
    if result.returncode != 0:
        logger.error("setup_github.sh failed:\n%s", result.stderr)
        raise RuntimeError(f"setup_github.sh failed with exit code {result.returncode}")

    logger.info("Reset complete. Waiting 60s for rate limit cooldown...")
    time.sleep(60)
