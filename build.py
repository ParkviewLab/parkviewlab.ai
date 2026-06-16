#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Gary Frattarola <garyf@parkviewlab.ai>
# SPDX-License-Identifier: LicenseRef-AllRightsReserved
"""
ParkviewLab releases page builder.

Renders releases/index.html — the "current releases" page. Each run fetches the
latest published version of every tracked project (PyPI / npm). Curated projects
(PROJECTS) get a full card plus a summary-table row; any *other* public repo in
the org (minus DENYLIST) gets a summary-table row only — so a newly-released
project shows up automatically and a human can promote it to a full card later
(the hybrid model; see the handbook's website.md).

For a project that publishes **GitHub Releases**, the card shows that release's
real per-version notes (the body, rendered from Markdown), with links to the
Release and CHANGELOG. Projects that don't publish Releases yet fall back to a
surface summary written from their README.

The page is a build artifact: rendered fresh at deploy (and by the local preview,
scripts/preview.sh) and NOT committed to git (.gitignore'd). Per-page "updated on"
dates are stamped separately by scripts/stamp.py.

Stdlib only (Python 3.9+). No third-party dependencies.

Usage:
    python3 build.py            # render releases/index.html
    python3 build.py --check    # report versions + discovered repos; write nothing

Adding a project as a full card: append an entry to PROJECTS below.
"""

import argparse
import datetime as dt
import html
import json
import os
import re
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ORG = "ParkviewLab"
UA = {"User-Agent": "parkviewlab-releases-builder"}

# Visible footer copyright (matches the per-file SPDX headers).
COPYRIGHT = "Copyright © 2026 Gary Frattarola"
CONTACT = "garyf@parkviewlab.ai"

# Public org repos that are NOT shippable products, so they're never listed:
# the websites themselves, the docs handbook, shared dev tooling, the desktop GUI.
DENYLIST = {"parkviewlab.ai", "zoestum.ai", "handbook", "dev-tools", "pvl-dotview"}

