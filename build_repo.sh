#!/usr/bin/env bash
#
# build_repo.sh — Builds the acme-sdk-python repo from scratch with
# realistic git history, multiple contributors, and tagged releases.
#
# Usage:
#   ./build_repo.sh [target_dir]
#
# If target_dir is not specified, uses the current directory.
# The script expects all source files to already exist in the directory.

set -euo pipefail

TARGET_DIR="${1:-.}"
cd "$TARGET_DIR"

# ── Helpers ──────────────────────────────────────────────────────────────

# Authors
ALICE_NAME="Alice Chen"
ALICE_EMAIL="alice@acme-sdk.dev"
BOB_NAME="Bob Martinez"
BOB_EMAIL="bob@acme-sdk.dev"
CHARLIE_NAME="Charlie Kim"
CHARLIE_EMAIL="charlie@acme-sdk.dev"
DANA_NAME="Dana Okafor"
DANA_EMAIL="dana@acme-sdk.dev"

# Base date: 2024-04-01T10:00:00Z — we'll advance from here
BASE_TS=1711965600  # 2024-04-01T10:00:00Z
OFFSET=0

advance_time() {
  # Advance by a random amount between 2-8 hours
  local min_hours="${1:-2}"
  local max_hours="${2:-8}"
  local hours=$(( RANDOM % (max_hours - min_hours + 1) + min_hours ))
  OFFSET=$(( OFFSET + hours * 3600 ))
}

current_date() {
  date -u -r $(( BASE_TS + OFFSET )) "+%Y-%m-%dT%H:%M:%S+00:00" 2>/dev/null || \
  date -u -d "@$(( BASE_TS + OFFSET ))" "+%Y-%m-%dT%H:%M:%S+00:00"
}

commit_as() {
  local name="$1"
  local email="$2"
  local message="$3"
  shift 3
  local date_str
  date_str="$(current_date)"

  GIT_AUTHOR_NAME="$name" \
  GIT_AUTHOR_EMAIL="$email" \
  GIT_COMMITTER_NAME="$name" \
  GIT_COMMITTER_EMAIL="$email" \
  GIT_AUTHOR_DATE="$date_str" \
  GIT_COMMITTER_DATE="$date_str" \
  git commit "$@" -m "$message"
}

alice() { commit_as "$ALICE_NAME" "$ALICE_EMAIL" "$@"; }
bob()   { commit_as "$BOB_NAME" "$BOB_EMAIL" "$@"; }
charlie() { commit_as "$CHARLIE_NAME" "$CHARLIE_EMAIL" "$@"; }
dana()  { commit_as "$DANA_NAME" "$DANA_EMAIL" "$@"; }

# ── Initialize Repository ───────────────────────────────────────────────

# Clean any existing git history
rm -rf .git
git init -b main

# Create .gitignore
cat > .gitignore << 'EOF'
__pycache__/
*.py[cod]
*$py.class
*.egg-info/
dist/
build/
.eggs/
*.egg
.mypy_cache/
.pytest_cache/
.ruff_cache/
.coverage
htmlcov/
.tox/
.venv/
venv/
*.db
acme_traces/
EOF

# ── Commit 1: Initial project skeleton (Alice) ──────────────────────────

advance_time 0 0  # Start at base time
git add .gitignore
git add LICENSE
git add pyproject.toml
alice "chore: initialize project with packaging config and license"

# ── Commit 2: Add core data models (Alice) ──────────────────────────────

advance_time 3 6
git add src/acme_sdk/__init__.py
git add src/acme_sdk/models.py
alice "feat: add core data models for Trace, Span, Event, and Metric"

# ── Commit 3: Add authentication module (Alice) ─────────────────────────

advance_time 4 8
git add src/acme_sdk/auth.py
alice "feat: implement API key authentication provider"

# ── Commit 4: Add config module (Alice) ─────────────────────────────────

advance_time 2 5
git add src/acme_sdk/config.py
alice "feat: add configuration management with env var support"

# ── Commit 5: Add serialization utilities (Alice) ───────────────────────

