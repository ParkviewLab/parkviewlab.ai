# parkviewlab.ai

The Parkview Lab website — a plain static site (no framework) served by
**GitHub Pages** at [parkviewlab.ai](https://parkviewlab.ai). It follows the
ParkviewLab [website-repo conventions](https://github.com/ParkviewLab/handbook/blob/main/docs/website.md).

## Layout

```
index.html                ← landing page
conception-space/         ← product page
releases/index.html       ← generated "current releases" page (built by build.py; not committed)
build.py                  ← stdlib builder for the releases page (source of truth for its design)
scripts/
  preview.sh              ← local preview: build + stamp dates + serve on localhost
  stamp.py                ← stamps each page's "updated on" date from git
assets/
  style.css               ← shared site styles + self-hosted @font-face (Michroma)
  fonts/michroma-latin.woff2
  img/                    ← brand logo SVGs
CNAME                     ← custom domain
.github/workflows/        ← reuse.yml (lint) + pages-deploy.yml (build + deploy)
```

## Branches & publishing

- **`live`** — production; GitHub Pages serves this branch via the Actions deploy.
- **`staging`** — integration (the default branch); work happens here.

Edit on `staging` (small changes directly; a `feature-`/`doc-` worktree branch for
bigger ones). Preview locally, then **publish by promoting `staging` → `live`**:

```bash
scripts/preview.sh                            # build + stamp + serve at http://localhost:8000
# when it looks right, from the live worktree:
git merge --ff-only staging && git push       # push to live → deploys
```

## Releases page

`build.py` renders `releases/index.html` from the latest published version of each
tracked Parkview Lab project (PyPI / npm). Curated projects get full cards; other
public org repos (minus a denylist) appear as table rows automatically. The page is
a build artifact — rebuilt and deployed by `.github/workflows/pages-deploy.yml` (on
publish, on a nightly schedule, and on demand), so it stays current without a server
and without being committed.

```bash
python3 build.py            # render releases/index.html
python3 build.py --check    # report versions + discovered repos; write nothing
```

## License

Standard copyright — © 2026 Gary Frattarola, all rights reserved (not open source).
The bundled Michroma font is third-party under `OFL-1.1`. See [`LICENSING.md`](LICENSING.md).
