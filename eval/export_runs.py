#!/usr/bin/env python3
"""Export datasets + experiments + runs tagged 'pretty-good' from Arize AX.

Writes one JSON file per dataset to eval/exports/, containing the dataset
metadata, all examples, and every experiment with its runs (including
evaluator outputs stored in additional_properties).

The Arize SDK doesn't expose tags, so the list of 'pretty-good' datasets
is hardcoded below from the UI.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent / ".env")

from arize import ArizeClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("export")

EXPORT_DIR = Path(__file__).parent / "exports"

PRETTY_GOOD = [
    # Baseline arm run (3 passes in same datasets)
    "eval-read-20260415-195616",
    "eval-write-T12-20260415-201615",
    "eval-write-T13-20260415-201754",
    "eval-write-T14-20260415-203132",
    "eval-write-T15-20260415-203330",
    "eval-write-T16-20260415-203918",
    "eval-write-T17-20260415-204401",
    "eval-write-T17-20260415-154121",
    "eval-write-T16-20260415-154020",
    "eval-write-T15-20260415-153508",
    "eval-write-T14-20260415-153328",
    "eval-write-T13-20260415-152941",
    "eval-write-T12-20260415-152754",
    "eval-read-20260415-145247",
    "eval-write-T17-20260415-141658",
    "eval-write-T16-20260415-141550",
    "eval-write-T15-20260415-141423",
    "eval-write-T14-20260415-140910",
    "eval-write-T13-20260415-140551",
    "eval-write-T12-20260415-140407",
    "eval-read-20260415-132329",
    "eval-write-T17-20260415-095011",
    "eval-write-T16-20260415-093751",
    "eval-write-T15-20260415-092327",
    "eval-write-T14-20260415-091043",
    "eval-write-T13-20260415-085507",
    "eval-write-T12-20260415-084104",
    "eval-read-20260414-184839",
]


def _to_dict(obj):
    """Best-effort conversion of SDK model objects to plain dicts."""
    if hasattr(obj, "model_dump"):
        return obj.model_dump(mode="json")
    if hasattr(obj, "to_dict"):
        return obj.to_dict()
    return obj


def list_all_datasets(client: ArizeClient, space_id: str) -> list:
    """Paginate through all datasets in the space."""
    out = []
    cursor = None
    while True:
        resp = client.datasets.list(space=space_id, limit=100, cursor=cursor)
        out.extend(resp.datasets)
        cursor = getattr(resp.pagination, "next_cursor", None) if resp.pagination else None
        if not cursor:
            break
    return out


def list_all_experiments(client: ArizeClient, dataset_id: str) -> list:
    out = []
    cursor = None
    while True:
        resp = client.experiments.list(dataset=dataset_id, limit=100, cursor=cursor)
        out.extend(resp.experiments)
        cursor = getattr(resp.pagination, "next_cursor", None) if resp.pagination else None
        if not cursor:
            break
    return out


def main():
    api_key = os.environ["ARIZE_API_KEY"]
    space_id = os.environ["ARIZE_SPACE_ID"]
    client = ArizeClient(api_key=api_key)

    EXPORT_DIR.mkdir(exist_ok=True)

    logger.info("Listing datasets in space %s...", space_id)
    all_datasets = list_all_datasets(client, space_id)
    by_name = {d.name: d for d in all_datasets}

    missing = [n for n in PRETTY_GOOD if n not in by_name]
    if missing:
        logger.warning("Missing %d datasets: %s", len(missing), missing)

    targets = [by_name[n] for n in PRETTY_GOOD if n in by_name]
    logger.info("Exporting %d datasets...", len(targets))

    for ds in targets:
        out_file = EXPORT_DIR / f"{ds.name}.json"
        if out_file.exists():
            logger.info("Skip (exists): %s", out_file.name)
            continue

        logger.info("Fetching examples for %s (%s)...", ds.name, ds.id)
        ex_resp = client.datasets.list_examples(dataset=ds.id, all=True)
        examples = [_to_dict(e) for e in ex_resp.examples]

        experiments_out = []
        experiments = list_all_experiments(client, ds.id)
        logger.info("  %d experiments", len(experiments))
        for exp in experiments:
            # Use REST (all=False) — the Flight path (all=True) crashes pydantic
            # validation because the payload has `result` instead of `output`.
            runs_resp = client.experiments.list_runs(experiment=exp.id, limit=100)
            runs = [_to_dict(r) for r in runs_resp.experiment_runs]
            experiments_out.append({"experiment": _to_dict(exp), "runs": runs})

        payload = {
            "dataset": _to_dict(ds),
            "examples": examples,
            "experiments": experiments_out,
        }
        out_file.write_text(json.dumps(payload, indent=2, default=str))
        logger.info("  wrote %s (%d bytes)", out_file.name, out_file.stat().st_size)

    logger.info("Done. %d files in %s", len(list(EXPORT_DIR.glob('*.json'))), EXPORT_DIR)


if __name__ == "__main__":
    main()