advance_time 3 6
git add src/acme_sdk/utils/__init__.py
git add src/acme_sdk/utils/serialization.py
alice "feat: add OTLP-compatible serialization for spans and metrics"

# ── Commit 6: Add retry logic (Alice) ───────────────────────────────────

advance_time 4 8
git add src/acme_sdk/utils/retry.py
alice "feat: implement exponential backoff retry with jitter"

# ── Commit 7: Add HTTP client (Alice) ───────────────────────────────────

advance_time 6 12
git add src/acme_sdk/client.py
alice "feat: add AcmeClient HTTP client with auth and retry support"

# ── Commit 8: Add OTLP exporter (Alice) ─────────────────────────────────

advance_time 4 8
git add src/acme_sdk/exporters/__init__.py
git add src/acme_sdk/exporters/otlp.py
alice "feat: add OTLP HTTP exporter with batch chunking"

# ── Commit 9: Bob adds initial README (Bob) ─────────────────────────────

advance_time 2 5
git add README.md
bob "docs: add project README with installation and quickstart"

# ── Commit 10: Charlie sets up CI (Charlie) ─────────────────────────────

advance_time 3 6
git add .github/workflows/ci.yml
charlie "ci: add GitHub Actions workflow for pytest and ruff"

# ── Commit 11: Charlie adds issue and PR templates (Charlie) ────────────

advance_time 1 3
git add .github/ISSUE_TEMPLATE/bug_report.md
git add .github/ISSUE_TEMPLATE/feature_request.md
git add .github/PULL_REQUEST_TEMPLATE.md
charlie "chore: add issue and pull request templates"

# ── Commit 12: Alice adds test fixtures (Alice) ─────────────────────────

advance_time 4 8
git add tests/conftest.py
alice "test: add shared test fixtures and mock API setup"

# ── Commit 13: Alice adds client tests (Alice) ──────────────────────────

advance_time 3 6
git add tests/test_client.py
alice "test: add unit tests for AcmeClient"

# ── Commit 14: Alice adds auth tests (Alice) ────────────────────────────

advance_time 2 4
git add tests/test_auth.py
alice "test: add unit tests for API key and OAuth authentication"

# ── Commit 15: Alice adds model tests (Alice) ───────────────────────────

advance_time 2 5
git add tests/test_models.py
alice "test: add unit tests for Span, Trace, Event, and Metric models"

# ── Commit 16: Add OTLP exporter tests (Alice) ──────────────────────────

advance_time 3 6
git add tests/test_exporters/test_otlp.py
alice "test: add unit tests for OTLP exporter"

# ── Commit 17: Bob adds getting started docs (Bob) ──────────────────────

advance_time 4 8
git add docs/getting-started.md
bob "docs: add getting started guide"

# ── Commit 18: Bob adds config docs (Bob) ───────────────────────────────

advance_time 2 5
git add docs/configuration.md
bob "docs: add configuration reference"

# ── Commit 19: Bob adds basic tracing example (Bob) ─────────────────────

advance_time 3 6
git add examples/basic_tracing.py
bob "docs: add basic tracing example"

# ── Commit 20: Alice adds config file support (Alice) ───────────────────

advance_time 4 8
# Simulate adding TOML/YAML config file loading
# (already in config.py, but this represents the "feature commit")
# We'll update the __init__.py to bump to show progress
cat > src/acme_sdk/__init__.py << 'PYEOF'
"""Acme SDK for Python — observability data collection and export."""

from acme_sdk.client import AcmeClient
from acme_sdk.config import AcmeConfig
from acme_sdk.models import Event, Metric, Span, Trace

__version__ = "0.9.0"
__all__ = [
    "AcmeClient",
    "AcmeConfig",
    "Event",
    "Metric",
    "Span",
    "Trace",
    "__version__",
]
PYEOF
git add src/acme_sdk/__init__.py
alice "feat: add TOML and YAML config file parsing with env var interpolation"

# ── Commit 21: Dana fixes a bug in retry logic (Dana) ───────────────────

