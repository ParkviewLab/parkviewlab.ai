# Contributing

parkviewlab.ai is a ParkviewLab **website repo** — it follows the
[website profile](https://github.com/ParkviewLab/handbook/blob/main/docs/website.md),
a lighter flow than the org's package repos.

## Edit & publish

- Work on **`staging`** (the default branch). Small edits can go straight to
  `staging`; for a bigger change, use a prefixed worktree branch (`feature-`,
  `doc-`, …) off `staging` and merge it back.
- **Preview locally** before publishing: `scripts/preview.sh` builds the releases
  page, stamps the "updated on" dates, and serves the site at
  `http://localhost:8000` — exactly what will deploy.
- **Publish by promoting `staging` → `live`** (from the `live` worktree:
  `git merge --ff-only staging && git push`). The push to `live` triggers the
  GitHub Pages deploy. There are **no version bumps, tags, or releases**.
- Promoting to `live` **publishes to the internet** — treat it as the go/no-go
  gate; get an explicit go-ahead first.

## What's generated (don't commit)

`releases/index.html` and the per-page "updated on" dates are build artifacts,
produced by `build.py` / `scripts/stamp.py` at deploy (and by the preview). They
are `.gitignore`d.

## Licensing

Standard copyright (all rights reserved) plus the bundled Michroma font under
`OFL-1.1`. Every file needs an SPDX header or a `REUSE.toml` entry — keep
`reuse lint` green:

```bash
uvx --from "reuse[charset-normalizer]" reuse lint
```

See [`LICENSING.md`](../LICENSING.md) and the handbook's
[`website.md`](https://github.com/ParkviewLab/handbook/blob/main/docs/website.md).
