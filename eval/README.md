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
| 4    | 8     | Analysis/synthesis | "Generate a changelog between two tags" |

### Task Categories

- **read**: Queries that don't modify repo state
- **write**: Operations that create/modify issues, PRs, branches, labels
- **analysis**: Complex reasoning over repo data (git history, cross-referencing)

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
3. Note the actual issue/PR numbers and update `tasks.json` if they differ from defaults

### Setup

```bash
# 1. Build the repo (if not already done)
./build_repo.sh

# 2. Push to GitHub
gh repo create <org>/acme-sdk-python --public --source=. --push

# 3. Create GitHub metadata
./setup_github.sh <org>/acme-sdk-python

# 4. Note issue/PR numbers and update tasks.json
```

### Between Runs

After each write-operation task run, reset the repo:

```bash
./eval/reset_repo.sh <org>/acme-sdk-python [known_good_sha]
```

### Task Execution Order

1. Run all **Tier 1-2 read tasks** first (no reset needed between them)
2. Run **Tier 3 write tasks** one at a time, resetting between each
3. Run **Tier 4 analysis tasks** (read-only, no reset needed)

## Files

| File | Purpose |
|------|---------|
| `tasks.json` | 25 task definitions with expected outputs |
| `reset_repo.sh` | Resets repo state after write operations |
| `README.md` | This file |

## Important Notes

- **Issue numbers**: The `setup_github.sh` script creates issues sequentially. The actual numbers depend on whether the repo is fresh. Always verify issue numbers match `tasks.json`.
- **Idempotency**: `reset_repo.sh` is safe to run multiple times.
- **Ground truth**: For Tier 4 analysis tasks, ground truth is evaluated by LLM-as-judge against criteria, not exact match.
- **Timing**: Issue open/close timestamps will be artificial (created in the same script run). Task T22 results should note this.
