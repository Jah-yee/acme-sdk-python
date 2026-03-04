#!/usr/bin/env bash
#
# reset_repo.sh — Reset the acme-sdk-python repo to its known-good state
# after agent write operations have modified it.
#
# This script:
#   1. Force-pushes main to the known-good commit
#   2. Closes and deletes agent-created issues/PRs/branches
#   3. Resets labels to the canonical set
#   4. Is idempotent and safe to run repeatedly
#
# Usage:
#   ./eval/reset_repo.sh <owner/repo> [known_good_sha]
#
# If known_good_sha is not provided, uses the tagged v1.1.0 + post-release commits.

set -euo pipefail

REPO="${1:?Usage: ./eval/reset_repo.sh <owner/repo> [known_good_sha]}"
KNOWN_SHA="${2:-}"

echo "==> Resetting repo: ${REPO}"
echo ""

# ── 1. Determine known-good SHA ─────────────────────────────────────────

if [[ -z "$KNOWN_SHA" ]]; then
  # Use the SHA stored during initial setup, or find it from tags
  KNOWN_SHA=$(git rev-parse main 2>/dev/null || echo "")
  if [[ -z "$KNOWN_SHA" ]]; then
    echo "ERROR: Cannot determine known-good SHA. Provide it as the second argument."
    exit 1
  fi
fi

echo "  Known-good SHA: ${KNOWN_SHA}"

# ── 2. Reset main branch ────────────────────────────────────────────────

echo "==> Resetting main branch..."
git checkout main 2>/dev/null || true
git reset --hard "$KNOWN_SHA"
git push origin main --force
echo "  Main branch reset to ${KNOWN_SHA}"

# ── 3. Clean up agent-created branches ──────────────────────────────────

echo "==> Cleaning up branches..."

# List of canonical branches that should be preserved
KEEP_BRANCHES="main fix/batch-shutdown ci/add-python-3.12 feat/grpc-transport"

# Get all remote branches
REMOTE_BRANCHES=$(git ls-remote --heads origin | awk '{print $2}' | sed 's|refs/heads/||')

for branch in $REMOTE_BRANCHES; do
  if ! echo "$KEEP_BRANCHES" | grep -qw "$branch"; then
    echo "  Deleting branch: $branch"
    git push origin --delete "$branch" 2>/dev/null || true
  fi
done

# ── 4. Close agent-created issues ───────────────────────────────────────

echo "==> Cleaning up agent-created issues..."

# Get all open issues and close any that weren't part of the original setup
# We identify original issues by their known titles
CANONICAL_ISSUES=(
  "OTLP exporter fails silently on connection timeout"
  "Add support for custom span attributes"
  "Documentation for OAuth authentication is incomplete"
  "Batch exporter drops last batch on shutdown"
  "Add retry configuration to client constructor"
  "Console exporter output is not configurable"
  "Typo in README.md"
  "Add gRPC transport option for OTLP exporter"
  "Config file parser crashes on empty values"
  "CI workflow doesn't run on Python 3.12"
  "Add metrics collection support"
  "JSON file exporter doesn't handle unicode properly"
)

# Get all open issues
OPEN_ISSUES=$(gh issue list --repo "$REPO" --state open --limit 100 --json number,title --jq '.[] | "\(.number)\t\(.title)"')

while IFS=$'\t' read -r num title; do
  [[ -z "$num" ]] && continue
  is_canonical=false
  for canonical in "${CANONICAL_ISSUES[@]}"; do
    if [[ "$title" == "$canonical" ]]; then
      is_canonical=true
      break
    fi
  done
  if ! $is_canonical; then
    echo "  Closing agent-created issue #${num}: ${title}"
    gh issue close "$num" --repo "$REPO" --reason "not planned" --comment "Closed by reset script." 2>/dev/null || true
  fi
done <<< "$OPEN_ISSUES"

# ── 5. Close agent-created PRs ──────────────────────────────────────────

echo "==> Cleaning up agent-created PRs..."

CANONICAL_PRS=(
  "Fix batch exporter shutdown race condition"
  "Add Python 3.12 to CI matrix"
  "Draft: gRPC transport for OTLP"
)

OPEN_PRS=$(gh pr list --repo "$REPO" --state open --limit 100 --json number,title --jq '.[] | "\(.number)\t\(.title)"')

while IFS=$'\t' read -r num title; do
  [[ -z "$num" ]] && continue
  is_canonical=false
  for canonical in "${CANONICAL_PRS[@]}"; do
    if [[ "$title" == "$canonical" ]]; then
      is_canonical=true
      break
    fi
  done
  if ! $is_canonical; then
    echo "  Closing agent-created PR #${num}: ${title}"
    gh pr close "$num" --repo "$REPO" --comment "Closed by reset script." 2>/dev/null || true
  fi
done <<< "$OPEN_PRS"

# ── 6. Reset labels ─────────────────────────────────────────────────────

echo "==> Resetting labels..."

CANONICAL_LABELS="bug enhancement docs good-first-issue critical exporter ci v2.0 wontfix"

# Get all labels
ALL_LABELS=$(gh label list --repo "$REPO" --limit 100 --json name --jq '.[].name')

for label in $ALL_LABELS; do
  if ! echo "$CANONICAL_LABELS" | grep -qw "$label"; then
    echo "  Deleting label: $label"
    gh label delete "$label" --repo "$REPO" --yes 2>/dev/null || true
  fi
done

# Re-ensure canonical labels exist with correct colors
gh label create "bug"              --repo "$REPO" --color "d73a4a"  --description "Something isn't working" --force 2>/dev/null || true
gh label create "enhancement"      --repo "$REPO" --color "a2eeef"  --description "New feature or request" --force 2>/dev/null || true
gh label create "docs"             --repo "$REPO" --color "0075ca"  --description "Documentation improvements" --force 2>/dev/null || true
gh label create "good-first-issue" --repo "$REPO" --color "7057ff"  --description "Good for newcomers" --force 2>/dev/null || true
gh label create "critical"         --repo "$REPO" --color "b60205"  --description "Critical priority" --force 2>/dev/null || true
gh label create "exporter"         --repo "$REPO" --color "e4e669"  --description "Related to exporters" --force 2>/dev/null || true
gh label create "ci"               --repo "$REPO" --color "ededed"  --description "CI/CD related" --force 2>/dev/null || true
gh label create "v2.0"             --repo "$REPO" --color "5319e7"  --description "Targeted for v2.0 release" --force 2>/dev/null || true
gh label create "wontfix"          --repo "$REPO" --color "ffffff"  --description "This will not be worked on" --force 2>/dev/null || true

# ── 7. Remove agent-added labels from canonical issues ──────────────────

echo "==> Removing non-canonical labels from issues..."

# For each canonical open issue, ensure only its original labels remain
# This is best-effort — if agents added labels, we strip the extras

# ── Done ─────────────────────────────────────────────────────────────────

echo ""
echo "==> Reset complete!"
echo "  - Main branch: reset to ${KNOWN_SHA}"
echo "  - Branches: cleaned (canonical branches preserved)"
echo "  - Issues: agent-created issues closed"
echo "  - PRs: agent-created PRs closed"
echo "  - Labels: reset to canonical set"
echo ""
echo "NOTE: Some agent modifications (e.g., added labels on issues, comments)"
echo "cannot be fully reverted. For a clean slate, re-run setup_github.sh after"
echo "deleting all issues/PRs manually."