# ---------------------------------------------------------------------------
# Tracked projects. `source` is how we discover the current published version:
#   ("pypi", "<pypi-name>")  or  ("npm", "<npm-name>")
# Everything else is the static page content for that project's card.
# ---------------------------------------------------------------------------
PROJECTS = [
    {
        "slug": "conception-space",
        "accent": "ac-cyan",
        "source": ("github", "conception-space"),
        "license": "AGPL-3.0-or-later",        # explicit — a GitHub-Release product, no registry to derive from
        "registry_table": "GitHub Releases",
        "tagline": "Organize your knowledge in space — a 3D, hand-placed graph where every node is a handle onto a real file.",
        "package_chip": '<span class="chip">GitHub: <a href="https://github.com/ParkviewLab/conception-space/releases">Releases</a></span>',
        "summary": (
            "A desktop app for organizing knowledge in 3D space. You place nodes by hand at explicit\n"
            "      coordinates, and each node is a <strong>handle onto a real file</strong> (usually a markdown\n"
            "      note). Layout is not computed — you decide where things live — so the space is spatially\n"
            "      memorable and you can see the shape of your relationships at a glance. Built with Electron +\n"
            "      Three.js; runs on macOS, Windows, and Linux."
        ),
    },
    {
        "slug": "jonobones",
        "accent": "ac-teal",
        "source": ("npm", "jonobones"),
        "registry_table": "npm · GHCR",        "tagline": "A headless, Joplin-sync-compatible knowledge daemon.",
        "package_chip": (
            '<span class="chip">npm: '
            '<a href="https://www.npmjs.com/package/jonobones">jonobones</a> · '
            '<a href="https://www.npmjs.com/package/@parkviewlab/jonobones">@parkviewlab/jonobones</a>'
            "</span>"
        ),
        "install": "npm install -g jonobones",
        "summary": (
            "Owns a private Joplin-format knowledge base (notes, notebooks, tags, resources) and keeps it\n"
            "      synchronized with any Joplin sync target — Joplin Server/Cloud, filesystem, WebDAV/Nextcloud,\n"
            "      Dropbox, OneDrive, or S3 — serving it to local applications over a localhost <code>/v1</code> REST API.\n"
            "      Clients speak HTTP only; the SQLite database, resource files, sync metadata, and encryption keys stay\n"
            "      private to the daemon. CLI control plane, token auth on every endpoint except <code>/health</code>, and\n"
            "      <code>service install</code> for launchd (macOS) / systemd (Linux). Ships on npm and as a container image."
        ),
    },
    {
        "slug": "deco-assaying",
        "accent": "ac-red",
        "source": ("pypi", "deco-assaying"),
        "registry_table": "PyPI · GHCR",        "tagline": "MCP server for source-code analysis via tree-sitter (Python/C/C++ initially, broader coverage planned).",
        "package_chip": '<span class="chip">PyPI: <a href="https://pypi.org/project/deco-assaying/">deco-assaying</a></span>',
        "install": "uvx deco-assaying",
        "summary": (
            "Feeds structural information about a codebase — symbols, imports, references, cAST chunks, and metrics —\n"
            "      into downstream consumers. Async <code>index_repo</code> jobs accept a local directory, a GitHub URL, or a\n"
            "      GitLab URL (including nested groups); results are retrievable over MCP tools or an HTTP download API\n"
            "      (manifest, analysis index, per-file artifacts). Partial-clone, bin-packed batched fetching keeps the\n"
            "      source-side disk footprint at ~100&nbsp;MB regardless of repo size. Ships MCP prompts that encode the\n"
            "      recommended workflow, plus optional <code>GITHUB_TOKEN</code>/<code>GITLAB_TOKEN</code> for higher quotas and private repos."
        ),
    },
    {
        "slug": "flint-slating",
        "accent": "ac-blue",
        "source": ("pypi", "flint-slating"),
        "registry_table": "PyPI · GHCR",        "tagline": "MCP server that reads PDFs and exposes them as structured Markdown.",
        "package_chip": '<span class="chip">PyPI: <a href="https://pypi.org/project/flint-slating/">flint-slating</a></span>',
        "install": "uvx flint-slating",
        "summary": (
            "Converts PDFs to LLM-ready Markdown with heading hierarchy, multi-column reading order, and Markdown\n"
            "      tables, plus ancillaries: metadata, outline, images, and per-page tables. Built entirely on a\n"
            "      permissive-license stack (Docling, pypdf, pdfplumber) — no PyMuPDF, no AGPL/GPL in the dependency tree,\n"
            "      enforced by a CI license-check. Runs as a Streamable-HTTP daemon or a stdio MCP server; large PDFs queue\n"
            "      a background job (hybrid sync/async), and torch is pinned to CPU-only wheels so no CUDA libraries are bundled."
        ),
    },
    {
        "slug": "smalt-mcp",
        "accent": "ac-yellow",
        "source": ("pypi", "smalt-mcp"),
        "registry_table": "PyPI · GHCR",        "tagline": "MCP wrapper around Smalt's storage surface (read / write / link / claim / search).",
        "package_chip": '<span class="chip">PyPI: <a href="https://pypi.org/project/smalt-mcp/">smalt-mcp</a></span>',
        "install": "uvx smalt-mcp",
        "summary": (
            "Per the project's status: the storage substrate is complete — 17 tools across three permission tiers\n"
            "      (<code>read_only</code> / <code>read_write</code> / <code>remove_destructive</code>), with an auto-indexer\n"
            "      trigger on writes and hybrid search (FTS + vector + alias, RRF-fused) over a markdown + LanceDB store. A\n"
            "      thin, single-writer wrapper with no agentic logic, serving as the storage layer for ParkviewLab's CoGrind\n"
            "      project. Streamable-HTTP transport with health, admin, and OpenAPI endpoints."
        ),
    },
    {
        "slug": "ebony-enriching",
        "accent": "ac-sage",
        "source": ("pypi", "ebony-enriching"),
        "registry_table": "PyPI · GHCR",        "tagline": "An MCP lab notebook — proposal / experiment / gap lifecycle.",
        "package_chip": '<span class="chip">PyPI: <a href="https://pypi.org/project/ebony-enriching/">ebony-enriching</a></span>',
        "install": "uvx ebony-enriching",
        "summary": (
            "Per the project's status: the v0.1 surface is complete — 13 tools across two permission tiers\n"
            "      (6 read-only, 7 read-write) covering the full proposal / experiment / gap lifecycle. Append-only\n"
            "      lab-notebook semantics (proposals transition status rather than delete; experiments are the historical\n"
            "      record); the server enforces storage correctness only, leaving lifecycle policy to the agents using it.\n"
            "      Five operating modes — uvx, uv tool install, launchd, systemd, and Docker/GHCR."
        ),
    },
]

