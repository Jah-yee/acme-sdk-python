#!/usr/bin/env python3
"""
Eval harness for MCP vs. Skill agent tool integration comparison.

Runs 25 GitHub operations tasks against 3 arms (MCP, Skill-LobeHub, Skill-Vault),
with configurable repetitions per task. Results are logged to Arize AX.

Usage:
    python eval/run_eval.py                                    # full run, all arms
    python eval/run_eval.py --arm mcp --task T01 --runs 1      # single task, single arm
    python eval/run_eval.py --tier 1 --dry-run                 # tier 1 only, dry run
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

# Load .env before any other imports that need env vars
load_dotenv(dotenv_path=Path(__file__).parent / ".env")

import pandas as pd
from arize import ArizeClient
from arize.experiments import EvaluationResult
from claude_agent_sdk import ClaudeAgentOptions, query, AssistantMessage, TextBlock, ToolUseBlock

from arms import get_arm_options, ARM_NAMES
from evaluators import evaluate_task
from rate_limit import throttled_reset, wait_if_needed

SCRIPT_DIR = Path(__file__).parent
REPO_ROOT = SCRIPT_DIR.parent
LOG_FILE = SCRIPT_DIR / "eval.log"

_log_fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
logging.basicConfig(level=logging.INFO, format=_log_fmt)
_file_handler = logging.FileHandler(LOG_FILE, mode="a")
_file_handler.setFormatter(logging.Formatter(_log_fmt))
logging.getLogger().addHandler(_file_handler)

logger = logging.getLogger("eval")


def load_tasks(task_filter: str | None = None, tier_filter: int | None = None) -> list[dict]:
    """Load tasks from tasks.json, optionally filtering by ID or tier."""
    tasks_file = SCRIPT_DIR / "tasks.json"
    with open(tasks_file) as f:
        data = json.load(f)

    tasks = data["tasks"]

    if task_filter:
        task_ids = [t.strip().upper() for t in task_filter.split(",")]
        tasks = [t for t in tasks if t["id"] in task_ids]

    if tier_filter:
        tasks = [t for t in tasks if t["tier"] == tier_filter]

    return tasks


def split_tasks(tasks: list[dict]) -> tuple[list[dict], list[dict]]:
    """Split tasks into read/analysis (no reset needed) and write (need reset)."""
    read_tasks = [t for t in tasks if t["category"] in ("read", "analysis")]
    write_tasks = [t for t in tasks if t["category"] == "write"]
    return read_tasks, write_tasks


async def run_single_task(description: str, options: ClaudeAgentOptions) -> dict:
    """Execute a single task via claude-agent-sdk and collect results."""
    result_text = ""
    tool_calls = 0
    start_time = time.time()

    try:
        async for message in query(prompt=description, options=options):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        result_text += block.text
                    elif isinstance(block, ToolUseBlock):
                        tool_calls += 1
    except Exception as e:
        result_text = f"ERROR: {e}"
        logger.error("Task failed: %s", e)

    elapsed = time.time() - start_time
    return {
        "output": result_text,
        "tool_calls": tool_calls,
        "latency_seconds": round(elapsed, 2),
    }


def create_arize_client() -> ArizeClient:
    """Create an authenticated Arize AX client."""
    api_key = os.environ.get("ARIZE_API_KEY")
    if not api_key:
        raise EnvironmentError("ARIZE_API_KEY must be set in eval/.env")
    return ArizeClient(api_key=api_key)


def create_dataset(client: ArizeClient, tasks: list[dict], name: str) -> str:
    """Upload tasks as an Arize AX dataset. Returns dataset_id."""
    space_id = os.environ.get("ARIZE_SPACE_ID")
    if not space_id:
        raise EnvironmentError("ARIZE_SPACE_ID must be set in eval/.env")

    df = pd.DataFrame({
        "attributes.input.value": [t["description"] for t in tasks],
        "attributes.output.value": [json.dumps(t.get("expected_output", {})) for t in tasks],
        "task_id": [t["id"] for t in tasks],
        "tier": [t["tier"] for t in tasks],
        "category": [t["category"] for t in tasks],
    })

    dataset = client.datasets.create(
        space_id=space_id,
        name=name,
        examples=df,
    )
    logger.info("Created dataset '%s' (id=%s) with %d tasks", name, dataset.id, len(tasks))
    return dataset.id


def run_experiment_for_arm(
    client: ArizeClient,
    dataset_id: str,
    tasks: list[dict],
    arm: str,
    repo: str,
    run_index: int,
    dry_run: bool = False,
) -> None:
    """Run one experiment iteration for a given arm."""
    options = get_arm_options(arm, repo)

    # Build a task lookup by description
    task_by_desc = {t["description"]: t for t in tasks}

    async def task_fn(dataset_row) -> str:
        """Arize experiment task function — runs Claude Code on the prompt."""
        description = dataset_row.get("attributes.input.value", "")
        result = await run_single_task(description, options)
        return json.dumps(result)

    def evaluator_fn(output: str, dataset_row) -> EvaluationResult:
        """Score the output against the task's expected output."""
        if output is None:
            return EvaluationResult(
                score=0, label="error",
                explanation="Task produced no output (likely errored).",
            )

        description = dataset_row.get("attributes.input.value", "")
        task = task_by_desc.get(description, {})

        # Parse the output JSON to get the text
        try:
            result = json.loads(output)
            output_text = result.get("output", output)
        except (json.JSONDecodeError, TypeError):
            output_text = output

        return evaluate_task(output_text or "", task)

    experiment_name = f"{arm}-run{run_index + 1}"
    logger.info("Running experiment: %s", experiment_name)

    experiment, experiment_df = client.experiments.run(
        name=experiment_name,
        dataset_id=dataset_id,
        task=task_fn,
        evaluators=[evaluator_fn],
        concurrency=1,  # Sequential to avoid rate limits
        exit_on_error=False,
        dry_run=dry_run,
        timeout=600,  # 10 minutes per task to avoid worker requeue
    )

    logger.info("Experiment %s complete. Results:\n%s", experiment_name, experiment_df.to_string())


