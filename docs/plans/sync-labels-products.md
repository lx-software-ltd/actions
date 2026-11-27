# Sync labels in the product repositories

Zone: yellow. The note stays until the pull request that finishes this change deletes it.

Issue 109. Checked 26 Nov 2026: `evolvesprouts`, `findingalpha`, `lx-software`, and `siutindei` have no `sync-labels.yml`. This repository's workflow sets `repositories` to `github.repository`.

## Decision

Each product runs the action on itself. `github.token` writes labels on the repository that is running the workflow. It cannot write issues on the other four.

`siblings` stays the local command in `sync-labels/README.md`, for a `gh` login that can write issues on each repository. This repository does not hold that token. `.github/workflows/sync-labels.yml` keeps `uses: ./sync-labels`, `mode: apply`, and `repositories: ${{ github.repository }}`.

## This change

Add `templates/workflows/sync-labels.yml` with no `# template:if-present`. Conformance then requires the file in every product. `profile: producer` skips that comparison, so this repository's `uses: ./sync-labels` stays.

The template follows the product workflow rules. Strings use double quotes. Top-level `permissions` is `contents: read`. The job `sync` is named Sync Labels, runs on `ubuntu-26.04`, and sets `issues: write`. Triggers are `workflow_dispatch`, `push` to `main`, and Monday 08:00 UTC (`0 8 * * 1`). Concurrency uses `${{ github.workflow }}-${{ github.ref }}` with `cancel-in-progress: false`, and the comment says an apply is left to finish because the writes are idempotent. Checkout is the same `actions/checkout` pin as the other templates. The apply step is:

```yaml
      - name: Apply the shared catalogue
        uses: lx-software-ltd/actions/sync-labels@ACTIONS_PIN # main DATE
        with:
          mode: apply
          repositories: ${{ github.repository }}
```

The opening comment says the workflow applies the catalogue to the calling repository and that `github.token` writes labels there. Unmarked text does not name a product. The job is not a required check. `main-protection` stays `lint`, `test`, and `security-summary`.

`docs/ci-contract.md` gains a row in the product workflow table: file `sync-labels.yml`, job `sync`, those triggers, catalogue applied to the calling repository, not a required check. The paragraph under "This repository" stays. It already describes this repository's own run.

`docs/decisions.md` under Labels states the chosen path. The products run `sync-labels.yml` from the template after the pin moves. `github.token` writes the calling repository. `siblings` remains the local command when `gh` can write issues on each repository.

`tests/test_workflow_conformance.py` loads `templates/workflows/sync-labels.yml`. A checkout without the file reports `sync-labels.yml: missing the shared workflow`. A copy of the template, with `ACTIONS_PIN` and `DATE` replaced by a real pin, reports no finding for that file.

## After this change

The README callers row stays blank for the four products until a workflow there calls the action.

`scripts/bump_pins.py` rewrites pins. It does not add a workflow. Each product pull request adds `.github/workflows/sync-labels.yml` in the same commit as the pin bump. Until that pin moves, the product stays on the previous template set. Issue 109 stays open until those four workflows are on `main`.
