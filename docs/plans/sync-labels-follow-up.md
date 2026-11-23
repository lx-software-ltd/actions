# Sync labels follow-up

Zone: yellow. The note stays until this pull request finishes the change, then the note goes.

The README callers cell names only this repository. `docs/decisions.md` already says the product repositories do not run `sync-labels` yet.

`sync-labels.yml` sets `cancel-in-progress: false`. An apply is left to finish. The writes are idempotent, and the next run applies whatever is still missing.

`apply` keeps going after a failed `gh` call. The run exits 1 and lists the changes that were written.

The `token` input defaults to `github.token`.

`gh api --paginate` returns one JSON array. The parser uses `json.loads` only.
