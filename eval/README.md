# MCP vs. Skill Evaluation Framework

## Experiment: "MCP vs. Command Line: A Head-to-Head Evaluation of Agent Tool Integration Patterns"

This directory contains the evaluation framework for comparing how AI agents perform GitHub operations using two different tool integration patterns:

- **Pattern A (MCP):** GitHub MCP server (`@modelcontextprotocol/server-github`) providing typed tool schemas
- **Pattern B (Skill/CLI):** SKILL.md files teaching the agent to use the `gh` CLI via bash commands

### 3-Arm Design

| Arm | Tool Pattern | Specific Tool | Description |
|-----|-------------|---------------|-------------|
| 1   | MCP         | `@modelcontextprotocol/server-github` | Typed tool schemas for GitHub operations |
| 2   | Skill       | `github-awesome-copilot-gh-cli` (LobeHub) | Comprehensive `gh` CLI reference |
| 3   | Skill       | `github-cli` (claude-skills-vault) | Opinionated, safety-tiered `gh` CLI guide |

The 2-skill design tests whether skill **quality** matters alongside whether skills can match MCP performance.

## Task Dataset

### `tasks.json`

Contains 25 evaluation tasks across 4 tiers:

| Tier | Count | Type | Example |
|------|-------|------|---------|
| 1    | 5     | Single-operation lookups | "How many open bugs?" |
| 2    | 6     | Multi-step reads | "Which bugs have PRs?" |
| 3    | 6     | Write operations | "Create an issue and add it to a milestone" |
| 4    | 8     | Analysis/synthesis | "Compare v1.0.0 and v1.1.0 milestones" |

### Task Categories

- **read**: Queries that don't modify repo state
- **write**: Operations that create/modify issues, PRs, branches, labels
- **analysis**: Complex reasoning over repo data (milestones, labels, PR audits, cross-referencing)

## Metrics

Captured via Arize AX tracing (OpenTelemetry):

| Metric | Description |
|--------|-------------|
| Task completion | Binary: did the agent complete the task? |
| Output quality | LLM-as-judge scoring (1-5) against expected output |
| Tool correctness | Were the right tools called with correct parameters? |
| Trajectory efficiency | Number of tool calls / minimum required calls |
| Token consumption | Total input + output tokens |
| Latency | Wall-clock time from prompt to completion |
| Run-to-run variance | Std dev across 5 runs per task |

Each task is run **5 times** per arm to measure variance.

## Running the Evaluation

### Prerequisites

1. The `acme-sdk-python` repo must be pushed to GitHub
2. `setup_github.sh` must have been run to create issues, PRs, etc.
3. Credentials configured in `eval/.env` (see `.env.example`)

Issue/PR numbers are NOT baked into `tasks.json` — `resolve_numbers.py` substitutes `{{PLACEHOLDER}}` tokens from the live repo at runtime.

### Setup

```bash
# 1. Push to GitHub (if not already done)
gh repo create <org>/acme-sdk-python --public --source=. --push

# 2. Create GitHub metadata (issues, PRs, labels, milestones)
./setup_github.sh <org>/acme-sdk-python
```

### Running from inside a Claude Code session

The harness spawns `claude` as a subprocess via `claude-agent-sdk`, which refuses to recurse. Strip the env vars first:

```bash
env -u CLAUDECODE -u CLAUDE_CODE_ENTRYPOINT python run_eval.py ...
```

### Between Runs

After each write-operation task run, reset the repo by re-running `setup_github.sh`:

```bash
./setup_github.sh <org>/acme-sdk-python
```

### Task Execution Order

1. Run all **Tier 1-2 read tasks** first (no reset needed between them)
2. Run **Tier 3 write tasks** one at a time, resetting between each
3. Run **Tier 4 analysis tasks** (read-only, no reset needed)

## Files

| File | Purpose |
|------|---------|
| `tasks.json` | 25 task definitions with expected outputs |
| `run_eval.py` | Main eval harness (Arize AX integration) |
| `arms.py` | 3-arm configurations (mcp, lobehub, vault) |
| `evaluators.py` | 5 scoring evaluators |
| `resolve_numbers.py` | Dynamic issue/PR number resolution |
| `skills/` | Skill files for the two CLI arms |
| `README.md` | This file |

## Important Notes

- **Issue numbers**: `setup_github.sh` creates issues sequentially; numbers increment with each run. `resolve_numbers.py` resolves `{{PLACEHOLDER}}` tokens in all task descriptions, notes, criteria, and state checks at runtime — no manual updating needed. `setup_github.sh` does NOT write numbers into `tasks.json`; do not re-add the jq substitution block that used to live there.
- **Idempotency**: `setup_github.sh` is safe to run multiple times — it cleans up previous state before recreating.
- **Ground truth**: For Tier 4 analysis tasks, ground truth is evaluated by LLM-as-judge against criteria, not exact match.
- **Timing**: Issue open/close timestamps will be artificial (created in the same script run). Task T22 results should note this.
