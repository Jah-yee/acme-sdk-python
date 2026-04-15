# acme-sdk-python — Project State for Claude Code

## What This Repo Is

A fake-but-realistic Python SDK (`acme-sdk-python`) used as a **test bed** for an AI agent evaluation comparing two GitHub tool integration patterns:

- **MCP arm**: GitHub MCP server (`@modelcontextprotocol/server-github`)
- **Skill arms**: `gh` CLI reference skill files (two variants: LobeHub and Vault)

For a talk: "MCP vs. Command Line: A Head-to-Head Evaluation of Agent Tool Integration Patterns" (AI Engineer Miami).

**GitHub repo**: `seldo/acme-sdk-python`

---

## Status

All deliverables from the original spec are complete. The eval harness has been run end-to-end (Tier 1 dry run: 15/15 correct across all 3 arms). Ready for the full live run.

- `build_repo.sh` — initial scaffolding (not needed post-setup)
- `setup_github.sh` — idempotent GitHub metadata setup/reset
- `eval/tasks.json` — 25 tasks across 4 tiers (5/6/6/8)
- `eval/run_eval.py`, `arms.py`, `evaluators.py`, `resolve_numbers.py`, `rate_limit.py` — eval harness
- `eval/skills/` — both skill files (LobeHub, Vault)

The spec's `eval/reset_repo.sh` was dropped as redundant with `setup_github.sh`.

---

## How to Run the Eval

### 1. Restore GitHub repo state

```bash
cd /Users/laurievoss/projects/arize/demos/acme-sdk-python
./setup_github.sh seldo/acme-sdk-python
```

Takes ~5 min. Creates 12 open issues, 3 open PRs, 3 milestones. Issue/PR numbers are NOT baked into `tasks.json` — `resolve_numbers.py` substitutes them at runtime from `{{PLACEHOLDER}}` tokens.

### 2. Configure environment

```bash
cp eval/.env.example eval/.env
# Fill in: ARIZE_API_KEY, ARIZE_SPACE_ID, ANTHROPIC_API_KEY,
# GITHUB_PERSONAL_ACCESS_TOKEN, EVAL_REPO=seldo/acme-sdk-python
```

### 3. Install eval dependencies

```bash
cd eval
pip install -r requirements.txt
```

### 4. Run

```bash
# Tier 1 only, dry run (no Arize logging) — smoke test
python eval/run_eval.py --tier 1 --dry-run --repo seldo/acme-sdk-python

# Full 3-arm run, 5x per task
python eval/run_eval.py --repo seldo/acme-sdk-python

# Single arm, single task, 1 run
python eval/run_eval.py --arm mcp --task T01 --runs 1 --repo seldo/acme-sdk-python
```

**Running from inside a Claude Code session**: the harness spawns `claude` as a subprocess via `claude-agent-sdk`, which refuses to recurse. Strip the env vars first:

```bash
env -u CLAUDECODE -u CLAUDE_CODE_ENTRYPOINT python eval/run_eval.py ...
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
    ├── tasks.json          # 25 task definitions (uses {{PLACEHOLDER}} tokens)
    ├── README.md           # Eval framework overview
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
- **5 evaluators**: correctness, output_quality (LLM-as-judge, Tier 4 only), efficiency (tool calls vs. baseline), latency, tool_fidelity (did agent use the right integration pattern?)
- Results logged to **Arize AX** via their experiments API
- Write tasks reset repo state via `setup_github.sh` between runs (rate-limited by `rate_limit.py`)

---

## Placeholder Substitution

Issue and PR numbers in `tasks.json` use `{{PLACEHOLDER}}` tokens (e.g., `{{ISSUE_BATCH_SHUTDOWN}}`, `{{PR_CI_MATRIX}}`). `resolve_numbers.py` queries GitHub at eval startup and substitutes real numbers into the raw JSON before parsing. All 16 placeholders (13 issues + 3 PRs) are defined in `ISSUE_KEYS` and `PR_KEYS`.

Never hand-edit numbers back into `tasks.json`, and do not re-add the jq substitution block to `setup_github.sh` — placeholder resolution makes both unnecessary and conflicting.

---

## Arize SDK Usage Notes

`run_eval.py` uses `ArizeClient` from the `arize` package:
- `client.datasets.create(space_id, name, examples=df)`
- `client.experiments.run(name, dataset_id, task, evaluators, ...)`

Verify these match the current `arize` SDK before running — the SDK evolves.
