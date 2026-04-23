#!/usr/bin/env bash
# setup-dev.sh — one-time developer environment setup
#
# Run once after cloning:
#   chmod +x setup-dev.sh && ./setup-dev.sh
#
# What it does:
#   1. Configures git to use the repo's .githooks/ directory.
#   2. Makes hook scripts executable.
#   3. Creates a Python venv and installs test dependencies.
#   4. Writes a repo-local git identity (rubeecube) if the current global
#      identity matches a blocked pattern.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$REPO_ROOT"

echo "=== Auto Print dev setup ==="

# ── 1. Hook path ──────────────────────────────────────────────────────────────
echo "→ Setting core.hooksPath = .githooks"
git config core.hooksPath .githooks
chmod +x .githooks/pre-commit .githooks/pre-push
echo "  Hooks installed."

# ── 2. Block forbidden global identity ───────────────────────────────────────
BLOCKED_EMAILS=("")
CURRENT_EMAIL=$(git config --global user.email 2>/dev/null || echo "")

for blocked in "${BLOCKED_EMAILS[@]}"; do
    if [[ "$CURRENT_EMAIL" == "$blocked" ]]; then
        echo ""
        echo "  ⚠ Global git email is $CURRENT_EMAIL (blocked for this repo)."
        echo "    Setting a repo-local identity instead..."
        git config user.name  "rubeecube"
        git config user.email "rubeecube@users.noreply.github.com"
        echo "  Repo-local identity set to rubeecube."
        break
    fi
done

# ── 3. Python venv ────────────────────────────────────────────────────────────
if [[ ! -d venv ]]; then
    echo "→ Creating Python venv"
    python3 -m venv venv
fi

echo "→ Installing test dependencies"
venv/bin/pip install --quiet -r requirements-test.txt

echo ""
echo "=== Setup complete. Run tests with: ==="
echo "    ./venv/bin/pytest tests/ -v"