advance_time 6 12
# Simulate a bugfix — the retry was not respecting Retry-After header
# (Already fixed in our code, this is the "history" of fixing it)
git add src/acme_sdk/utils/retry.py
dana "fix: respect Retry-After header in retry backoff calculation"

# ── Commit 22: Alice adds retry tests (Alice) ───────────────────────────

advance_time 2 4
git add tests/test_utils/test_retry.py
alice "test: add comprehensive tests for retry logic including Retry-After"

# ── Commit 23: Charlie adds pyproject.toml dev deps (Charlie) ───────────

advance_time 3 6
git add pyproject.toml
charlie "chore: add dev dependencies (pytest, ruff, mypy) to pyproject.toml"

# ── Commit 24: Alice adds OAuth support (Alice) ─────────────────────────

advance_time 6 12
git add src/acme_sdk/auth.py
alice "feat: add OAuth 2.0 client credentials authentication"

# ── Commit 25: Bob updates README with OAuth docs (Bob) ─────────────────

advance_time 2 4
git add README.md
bob "docs: add OAuth 2.0 authentication section to README"

# ── Commit 26: Alice refactors models to use Pydantic v2 (Alice) ────────

advance_time 8 16
git add src/acme_sdk/models.py
git add tests/test_models.py
alice "refactor: migrate models to Pydantic v2 with field_validator"

# ── Commit 27: Dana fixes serialization for nested attributes (Dana) ────

advance_time 4 8
git add src/acme_sdk/utils/serialization.py
dana "fix: handle nested dict and list attribute serialization"

# ── Commit 28: CHANGELOG for v1.0.0 (Bob) ───────────────────────────────

advance_time 2 4
# Write the v1.0.0-only changelog
cat > CHANGELOG.md << 'CHEOF'
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2024-07-01

### Added
- Initial release of the Acme SDK for Python
- `AcmeClient` with HTTP transport
- Core data models: `Trace`, `Span`, `Event`, `Metric`
- OTLP HTTP exporter
- API key authentication
- OAuth 2.0 client credentials authentication
- Configuration via code, env vars, and config files
- Basic retry logic with exponential backoff
- Comprehensive test suite
- Documentation and examples

[1.0.0]: https://github.com/acme-corp/acme-sdk-python/releases/tag/v1.0.0
CHEOF
git add CHANGELOG.md
bob "docs: add CHANGELOG for v1.0.0 release"

# ── Commit 29: Version bump to 1.0.0 (Charlie) ─────────────────────────

advance_time 1 2
cat > src/acme_sdk/__init__.py << 'PYEOF'
"""Acme SDK for Python — observability data collection and export."""

from acme_sdk.client import AcmeClient
from acme_sdk.config import AcmeConfig
from acme_sdk.models import Event, Metric, Span, Trace

__version__ = "1.0.0"
__all__ = [
    "AcmeClient",
    "AcmeConfig",
    "Event",
    "Metric",
    "Span",
    "Trace",
    "__version__",
]
PYEOF
git add src/acme_sdk/__init__.py
charlie "chore: bump version to 1.0.0"

# ── TAG: v1.0.0 ─────────────────────────────────────────────────────────

git tag -a v1.0.0 -m "Release v1.0.0 — Initial release"

# ═══════════════════════════════════════════════════════════════════════
# POST-v1.0.0 DEVELOPMENT (toward v1.1.0)
# ═══════════════════════════════════════════════════════════════════════

# ── Commit 30: Alice adds JSON file exporter (Alice) ────────────────────

advance_time 8 16
git add src/acme_sdk/exporters/json_file.py
git add src/acme_sdk/exporters/__init__.py
alice "feat: add JSON file exporter for local trace storage"

# ── Commit 31: Alice adds JSON exporter tests (Alice) ───────────────────

advance_time 3 6
git add tests/test_exporters/test_json_file.py
alice "test: add unit tests for JSON file exporter"

# ── Commit 32: Alice adds console exporter (Alice) ──────────────────────

advance_time 6 12
git add src/acme_sdk/exporters/console.py
alice "feat: add console exporter with colorized output"

# ── Commit 33: Alice adds batch processing (Alice) ──────────────────────

