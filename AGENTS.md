# AGENTS.md

## Zones

Autonomy follows blast radius. The map is `docs/architecture/zones.md`. The stricter zone wins, and a more specific path beats a glob. If scope grows into a stricter zone, stop and ask.

- **Red.** Plan in chat and wait for explicit approval before any write. The PII denylist is red.
- **Yellow.** Write a short plan under `docs/plans/` before editing. This includes workflows, action files, `scripts/**`, `fixtures/**`, `docs/ci-contract.md`, the zone map, `AGENTS.md`, and Dependabot config. `docs/**` is not green as a whole.
- **Green.** Implement and verify. Summarise intent in the pull request.

## What this repository is

Composite actions and the hooks the product repositories share. An action cannot read `secrets` or `vars`. Callers pass those as inputs. Payload is `"$GITHUB_ACTION_PATH/..."`. Shared payload is `"$GITHUB_ACTION_PATH/../lib/..."`. An action does not call another action in this repository.

Nothing private goes in this repository: no secret, account id, internal hostname, or personal data. A product's own further denylist entries stay in that product. `scripts/pii-denylist.sha256` holds the 31 organisation digests the owner approved on 20 Nov 2026. They are the same digests as in `evolvesprouts` and `siutindei`. No plaintext.

No workflow here requests `id-token: write` or calls AWS.

`main-protection` and `release-tags` both apply. `lint` and `test` are required. Do not create a `v*` tag: `release-tags` blocks creation, update, and deletion, and the owner has not yet split creation into its own ruleset. The plan copy is `docs/plans/shared-actions-and-ci-convergence.md`.

The `lint`, `test`, and `security-summary` gates pin `lx-software-ltd/actions/require-jobs` at the merge SHA in `docs/plans/progress.md`. They must not use `uses: ./require-jobs`.

## Checks

`python3 -m unittest discover -s tests -v` runs the unit tests. `python3 scripts/check_action_layout.py` checks composite actions and workflow pins. `python3 scripts/check_pii.py` scans tracked source against `scripts/pii-denylist.sha256`.

Python payload uses the standard library and runs on Python 3.12.
