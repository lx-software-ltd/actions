# AGENTS.md

## Zones

Autonomy follows blast radius. The map is `docs/architecture/zones.md`. The stricter zone wins, and a more specific path beats a glob. If scope grows into a stricter zone, stop and ask.

- **Red.** Plan in chat and wait for explicit approval before any write. The PII denylist is red.
- **Yellow.** Write a short plan under `docs/plans/` before editing. This includes workflows, action files, `scripts/**`, `fixtures/**`, `docs/ci-contract.md`, the zone map, `AGENTS.md`, and Dependabot config. `docs/**` is not green as a whole. The pull request that finishes a plan deletes its note.
- **Green.** Implement and verify. Summarise intent in the pull request.

## What this repository is

Composite actions and the hooks the product repositories share. An action cannot read `secrets` or `vars`. Callers pass those as inputs. Payload is `"$GITHUB_ACTION_PATH/..."`. Shared payload is `"$GITHUB_ACTION_PATH/../lib/..."`. The organisation denylist is the exception: it stays at `scripts/pii-denylist.sha256`, and the checker reads that file from its own checkout. An action does not call another action in this repository.

Nothing private goes in this repository: no secret, account id, internal hostname, or personal data. A product's own further denylist entries stay in that product, in `scripts/pii-denylist.sha256`, and are added to the organisation list. A missing product file adds nothing. `scripts/pii-denylist.sha256` in this repository holds the 31 organisation digests the owner approved on 20 Nov 2026. The checker applies them in all five repositories, including `lx-software`. The published owner name in `lx-software` stays in `site.json`. `.json` is not scanned. No plaintext.

No workflow here requests `id-token: write` or calls AWS.

`main-protection`, `release-tags`, and `release-tags-create` apply. `lint`, `test`, and `security-summary` are required. Do not create a `v*` tag: `release-tags` blocks update and deletion, and `release-tags-create` blocks creation. The decisions that still bind are `docs/decisions.md`.

The `lint`, `test`, and `security-summary` gates pin `lx-software-ltd/actions/require-jobs` at `1a3cca7c38163f8164c262323601c34a4df5b7a4`. They must not use `uses: ./require-jobs`.

## Checks

`python3 -m unittest discover -s tests -v` runs the unit tests. `python3 scripts/check_action_layout.py` checks composite actions and workflow pins. `python3 scripts/check_pii.py` scans tracked source against `scripts/pii-denylist.sha256`.

Python payload uses the standard library and runs on Python 3.12.
