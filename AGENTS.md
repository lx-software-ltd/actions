# AGENTS.md

## Zones

Autonomy follows blast radius. The map is `docs/architecture/zones.md`. The stricter zone wins, and a more specific path beats a glob. If scope grows into a stricter zone, stop and ask.

- **Red.** Plan in chat and wait for explicit approval before any write. The PII denylist is red.
- **Yellow.** Write a short plan under `docs/plans/` before editing. This includes workflows, action files, `scripts/**`, `fixtures/**`, `docs/ci-contract.md`, the zone map, `AGENTS.md`, and Dependabot config. `docs/**` is not green as a whole.
- **Green.** Implement and verify. Summarise intent in the pull request.

## What this repository is

Composite actions and the hooks the product repositories share. An action cannot read `secrets` or `vars`. Callers pass those as inputs. Payload is `"$GITHUB_ACTION_PATH/..."`. Shared payload is `"$GITHUB_ACTION_PATH/../lib/..."`. An action does not call another action in this repository.

Nothing private goes in this repository: no secret, account id, internal hostname, or personal data. The PII hash list for a product stays in that product. `scripts/pii-denylist.sha256` has no digests, so the PII job checks nothing until the owner adds organisation-level hashes.

No workflow here requests `id-token: write` or calls AWS.

`main-protection` and `release-tags` do not apply to this repository. Do not create a `v*` tag. Do not treat a green `lint` or `test` check as merge protection. The plan copy and the corrections live in `docs/plans/shared-actions-and-ci-convergence.md`.

The `lint`, `test`, and `security-summary` gates stay inline in the workflow file. They must not use `uses: ./require-jobs`.

## Checks

`python3 -m unittest discover -s tests -v` runs the unit tests. `python3 scripts/check_action_layout.py` checks composite actions and workflow pins. `python3 scripts/check_pii.py` scans tracked source against `scripts/pii-denylist.sha256`.

Python payload uses the standard library and runs on Python 3.12.
