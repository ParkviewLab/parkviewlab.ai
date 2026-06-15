#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Gary Frattarola <garyf@parkviewlab.ai>
# SPDX-License-Identifier: LicenseRef-AllRightsReserved
"""
Stamp each page's "This page updated on <date>" from its git last-commit date.

Replaces the literal token STAMP_DATE in every *.html under --dir with that file's
last-commit date (formatted "June 1, 2026"), looked up in --git-dir's history.
Files with no commit yet (new/uncommitted) fall back to today, so a local preview
of unsaved edits shows today's date. Generated pages (the releases page) don't
carry the token and are skipped.

Runs in the deploy (in place, on the ephemeral checkout) and from
scripts/preview.sh (on a throwaway copy, so the working tree keeps the STAMP_DATE
placeholder). Stdlib only. See the handbook's website.md.

Usage: python3 scripts/stamp.py [--dir .] [--git-dir <same as --dir>]
"""

import argparse
import datetime as dt
import os
import subprocess

TOKEN = "STAMP_DATE"


def human_date(d):
    # "June 1, 2026" — month name, no zero-padded day, portably.
    return f"{d:%B} {d.day}, {d.year}"


def git_date(git_dir, relpath):
    """Last-commit date for relpath, or today if it isn't committed yet."""
    try:
        out = subprocess.run(
            ["git", "-C", git_dir, "log", "-1", "--format=%cs", "--", relpath],
            capture_output=True, text=True, check=False,
        ).stdout.strip()
        if out:
            return dt.date.fromisoformat(out)
    except Exception:  # noqa: BLE001
        pass
    return dt.date.today()


def main():
    ap = argparse.ArgumentParser(description="Stamp page 'updated on' dates from git.")
    ap.add_argument("--dir", default=".", help="directory of HTML to stamp (default: .)")
    ap.add_argument("--git-dir", default=None, help="repo for date lookups (default: --dir)")
    args = ap.parse_args()
    root = os.path.abspath(args.dir)
    git_dir = os.path.abspath(args.git_dir) if args.git_dir else root

    stamped = 0
    for dirpath, _dirs, files in os.walk(root):
        for fn in files:
            if not fn.endswith(".html"):
                continue
            path = os.path.join(dirpath, fn)
            with open(path, encoding="utf-8") as f:
                html = f.read()
            if TOKEN not in html:
                continue
            relpath = os.path.relpath(path, root)
            date = human_date(git_date(git_dir, relpath))
            with open(path, "w", encoding="utf-8") as f:
                f.write(html.replace(TOKEN, date))
            print(f"  stamped {relpath} -> {date}")
            stamped += 1
    if not stamped:
        print("  (no pages with STAMP_DATE to stamp)")


if __name__ == "__main__":
    main()
