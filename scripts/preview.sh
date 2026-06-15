#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Gary Frattarola <garyf@parkviewlab.ai>
# SPDX-License-Identifier: LicenseRef-AllRightsReserved
#
# Local preview — build + stamp the site exactly as the deploy does, into a
# throwaway dir, and serve it on localhost. The working tree is left untouched
# (the built releases page and the stamped dates are build artifacts). Review
# here, then publish by promoting staging -> live. See the handbook's website.md.
#
# Usage: scripts/preview.sh [port]   (default port 8000)

set -euo pipefail

PORT="${1:-8000}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="$(mktemp -d -t parkviewlab-preview.XXXXXX)"
trap 'rm -rf "$OUT"' EXIT

# Copy the repo (minus VCS) into the throwaway dir so we never edit the worktree.
rsync -a --exclude '.git' "$ROOT"/ "$OUT"/

# Build the releases page (fresh) and stamp the page dates from ROOT's git history.
( cd "$OUT" && python3 build.py )
python3 "$ROOT/scripts/stamp.py" --dir "$OUT" --git-dir "$ROOT"

echo
echo "Preview ready — open http://localhost:$PORT"
echo "(Ctrl-C to stop. Nothing is published; this is a throwaway copy.)"
( cd "$OUT" && python3 -m http.server "$PORT" )