advance_time 8 16
git add src/acme_sdk/utils/batching.py
alice "feat: add batch processor with configurable flush intervals"

# ── Commit 34: Alice adds batch processor tests (Alice) ─────────────────

advance_time 3 6
git add tests/test_utils/test_batching.py
alice "test: add unit tests for batch processor"

# ── Commit 35: Dana fixes OTLP batch size bug (Dana) ────────────────────

advance_time 4 8
# Simulate fixing a bug where OTLP exporter dropped spans > 1000
git add src/acme_sdk/exporters/otlp.py
dana "fix: OTLP exporter no longer drops spans when batch exceeds 1000"

# ── Commit 36: Bob adds exporters documentation (Bob) ───────────────────

advance_time 3 6
git add docs/exporters.md
bob "docs: add exporters guide covering OTLP, JSON, and console"

# ── Commit 37: Bob adds API reference (Bob) ─────────────────────────────

advance_time 4 8
git add docs/api-reference.md
bob "docs: add comprehensive API reference"

# ── Commit 38: Bob adds custom exporter example (Bob) ───────────────────

advance_time 2 5
git add examples/custom_exporter.py
bob "docs: add custom SQLite exporter example"

# ── Commit 39: Bob adds batch export example (Bob) ──────────────────────

advance_time 2 4
git add examples/batch_export.py
bob "docs: add batch export example with simulated traffic"

# ── Commit 40: Alice adds gzip compression to OTLP (Alice) ──────────────

advance_time 6 10
git add src/acme_sdk/exporters/otlp.py
git add src/acme_sdk/client.py
alice "feat: enable gzip compression by default in OTLP exporter"

# ── Commit 41: Charlie updates CI matrix (Charlie) ──────────────────────

advance_time 3 6
git add .github/workflows/ci.yml
charlie "ci: add Python 3.11 to CI test matrix"

# ── Commit 42: Dana fixes race condition in batch flush (Dana) ───────────

advance_time 8 14
git add src/acme_sdk/utils/batching.py
dana "fix: resolve race condition in batch exporter shutdown flush"

# ── Commit 43: Alice improves error messages (Alice) ────────────────────

advance_time 4 8
git add src/acme_sdk/auth.py
git add src/acme_sdk/client.py
alice "feat: improve error messages for authentication failures"

# ── Commit 44: CHANGELOG for v1.1.0 (Bob) ───────────────────────────────

advance_time 2 4
# Write the full changelog including v1.1.0
cat > CHANGELOG.md << 'CHEOF'
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.1.0] - 2024-09-15

### Added
- JSON file exporter for writing traces to local files
- Console exporter for development and debugging
- Batch processing utilities for high-throughput workloads
- OAuth 2.0 authentication support
- Configuration file support (YAML and TOML)
- Exponential backoff retry logic with jitter

### Changed
- OTLP exporter now supports gzip compression by default
- Client constructor accepts optional `timeout` parameter
- Improved error messages for authentication failures

### Fixed
- OTLP exporter no longer drops spans when batch size exceeds 1000
- Race condition in batch exporter flush on interpreter shutdown
- Config parser handles environment variable interpolation correctly

## [1.0.0] - 2024-07-01

### Added
- Initial release of the Acme SDK for Python
- `AcmeClient` with HTTP transport
- Core data models: `Trace`, `Span`, `Event`, `Metric`
- OTLP HTTP exporter
- API key authentication
- Basic retry logic
- Comprehensive test suite
- Documentation and examples

[Unreleased]: https://github.com/acme-corp/acme-sdk-python/compare/v1.1.0...HEAD
[1.1.0]: https://github.com/acme-corp/acme-sdk-python/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/acme-corp/acme-sdk-python/releases/tag/v1.0.0
CHEOF
git add CHANGELOG.md
bob "docs: update CHANGELOG for v1.1.0 release"

# ── Commit 45: Version bump to 1.1.0 (Charlie) ─────────────────────────

advance_time 1 2
cat > src/acme_sdk/__init__.py << 'PYEOF'
"""Acme SDK for Python — observability data collection and export."""