# ---------------------------------------------------------------------------
# Page template. HEAD is everything up to (and including) </header>; the
# "Updated" date is injected at __UPDATED__. Table rows and cards are
# generated from PROJECTS so the design lives in exactly one place.
# ---------------------------------------------------------------------------
HEAD = """<!DOCTYPE html>
<!--
SPDX-FileCopyrightText: 2026 Gary Frattarola <garyf@parkviewlab.ai>
SPDX-License-Identifier: LicenseRef-AllRightsReserved
-->
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ParkviewLab — Current Releases</title>
<style>
  /* Self-hosted Michroma (OFL) — no external font call. Page lives at /releases/. */
  @font-face{font-family:'Michroma';font-style:normal;font-weight:400;font-display:swap;
    src:url('../assets/fonts/michroma-latin.woff2') format('woff2');}
  :root{
    /* Brand */
    --teal:#00C2C7; --teal-deep:#004f52; --sage:#90b095; --ink:#141414;
    /* Bauhaus / Kandinsky accents */
    --red:#E2483D; --blue:#2547C8; --yellow:#F2B33D;
    /* Surfaces */
    --paper:#f3eee2; --paper-2:#ece5d4; --card:#fbf8f1; --muted:#5d6258;
    --code:#161412; --code-text:#ece5d4;
    --mono:ui-monospace,SFMono-Regular,"SF Mono",Menlo,Consolas,monospace;
    --sans:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
    --display:'Michroma',var(--sans);
  }
  *{box-sizing:border-box}
  body{margin:0;background:var(--paper);color:var(--ink);font-family:var(--sans);
       line-height:1.58;-webkit-font-smoothing:antialiased;}
  .wrap{max-width:900px;margin:0 auto;padding:0 24px 80px;}

  /* ---- Header ---- */
  header{padding:10px 0 28px;margin-bottom:36px;border-bottom:3px solid var(--ink);}
  /* logo row sits above the heading; logo right-aligned so the wordmark's
     right edge lines up with the right edge of the page column */
  .logo-row{width:100%;margin-bottom:0;}
  .logo{display:block;width:370px;max-width:62%;height:auto;margin:0 0 0 auto;}
  .head-text{width:100%;}
  @media(max-width:620px){.logo{max-width:84%;}}
  h1{font-family:var(--display);font-size:23px;letter-spacing:.02em;margin:0 0 4px;
     color:var(--teal-deep);text-transform:uppercase;}
  .rule{height:6px;width:120px;background:var(--teal);margin:0 0 14px;}
  .lede{color:var(--muted);font-size:15px;margin:0;max-width:600px;}
  .lede a{color:var(--teal-deep);text-decoration-color:var(--teal);}
  .updated{font-family:var(--mono);font-size:12px;letter-spacing:.08em;text-transform:uppercase;
           color:var(--muted);margin:0 0 4px;}

  /* ---- Summary table ---- */
  table.summary{width:100%;border-collapse:collapse;margin:0 0 44px;font-size:14px;
                background:var(--card);border:2px solid var(--ink);}
  table.summary th,table.summary td{text-align:left;padding:11px 14px;border-bottom:1px solid #d9d0bd;}
  table.summary thead th{background:var(--ink);color:var(--paper);font-family:var(--mono);
        font-weight:600;font-size:11px;text-transform:uppercase;letter-spacing:.1em;border-bottom:none;}
  table.summary tbody tr:last-child td{border-bottom:none;}
  table.summary td a{color:var(--teal-deep);text-decoration:none;font-weight:700;}
  table.summary td a:hover{color:var(--red);}
  .ver{font-family:var(--mono);color:var(--ink);font-weight:600;}
  .reg{font-family:var(--mono);font-size:12px;color:var(--muted);letter-spacing:.03em;}

  /* ---- Cards ---- */
  .card{position:relative;background:var(--card);border:2px solid var(--ink);
        padding:26px 28px 28px;margin:0 0 26px;overflow:hidden;}
  .card::before{content:"";position:absolute;top:0;left:0;width:100%;height:8px;background:var(--ac);}
  .card h2{font-family:var(--display);margin:6px 0 0;font-size:18px;letter-spacing:.01em;
           display:flex;align-items:center;gap:12px;flex-wrap:wrap;}
  .card h2 a{color:var(--ink);text-decoration:none;}
  .card h2 a:hover{color:var(--ac);}
  .badge{font-family:var(--mono);font-size:12px;color:#fff;background:var(--ac);
         border-radius:0;padding:3px 10px;letter-spacing:.02em;}
  .tagline{color:var(--muted);font-size:14.5px;margin:12px 0 16px;max-width:640px;}
  .meta{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 4px;}
  .chip{font-family:var(--mono);font-size:11.5px;color:var(--ink);background:var(--paper-2);
        border:1px solid #d4cab5;padding:4px 9px;letter-spacing:.02em;}
  .chip a{color:var(--teal-deep);text-decoration:none;}
  .chip a:hover{color:var(--red);}
  .section-label{font-family:var(--mono);font-size:10.5px;text-transform:uppercase;letter-spacing:.12em;
        color:var(--muted);margin:20px 0 8px;font-weight:600;display:flex;align-items:center;gap:8px;}
  .section-label::before{content:"";width:10px;height:10px;background:var(--ac);display:inline-block;}
  .section-label a{color:var(--teal-deep);text-decoration:none;}
  .section-label a:hover{color:var(--red);}
  .summary-box{background:#fff;border:1px solid #e0d8c6;border-left:5px solid var(--ac);
        padding:13px 16px;font-size:14.5px;color:#33372f;}
  .summary-box code{font-family:var(--mono);font-size:12.5px;background:var(--paper-2);padding:1px 5px;}
  .summary-box p{margin:0 0 8px;}
  .summary-box p:last-child{margin-bottom:0;}
  .summary-box ul{margin:0 0 8px;padding-left:18px;}
  .summary-box li{margin:3px 0;}
  .summary-box a{color:var(--teal-deep);}
  .summary-box .rn-h{font-family:var(--mono);font-size:10.5px;text-transform:uppercase;
        letter-spacing:.1em;color:var(--muted);font-weight:600;margin:12px 0 5px;}
  .summary-box .rn-h:first-child{margin-top:0;}
  pre{background:var(--code);border:0;padding:14px 16px;overflow-x:auto;margin:8px 0 0;}
  pre code{font-family:var(--mono);font-size:12.5px;color:var(--code-text);line-height:1.7;}
  pre .c{color:var(--sage);}      /* comment */
  pre .p{color:var(--teal);}      /* prompt/emphasis */

  /* accent themes */
  .ac-teal{--ac:var(--teal-deep)}
  .ac-red{--ac:var(--red)}
  .ac-blue{--ac:var(--blue)}
  .ac-yellow{--ac:#c98a17}
  .ac-sage{--ac:#4f7d5a}
  .ac-cyan{--ac:#0e7490}

  .downloads{list-style:none;margin:8px 0 0;padding:0;}
  .downloads li{font-size:13px;line-height:1.9;}
  .downloads a{font-family:var(--mono);}
  .dl-note{margin:10px 0 0;font-size:12px;color:var(--muted);}

  .note{margin-top:42px;padding:18px 20px;background:var(--paper-2);border:2px solid var(--ink);
        color:#3c4036;font-size:13px;line-height:1.6;}
  .note strong{color:var(--ink);font-family:var(--display);font-size:11px;text-transform:uppercase;
        letter-spacing:.08em;display:inline-block;margin-right:6px;}
  footer{margin-top:30px;color:var(--muted);font-size:12px;text-align:center;font-family:var(--mono);
         letter-spacing:.04em;line-height:1.9;}
  footer a{color:var(--teal-deep);}
</style>
</head>
<body>
<div class="wrap">

  <header>
    <!-- Brand logo (color, horizontal, dark ink for light ground) -->
    <div class="logo-row">
    <svg class="logo" viewBox="0 72 514 148" role="img" xmlns="http://www.w3.org/2000/svg" aria-label="Parkview Lab">
      <defs><style>.wm{font-family:'Michroma',sans-serif;fill:#141414;}.wm-stroke{font-family:'Michroma',sans-serif;fill:none;stroke:#141414;stroke-linejoin:round;}</style></defs>
      <g transform="translate(150,150)">
        <rect x="-88.572067" y="39.569824" width="9" height="28" fill="#90b095"/>
        <circle cx="-83" cy="10" r="30" fill="#90b095"/><circle cx="-111" cy="20" r="22" fill="#90b095"/>
        <circle cx="-55" cy="18" r="21" fill="#90b095"/><circle cx="-119" cy="4" r="16" fill="#90b095"/>
        <circle cx="-47" cy="6" r="15" fill="#90b095"/><circle cx="-99" cy="-14" r="24" fill="#90b095"/>
        <circle cx="-71" cy="-22" r="20" fill="#90b095"/><circle cx="-103" cy="-32" r="16" fill="#90b095"/>
        <circle cx="-79" cy="-38" r="15" fill="#90b095"/><circle cx="-59" cy="-14" r="13" fill="#90b095"/>
        <rect x="-5.820663" y="39.498325" width="6" height="22" fill="#90b095"/>
        <circle cx="-2" cy="26" r="17" fill="#90b095"/><circle cx="-19" cy="29" r="13" fill="#90b095"/>
        <circle cx="14" cy="27" r="12" fill="#90b095"/><circle cx="-11" cy="12" r="13" fill="#90b095"/>
        <circle cx="7" cy="13" r="14" fill="#90b095"/><circle cx="-4.28" cy="-2.71" r="11" fill="#90b095"/>
        <circle cx="6" cy="-2.14" r="7" fill="#90b095"/>
        <g transform="matrix(0.84873,0,0,0.84873,-48.5422,6.0416)">
          <path d="m -16,-78 a 28,28 0 0 1 32,0" fill="none" stroke="#00C2C7" stroke-width="4" stroke-linecap="square"/>
          <path d="m -28,-88 a 46,46 0 0 1 56,0" fill="none" stroke="#00C2C7" stroke-width="2.5" stroke-linecap="square"/>
          <polyline points="0,-28 0,-36 0,-62" fill="none" stroke="#00C2C7" stroke-width="6" stroke-linecap="square"/>
          <polyline points="24,-14 32,-22 53.7,-28" fill="none" stroke="#00C2C7" stroke-width="6" stroke-linecap="square"/>
          <polyline points="-24,-14 -32,-22 -53.7,-28" fill="none" stroke="#00C2C7" stroke-width="6" stroke-linecap="square"/>
          <polyline points="0,28 0,35 0,56" fill="none" stroke="#00C2C7" stroke-width="4.5" stroke-linecap="square"/>
          <polyline points="24,14 30,20 46,28" fill="none" stroke="#00C2C7" stroke-width="4.5" stroke-linecap="square"/>
          <polyline points="-24,14 -30,20 -46,28" fill="none" stroke="#00C2C7" stroke-width="4.5" stroke-linecap="square"/>
          <circle cx="0" cy="-62" r="11" fill="#00C2C7"/><circle cx="0" cy="-62" r="5" fill="#004f52"/>
          <circle cx="53.7" cy="-31" r="11" fill="#00C2C7"/><circle cx="53.7" cy="-31" r="5" fill="#004f52"/>
          <circle cx="-53.7" cy="-31" r="11" fill="#00C2C7"/><circle cx="-53.7" cy="-31" r="5" fill="#004f52"/>
          <circle cx="0" cy="56" r="9" fill="#00C2C7"/><circle cx="0" cy="56" r="4" fill="#004f52"/>
          <circle cx="46" cy="28" r="9" fill="#00C2C7"/><circle cx="46" cy="28" r="4" fill="#004f52"/>
          <circle cx="-46" cy="28" r="9" fill="#00C2C7"/><circle cx="-46" cy="28" r="4" fill="#004f52"/>
          <polygon points="0,-28 24,-14 24,14 0,28 -24,14 -24,-14" fill="#00C2C7"/>
          <polygon points="0,-23 20,-11.5 20,11.5 0,23 -20,11.5 -20,-11.5" fill="#004f52"/>
          <line x1="0" y1="-23" x2="0" y2="23" stroke="#00C2C7" stroke-width="3" stroke-linecap="square"/>
        </g>
      </g>
      <text x="248" y="166" class="wm-stroke" font-size="36" letter-spacing="2" stroke-width="1.2">PARKVIEW</text>
      <text x="248" y="166" class="wm" font-size="36" letter-spacing="2">PARKVIEW</text>
      <polygon points="248,178 514,178 511,181 248,181" fill="#00C2C7"/>
      <text x="248" y="206" class="wm-stroke" font-size="20" letter-spacing="6" stroke-width="1.2">LAB</text>
      <text x="248" y="206" class="wm" font-size="20" letter-spacing="6">LAB</text>
    </svg>
    </div>

    <div class="head-text">
      <h1>Current Releases</h1>
      <div class="rule"></div>
      <p class="updated">Updated __UPDATED__</p>
      <p class="lede">The latest published version of each public
        <a href="https://github.com/ParkviewLab">ParkviewLab</a> open-source project, where it ships,
        and a summary of what each current version provides.</p>
    </div>
  </header>
"""