def run_read_tasks(
    client: ArizeClient,
    tasks: list[dict],
    arms: list[str],
    repo: str,
    num_runs: int,
    dry_run: bool,
) -> None:
    """Run read/analysis tasks — no repo reset needed between runs."""
    if not tasks:
        return

    logger.info("=== Running %d read/analysis tasks ===", len(tasks))
    dataset_name = f"eval-read-{int(time.time())}"
    dataset_id = create_dataset(client, tasks, dataset_name)

    for arm in arms:
        for run_idx in range(num_runs):
            logger.info("--- %s run %d/%d ---", arm, run_idx + 1, num_runs)
            run_experiment_for_arm(client, dataset_id, tasks, arm, repo, run_idx, dry_run)


def run_write_tasks(
    client: ArizeClient,
    tasks: list[dict],
    arms: list[str],
    repo: str,
    num_runs: int,
    dry_run: bool,
) -> None:
    """Run write tasks — reset repo before each run."""
    if not tasks:
        return

    logger.info("=== Running %d write tasks ===", len(tasks))

    for task in tasks:
        task_list = [task]
        dataset_name = f"eval-write-{task['id']}-{int(time.time())}"
        dataset_id = create_dataset(client, task_list, dataset_name)

        for arm in arms:
            for run_idx in range(num_runs):
                logger.info("--- %s / %s run %d/%d ---", task["id"], arm, run_idx + 1, num_runs)

                # Reset repo state before each write task run
                if not dry_run:
                    logger.info("Resetting repo state...")
                    throttled_reset(repo, str(REPO_ROOT))

                run_experiment_for_arm(client, dataset_id, task_list, arm, repo, run_idx, dry_run)


def main():
    parser = argparse.ArgumentParser(description="MCP vs. Skill eval harness")
    parser.add_argument("--repo", default=os.environ.get("EVAL_REPO", ""), help="GitHub repo (owner/name)")
    parser.add_argument("--arm", choices=ARM_NAMES + ["all"], default="all", help="Which arm to run")
    parser.add_argument("--task", default=None, help="Task ID(s) to run, comma-separated (e.g. T01,T02)")
    parser.add_argument("--tier", type=int, default=None, choices=[1, 2, 3, 4], help="Run only tasks of this tier")
    parser.add_argument("--runs", type=int, default=5, help="Number of runs per task per arm")
    parser.add_argument("--dry-run", action="store_true", help="Dry run (don't log to Arize)")
    args = parser.parse_args()

    if not args.repo:
        parser.error("--repo is required (or set EVAL_REPO in eval/.env)")

    arms = ARM_NAMES if args.arm == "all" else [args.arm]
    tasks = load_tasks(task_filter=args.task, tier_filter=args.tier)

    if not tasks:
        logger.error("No tasks matched the filter criteria.")
        sys.exit(1)

    logger.info("Eval config: repo=%s, arms=%s, tasks=%d, runs=%d, dry_run=%s",
                args.repo, arms, len(tasks), args.runs, args.dry_run)

    client = create_arize_client()
    read_tasks, write_tasks = split_tasks(tasks)

    # Run read/analysis tasks first (no reset needed)
    run_read_tasks(client, read_tasks, arms, args.repo, args.runs, args.dry_run)

    # Run write tasks (reset between each run)
    run_write_tasks(client, write_tasks, arms, args.repo, args.runs, args.dry_run)

    logger.info("=== Eval complete! Check Arize AX dashboard for results. ===")


if __name__ == "__main__":
    main()
