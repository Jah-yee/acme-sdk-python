#!/usr/bin/env python3
"""Build a CSV summary of eval scores averaged across 3 passes.

Rows: one per (tier, task_id), sorted by tier then task_id.
Columns grouped by metric: for each metric, three arm columns (LobeHub, MCP, Vault).
A header row above the column names labels each triplet with the metric name.
"""

from __future__ import annotations

import csv
import json
import re
from collections import defaultdict
from pathlib import Path

EXPORT_DIR = Path(__file__).parent / "exports"
OUT_FILE = Path(__file__).parent / "summary.csv"

ARMS = ["baseline", "lobehub", "mcp", "vault"]
ARM_LABELS = {"baseline": "Baseline", "lobehub": "LobeHub", "mcp": "MCP", "vault": "Vault"}
EVAL_METRICS = ["correctness", "output_quality", "efficiency", "latency", "tool_fidelity"]
OUTPUT_METRICS = ["input_tokens", "output_tokens", "total_cost_usd", "latency_seconds"]
ALL_METRICS = EVAL_METRICS + OUTPUT_METRICS
METRIC_LABELS = {
    "correctness": "Correctness",
    "output_quality": "Output Quality",
    "efficiency": "Efficiency",
    "latency": "Latency",
    "tool_fidelity": "Tool Fidelity",
    "input_tokens": "Input Tokens",
    "output_tokens": "Output Tokens",
    "total_cost_usd": "Cost (USD)",
    "latency_seconds": "Latency (seconds)",
}


def group_key(name: str) -> str:
    m = re.match(r"eval-(read|write-T\d+)-\d+-\d+", name)
    return m.group(1) if m else name


def timestamp_key(name: str) -> str:
    m = re.search(r"(\d{8}-\d{6})$", name)
    return m.group(1) if m else ""


def main() -> None:
    files = sorted(EXPORT_DIR.glob("*.json"))
    by_group: dict[str, list[Path]] = defaultdict(list)
    for f in files:
        by_group[group_key(f.stem)].append(f)
    file_to_pass: dict[Path, int] = {}
    for group, paths in by_group.items():
        paths.sort(key=lambda p: timestamp_key(p.stem))
        for i, p in enumerate(paths, start=1):
            file_to_pass[p] = i

    # Collect per-run scores: scores[(tier, task_id)][(arm, metric)] = [score, ...]
    scores: dict[tuple, dict[tuple, list]] = defaultdict(lambda: defaultdict(list))
    row_meta: dict[tuple, dict] = {}

    for f in files:
        data = json.loads(f.read_text())
        pass_n = file_to_pass[f]

        ex_by_id: dict[str, dict] = {}
        for ex in data["examples"]:
            props = ex.get("additional_properties") or {}
            task_id = props.get("task_id")
            tier = props.get("tier")
            if task_id is None or tier is None:
                continue
            ex_by_id[ex["id"]] = {"task_id": task_id, "tier": float(tier), "category": props.get("category")}
            key = (float(tier), task_id)
            if key not in row_meta:
                row_meta[key] = {"tier": int(float(tier)), "task_id": task_id, "category": props.get("category")}

        for exp_entry in data["experiments"]:
            exp_name = exp_entry["experiment"]["name"]
            m = re.match(r"(baseline|lobehub|mcp|vault)-run\d+", exp_name)
            if not m:
                continue
            arm = m.group(1)

            for run in exp_entry["runs"]:
                ex_info = ex_by_id.get(run["example_id"])
                if not ex_info:
                    continue
                key = (ex_info["tier"], ex_info["task_id"])
                props = run.get("additional_properties") or {}
                for metric in EVAL_METRICS:
                    val = props.get(f"eval.{metric}.score")
                    if val is not None:
                        try:
                            scores[key][(arm, metric)].append(float(val))
                        except (ValueError, TypeError):
                            pass
                # Extract token/cost/latency from the output JSON
                try:
                    result = json.loads(run.get("output") or "{}")
                except (json.JSONDecodeError, TypeError):
                    result = {}
                for metric in OUTPUT_METRICS:
                    val = result.get(metric)
                    if val is not None:
                        try:
                            scores[key][(arm, metric)].append(float(val))
                        except (ValueError, TypeError):
                            pass

    # Column layout: tier, task_id, category, then per-metric triplets
    meta_cols = ["tier", "task_id", "category"]
    data_cols = []
    for metric in ALL_METRICS:
        for arm in ARMS:
            data_cols.append((metric, arm))

    # Build group header row (metric name above each triplet)
    group_header = ["", "", ""]
    for metric in ALL_METRICS:
        group_header.append(METRIC_LABELS[metric])
        group_header.extend([""] * (len(ARMS) - 1))  # blanks for the rest of the arm group

    # Build column name row
    col_names = meta_cols[:]
    for metric, arm in data_cols:
        col_names.append(ARM_LABELS[arm])

    with OUT_FILE.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(group_header)
        w.writerow(col_names)
        for key in sorted(row_meta.keys()):
            meta = row_meta[key]
            row = [meta["tier"], meta["task_id"], meta["category"]]
            for metric, arm in data_cols:
                vals = scores[key].get((arm, metric), [])
                if vals:
                    avg = sum(vals) / len(vals)
                    if metric in ("input_tokens", "output_tokens"):
                        row.append(int(round(avg)))
                    elif metric == "total_cost_usd":
                        row.append(round(avg, 4))
                    elif metric == "latency_seconds":
                        row.append(round(avg, 1))
                    else:
                        row.append(round(avg, 3))
                else:
                    row.append("")
            w.writerow(row)

    print(f"Wrote {OUT_FILE} ({len(row_meta)} tasks, {len(data_cols)} metric columns)")


if __name__ == "__main__":
    main()