TABLE_OPEN = """
  <table class="summary">
    <thead>
      <tr><th>Project</th><th>Latest</th><th>Released</th><th>Published to</th></tr>
    </thead>
    <tbody>
"""

TABLE_CLOSE = """    </tbody>
  </table>
"""

ROW_TMPL = (
    '      <tr><td><a href="https://github.com/ParkviewLab/{slug}">{slug}</a></td>'
    '<td class="ver">{version}</td><td>{date}</td><td class="reg">{registry_table}</td></tr>\n'
)

TAIL = """
  <div class="note">
    <strong>About these notes</strong> Where a project publishes
    <a href="https://github.com/orgs/ParkviewLab/repositories">GitHub Releases</a>, its per-version
    release notes are shown above, pulled from the latest release (and linked to the full Release and
    CHANGELOG). For projects that don't publish them yet, the summary describes the current shipped
    surface from the project's README — not a per-version diff.
  </div>

  <footer>
    <div>Versions sourced from PyPI, npm, and GitHub Releases · container images on
    <a href="https://github.com/orgs/ParkviewLab/packages">GHCR</a> · released via tag-driven CI on <code>v*</code> tags.</div>
    <div>__COPYRIGHT__ · <a href="mailto:__CONTACT__">__CONTACT__</a> · This page updated on __UPDATED__</div>
  </footer>
</div>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Fetch helpers
# ---------------------------------------------------------------------------
def _get_json(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def _gh_json(url):
    """GET a GitHub API URL with optional auth; return parsed JSON or None (quiet)."""
    headers = dict(UA)
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except Exception:  # noqa: BLE001  (404 / network → treat as "not available")
        return None


def _fetch_registry(kind, pkg):
    """Return (version, iso_date, license) from PyPI/npm, or (None, None, None).

    The license is the registry's own metadata — PyPI's PEP 639 `license_expression`
    or npm's `license` — the single source of truth, never hardcoded here (so it tracks
    relicenses the same way the version tracks releases). Quiet — used for probing too."""
    try:
        if kind == "pypi":
            d = _get_json(f"https://pypi.org/pypi/{pkg}/json")
            info = d["info"]
            ver = info["version"]
            files = d["releases"].get(ver) or []
            date = files[0]["upload_time_iso_8601"][:10] if files else ""
            lic = info.get("license_expression") or info.get("license") or ""
            return ver, date, lic
        if kind == "npm":
            d = _get_json(f"https://registry.npmjs.org/{pkg}")
            ver = d["dist-tags"]["latest"]
            date = (d.get("time", {}).get(ver) or "")[:10]
            vmeta = (d.get("versions") or {}).get(ver) or {}
            lic = vmeta.get("license") or d.get("license") or ""
            return ver, date, lic
    except Exception:  # noqa: BLE001
        return None, None, None
    return None, None, None


def fetch_latest(project):
    """(version, date, license) for a curated project; prints on failure."""
    kind, pkg = project["source"]
    ver, date, lic = _fetch_registry(kind, pkg)
    if ver is None:
        print(f"  ! could not fetch {project['slug']} ({kind}:{pkg})", file=sys.stderr)
    return ver, date, lic


def fetch_release(slug):
    """Latest GitHub Release for a repo, or None if it publishes none.

    Also returns the published date and installer assets (download URLs) so a
    GitHub-Release product (no PyPI/npm package) can source its version, date,
    and per-OS download links from here."""
    d = _gh_json(f"https://api.github.com/repos/{ORG}/{slug}/releases/latest")
    if d and d.get("tag_name"):
        return {
            "tag": d["tag_name"],
            "body": d.get("body") or "",
            "url": d.get("html_url") or "",
            "date": (d.get("published_at") or "")[:10],
            "assets": [
                {"name": a.get("name", ""), "url": a.get("browser_download_url", "")}
                for a in (d.get("assets") or [])
            ],
        }
    return None


def has_changelog(slug):
    """True if the repo keeps a CHANGELOG.md."""
    d = _gh_json(f"https://api.github.com/repos/{ORG}/{slug}/contents/CHANGELOG.md")
    return bool(d and d.get("name") == "CHANGELOG.md")


def discover_extras(curated):
    """Public org repos that are neither curated nor denylisted → table-only rows.

    Each gets a version probed from PyPI then npm (the org convention: package
    name == repo name); if neither has it, the row links to the repo on GitHub.
    Returns dicts shaped for ROW_TMPL. Fully automatic listing is intentionally
    avoided — see the DENYLIST and the handbook's website.md (hybrid model).
    """
    repos = _gh_json(f"https://api.github.com/orgs/{ORG}/repos?per_page=100&type=public")
    if not repos:
        print("  (skipped org repo discovery: GitHub API unavailable)", file=sys.stderr)
        return []
    extras = []
    for repo in sorted((x for x in repos if isinstance(x, dict)), key=lambda x: x.get("name", "")):
        name = repo.get("name", "")
        if repo.get("private") or repo.get("archived"):
            continue
        if name in curated or name in DENYLIST:
            continue
        ver = date = reg = None
        for kind in ("pypi", "npm"):
            ver, date, _lic = _fetch_registry(kind, name)
            if ver:
                reg = "PyPI" if kind == "pypi" else "npm"
                break
        extras.append({
            "slug": name,
            "version": ver or "—",
            "date": date or "—",
            "registry_table": reg or f'<a href="https://github.com/{ORG}/{name}">GitHub</a>',
        })
        print(f"  + discovered (table-only): {name}  {ver or '—'}  {reg or 'GitHub'}")
    if not extras:
        print("  (no untracked public product repos — all are curated or denylisted)")
    return extras


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------
def _inline(text):
    """Inline Markdown → HTML on already-escaped text: code, bold, links."""
    text = html.escape(text, quote=False)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", r'<a href="\2">\1</a>', text)
    return text


def md_to_html(md):
    """Render the small Markdown subset GitHub release bodies use (git-cliff output):
    `## ` version headings (dropped — the card badge already shows it), `### ` section
    headings, paragraphs, and `- `/`* ` bullet lists, with inline code/bold/links."""
    out, para, items = [], [], []

    def flush_para():
        if para:
            out.append("<p>" + _inline(" ".join(para).strip()) + "</p>")
            para.clear()

    def flush_list():
        if items:
            out.append("<ul>" + "".join(f"<li>{_inline(i)}</li>" for i in items) + "</ul>")
            items.clear()

    for raw in md.replace("\r\n", "\n").split("\n"):
        s = raw.strip()
        if not s:
            flush_para(); flush_list(); continue
        if s.startswith("## "):           # top version line — redundant with the badge
            flush_para(); flush_list(); continue
        if s.startswith("### "):
            flush_para(); flush_list()
            out.append(f'<div class="rn-h">{_inline(s[4:].strip())}</div>')
            continue
        if s.startswith("- ") or s.startswith("* "):
            flush_para()
            items.append(s[2:].strip())
            continue
        para.append(s)
    flush_para(); flush_list()
    return "\n      ".join(out)


OS_LABELS = [
    (".dmg", "macOS (Apple Silicon)"),
    ("-setup.exe", "Windows"),
    (".AppImage", "Linux · AppImage"),
    (".deb", "Linux · Debian/Ubuntu"),
]


def download_section(p, rel):
    """Per-OS installer links for a GitHub-Release (desktop) product, built from
    the release assets — replaces the registry `install` + `docker pull` block."""
    assets = (rel or {}).get("assets", [])
    items, seen = [], set()
    for suffix, label in OS_LABELS:
        for a in assets:
            if a["name"].endswith(suffix) and a["name"] not in seen:
                seen.add(a["name"])
                items.append(f'<li>{label}: <a href="{a["url"]}">{a["name"]}</a></li>')
                break
    if not items and rel:
        items = [f'<li>See the <a href="{rel["url"]}">latest release</a>.</li>']
    links = "\n      ".join(items)
    return f"""<div class="section-label">Download v{p["version"]}</div>
    <ul class="downloads">
      {links}
    </ul>
    <p class="dl-note">Unsigned builds — your OS may warn on first launch. See the
    <a href="https://github.com/{ORG}/{p["slug"]}#install">install notes</a>.</p>"""


def build_card(p):
    """One project card. Shows real GitHub release notes when present, else the
    README surface summary. A GitHub-Release product (no registry package) renders
    per-OS download links instead of an `install` command + container image."""
    is_download = p["source"][0] == "github"
    chips = [f'<span class="chip">Released {p["date"]}</span>']
    if p.get("license"):
        chips.append(f'<span class="chip">{p["license"]}</span>')
    chips.append(p["package_chip"])
    if not is_download:
        chips.append(f'<span class="chip"><a href="https://github.com/{ORG}/{p["slug"]}/pkgs/container/{p["slug"]}">container image</a></span>')
    rel = p.get("release")
    if rel:
        chips.append(f'<span class="chip"><a href="{rel["url"]}">release notes</a></span>')
    if p.get("has_changelog"):
        chips.append(f'<span class="chip"><a href="https://github.com/{ORG}/{p["slug"]}/blob/main/CHANGELOG.md">changelog</a></span>')
    meta = "\n      ".join(chips)

    if rel and rel["body"].strip():
        label = f'Release notes <a href="{rel["url"]}">{html.escape(rel["tag"])} &#8599;</a>'
        body = md_to_html(rel["body"])
    else:
        label = "What this version provides"
        body = p["summary"]

    if is_download:
        bottom = download_section(p, rel)
    else:
        bottom = f"""<div class="section-label">Install</div>
    <pre><code>{p["install"]}
