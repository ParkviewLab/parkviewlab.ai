# parkviewlab.ai

The Parkview Lab website — a plain static site served by **GitHub Pages** at
[parkviewlab.ai](https://parkviewlab.ai). No build framework.

## Layout

```
index.html              ← landing page
releases/index.html     ← auto-generated "current releases" page (built by build.py)
build.py                ← stdlib-only builder for the releases page (source of truth for its design)
assets/
  style.css             ← shared site styles + self-hosted @font-face (Michroma)
  fonts/michroma-latin.woff2
  img/                  ← brand logo SVGs
CNAME                   ← custom domain for GitHub Pages
```

## Fonts & logos

- **Michroma** is self-hosted in `assets/fonts/` (OFL) — no Google Fonts call.
- Logo SVGs are inlined in HTML so they render with the page's self-hosted font.

## Releases page

`build.py` fetches the latest published version of each Parkview Lab project and renders
`releases/index.html`. It runs in CI (see `.github/workflows/`) — triggered on each org release,
on a nightly schedule, and manually — so the page stays current without a server.

```bash
python3 build.py            # rebuild if a version changed
python3 build.py --check    # report only
python3 build.py --force    # rebuild unconditionally
```