from acme_sdk.client import AcmeClient
from acme_sdk.config import AcmeConfig
from acme_sdk.models import Event, Metric, Span, Trace

__version__ = "1.1.0"
__all__ = [
    "AcmeClient",
    "AcmeConfig",
    "Event",
    "Metric",
    "Span",
    "Trace",
    "__version__",
]
PYEOF
git add src/acme_sdk/__init__.py
charlie "chore: bump version to 1.1.0"

# ── TAG: v1.1.0 ─────────────────────────────────────────────────────────

git tag -a v1.1.0 -m "Release v1.1.0 — Exporters, batch processing, and OAuth"

# ═══════════════════════════════════════════════════════════════════════
# POST-v1.1.0 DEVELOPMENT (HEAD)
# ═══════════════════════════════════════════════════════════════════════

# ── Commit 46: Alice adds console colorize option (Alice) ───────────────

advance_time 6 12
git add src/acme_sdk/exporters/console.py
alice "feat: add configurable colorized output to console exporter"

# ── Commit 47: Alice exposes retry attempt count (Alice) ─────────────────

advance_time 4 8
git add src/acme_sdk/utils/retry.py
alice "feat: expose retry attempt count in on_retry callback"

# ── Commit 48: Dana fixes JSON unicode handling (Dana) ──────────────────

advance_time 6 10
git add src/acme_sdk/exporters/json_file.py
dana "fix: handle unicode characters correctly in JSON file exporter"

# ── Commit 49: Bob updates CHANGELOG (Bob) ──────────────────────────────

advance_time 2 4
# Restore the final CHANGELOG with unreleased section
cat > CHANGELOG.md << 'CHEOF'
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Console exporter colorized output option
- Retry logic now exposes attempt count in callbacks

### Fixed
- JSON file exporter handles unicode characters correctly

## [1.1.0] - 2024-09-15

### Added
- JSON file exporter for writing traces to local files
- Console exporter for development and debugging
- Batch processing utilities for high-throughput workloads
- OAuth 2.0 authentication support
- Configuration file support (YAML and TOML)
- Exponential backoff retry logic with jitter

### Changed
- OTLP exporter now supports gzip compression by default
- Client constructor accepts optional `timeout` parameter
- Improved error messages for authentication failures

### Fixed
- OTLP exporter no longer drops spans when batch size exceeds 1000
- Race condition in batch exporter flush on interpreter shutdown
- Config parser handles environment variable interpolation correctly

## [1.0.0] - 2024-07-01

### Added
- Initial release of the Acme SDK for Python
- `AcmeClient` with HTTP transport
- Core data models: `Trace`, `Span`, `Event`, `Metric`
- OTLP HTTP exporter
- API key authentication
- Basic retry logic
- Comprehensive test suite
- Documentation and examples

[Unreleased]: https://github.com/acme-corp/acme-sdk-python/compare/v1.1.0...HEAD
[1.1.0]: https://github.com/acme-corp/acme-sdk-python/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/acme-corp/acme-sdk-python/releases/tag/v1.0.0
CHEOF
git add CHANGELOG.md
bob "docs: update CHANGELOG with unreleased changes"

# ── Commit 50: Charlie updates README support section (Charlie) ──────────

advance_time 3 6
git add README.md
charlie "docs: update README with support section and troubleshooting link"

# ── Commit 51: Add eval directory (Bob) ─────────────────────────────────

advance_time 2 4
git add eval/ || true  # May not exist yet during script creation
git add build_repo.sh setup_github.sh 2>/dev/null || true
bob "chore: add evaluation framework and build scripts" --allow-empty

echo ""
echo "✅ Repository built successfully!"
echo "   Commits: $(git rev-list --count HEAD)"
echo "   Tags: $(git tag | wc -l | tr -d ' ')"
echo "   Contributors: $(git shortlog -sn | wc -l | tr -d ' ')"
echo ""
echo "Next steps:"
echo "  1. Create a GitHub repo and push: git remote add origin <url> && git push -u origin main --tags"
echo "  2. Run setup_github.sh to create issues, PRs, labels, and milestones"