<span class="c"># or</span>
docker pull ghcr.io/parkviewlab/{p["slug"]}:latest</code></pre>"""

    return f"""
  <!-- {p["slug"]} -->
  <div class="card {p["accent"]}">
    <h2><a href="https://github.com/{ORG}/{p["slug"]}">{p["slug"]}</a> <span class="badge">v{p["version"]}</span></h2>
    <p class="tagline">{p["tagline"]}</p>
    <div class="meta">
      {meta}
    </div>
    <div class="section-label">{label}</div>
    <div class="summary-box">
      {body}
    </div>
    {bottom}
  </div>
"""


def human_date(d):
    # "June 1, 2026" — month name, no zero-padded day, portably.
    return f"{d:%B} {d.day}, {d.year}"


def render(projects, extras, updated):
    rows = "".join(ROW_TMPL.format(**p) for p in projects)
    rows += "".join(ROW_TMPL.format(**e) for e in extras)
    cards = "".join(build_card(p) for p in projects)
    page = HEAD + TABLE_OPEN + rows + TABLE_CLOSE + cards + TAIL
    return (
        page.replace("__UPDATED__", updated)
        .replace("__COPYRIGHT__", COPYRIGHT)
        .replace("__CONTACT__", CONTACT)
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="Render the ParkviewLab releases page.")
    ap.add_argument("--check", action="store_true", help="report only; write nothing")
    args = ap.parse_args()

    today = dt.date.today()
    print(f"ParkviewLab releases build — {today.isoformat()}")

    # Curated projects → full cards + table rows. Pull real release notes where published.
    projects = []
    for p in PROJECTS:
        rel = fetch_release(p["slug"])
        if p["source"][0] == "github":
            # Desktop / installer product: version + date come from the GitHub Release.
            if not rel:
                print(f"  ! aborting: no GitHub release for {p['slug']}", file=sys.stderr)
                return 2
            ver, date, lic = rel["tag"].lstrip("v"), rel["date"], p.get("license", "")
        else:
            ver, date, lic = fetch_latest(p)
            if ver is None:
                print(f"  ! aborting: missing data for {p['slug']}", file=sys.stderr)
                return 2
        proj = dict(p, version=ver, date=date, license=lic, release=rel, has_changelog=has_changelog(p["slug"]))
        projects.append(proj)
        notes = f"release notes {rel['tag']}" if rel else "README summary"
        print(f"  {p['slug']:<16} {ver:<16} {date}  {lic or '—':<18} [{notes}]")

    # Other public org repos → table-only rows (or none, if all denylisted).
    extras = discover_extras({p["slug"] for p in PROJECTS})

    if args.check:
        return 0

    out_path = os.path.join(HERE, "releases", "index.html")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(render(projects, extras, human_date(today)))
    print("\nwrote releases/index.html")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
