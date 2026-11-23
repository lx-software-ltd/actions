# Sync labels

Zone: yellow. The note stays until this pull request finishes the change, then the note goes.

`sync-labels/labels.json` is the shared catalogue for this repository and `evolvesprouts`, `findingalpha`, `lx-software`, and `siutindei`. It is the GitHub defaults plus `dependencies`, `ci`, `infrastructure`, and `mobile`. Colours follow the value already used by more than one repository. `mobile` is `0e8a16`, "Flutter app".

The action creates a missing label and updates colour, description, and letter case. A label that is not in the catalogue stays, including `lambda` and the siutindei board labels. `mode: check` fails on drift. `mode: apply` writes.

`.github/workflows/sync-labels.yml` applies the catalogue to this repository. `github.token` can write labels here. `SYNC_LABELS_REPOSITORIES=siblings` applies the same catalogue to the five repositories when the token can write issues on each.

Fixtures cover a match and a drift. The CI contract lists the workflow.
