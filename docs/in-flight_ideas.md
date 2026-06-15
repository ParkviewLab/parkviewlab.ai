# In-flight ideas

Scratchpad for ideas under consideration — questions, not commitments (see the
handbook's `documentation.md`). Don't act on an entry silently.

## Deployed staging preview

A deployed preview of `staging` (a separate Pages environment, or a `staging.`
subdomain) so a reviewer can see changes online before promoting to `live`. Today
review is local-only via `scripts/preview.sh` — enough for a solo maintainer, but a
shared URL would help when others review.

## Immediate releases-page refresh on project releases

The releases page refreshes nightly (and on publish / manual dispatch). For an
instant update when a project cuts a release, a sibling repo's `release.yml` could
fire a `repository_dispatch` at parkviewlab.ai to rebuild. Needs a cross-repo
token; weigh against the nightly cadence (usually fine).

## Promote-to-live convenience

A one-liner (a `git publish` alias or a tiny script) wrapping
`git -C ../parkviewlab.ai-live merge --ff-only staging && git push`, so publishing
is a single obvious command.
