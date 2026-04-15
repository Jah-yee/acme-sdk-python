# acme-sdk-python — Project State for Claude Code

## What This Repo Is

A fake-but-realistic Python SDK (`acme-sdk-python`) used as a **test bed** for an AI agent evaluation comparing two GitHub tool integration patterns:

- **MCP arm**: GitHub MCP server (`@modelcontextprotocol/server-github`)
- **Skill arms**: `gh` CLI reference skill files (two variants: LobeHub and Vault)

This is for a talk: "MCP vs. Command Line: A Head-to-Head Evaluation of Agent Tool Integration Patterns" (AI Engineer Miami).

**GitHub repo**: `seldo/acme-sdk-python`

---

## What Was Originally Requested vs. What Was Built

### ✅ Completed

| Deliverable | Status | Notes |
|---|---|---|
| SDK source code (`src/acme_sdk/`) | ✅ Done | Full implementation: client, models, auth, exporters, utils |
| Tests (`tests/`) | ✅ Done | Full test suite |
| Docs (`docs/`) | ✅ Done | 4 doc files |
| Examples (`examples/`) | ✅ Done | 3 example scripts |
| `.github/` templates | ✅ Done | Issue + PR templates |
| `pyproject.toml`, `LICENSE`, etc. | ✅ Done | |
| `build_repo.sh` | ✅ Done | Initial repo scaffolding script (not needed post-setup) |
| `setup_github.sh` | ✅ Done | Creates all GitHub metadata; also serves as reset |
| `eval/tasks.json` | ✅ Done | 25 tasks, but see **Known Bugs** below |
| `eval/README.md` | ✅ Done | Stale: still references deleted `reset_repo.sh` |
| Eval harness (`eval/run_eval.py`) | ✅ Done (bonus) | Never been run end-to-end |
| `eval/arms.py` | ✅ Done | 3-arm config (mcp, lobehub, vault) |
| `eval/evaluators.py` | ✅ Done | 5 evaluators: correctness, quality, efficiency, latency, fidelity |
| `eval/resolve_numbers.py` | ✅ Done | Dynamically resolves `{{ISSUE_*}}` / `{{PR_*}}` placeholders |
| `eval/rate_limit.py` | ✅ Done | Rate limiting for setup_github.sh calls |
| `eval/skills/` | ✅ Done | Both skill files present |

### ⚠️ Gaps vs. Original Spec

**1. `eval/reset_repo.sh` was removed**

Was in the original spec; was deleted as redundant because `setup_github.sh` handles both setup and idempotent cleanup.

`eval/README.md` still references it — needs updating.

**2. GitHub repo state is stale**

`setup_github.sh` has been run many times, leaving ~700+ orphaned closed issues/PRs. As of last check, only 1 open issue exists (#732 OTLP timeout). The repo needs `setup_github.sh seldo/acme-sdk-python` re-run to restore the full 12-open-issues + 3-open-PRs state.

---

## Known Bugs in tasks.json

All previously known bugs have been fixed:
- T01 explanation now lists all 5 open bugs (was missing the JSON unicode bug).
- T02 explanation now correctly notes assignees fail silently (value `"no"` was always correct).
- All hardcoded `#NNN` issue/PR numbers in Tier 1-3 descriptions/notes/state_checks were converted to `{{PLACEHOLDER}}` tokens, so `resolve_numbers.py` substitutes current numbers at runtime.

---

## How to Run the Eval

### 1. Restore GitHub repo state

```bash
cd /Users/laurievoss/projects/arize/demos/acme-sdk-python
./setup_github.sh seldo/acme-sdk-python
```

This takes ~5 min. After running, note the new issue/PR numbers printed at the end — they'll be needed.

### 2. Configure environment

```bash
cp eval/.env.example eval/.env
# Fill in:
# ARIZE_API_KEY=
# ARIZE_SPACE_ID=
# ANTHROPIC_API_KEY=
# GITHUB_PERSONAL_ACCESS_TOKEN=
# EVAL_REPO=seldo/acme-sdk-python
```

### 3. Install eval dependencies

```bash
cd eval
pip install -r requirements.txt
```

### 4. Run

```bash
# Full 3-arm run, 5x per task
python eval/run_eval.py --repo seldo/acme-sdk-python

# Single arm, single task, 1 run
python eval/run_eval.py --arm mcp --task T01 --runs 1

# Tier 1 only, dry run (no Arize logging)
python eval/run_eval.py --tier 1 --dry-run
```

---

## File Map

```
acme-sdk-python/
├── build_repo.sh           # Initial scaffolding script (not needed post-setup)
├── setup_github.sh         # Creates/resets GitHub issues, PRs, labels, milestones
├── src/acme_sdk/           # Fake SDK source
├── tests/                  # Test suite
├── docs/                   # Documentation
├── examples/               # Usage examples
└── eval/
    ├── run_eval.py         # Main eval harness
    ├── arms.py             # 3-arm configurations (mcp, lobehub, vault)
    ├── evaluators.py       # 5 scoring evaluators
    ├── rate_limit.py       # Rate limiting for reset calls
    ├── resolve_numbers.py  # Dynamic issue/PR number resolution
    ├── tasks.json          # 25 task definitions (see Known Bugs above)
    ├── README.md           # Stale: references deleted reset_repo.sh
    ├── .env.example        # Template for required credentials
    └── skills/
        ├── gh-cli-lobehub.md     # LobeHub gh CLI skill
        └── github-cli-vault.md   # Vault gh CLI skill
```

---

## Eval Design Summary

- **3 arms**: MCP (GitHub MCP server), Skill-LobeHub, Skill-Vault
- **25 tasks** across 4 tiers (5 / 6 / 6 / 8)
- **5 runs per task** per arm for variance measurement
- **5 evaluators**: correctness, output_quality (LLM-as-judge), efficiency (tool calls vs. baseline), latency, tool_fidelity (did agent use the right integration pattern?)
- Results logged to **Arize AX** via their experiments API
- Write tasks reset repo state via `setup_github.sh` between runs (via `throttled_reset` in `rate_limit.py`)

---

## Arize SDK Usage Notes

`run_eval.py` uses `ArizeClient` from `arize` package. The API calls used are:
- `client.datasets.create(space_id, name, examples=df)`
- `client.experiments.run(name, dataset_id, task, evaluators, ...)`

Verify these match the current `arize` SDK before running — the SDK evolves.

---

## Task Number Translation

After `setup_github.sh` runs, issue numbers increment because GitHub numbers are sequential. The `resolve_numbers.py` module handles placeholders in the task JSON body (e.g., `{{ISSUE_BATCH_SHUTDOWN}}` → 735), but **task description strings** with hardcoded numbers (T02, T14, T16, T17) need manual updating after a reset. This is a known limitation.
