# Agent work zones

Autonomy follows blast radius. A change that touches more than one zone uses the stricter zone. A more specific path beats a glob. If implementation spreads into a stricter zone, stop and ask.

## Red

Plan in chat and wait for explicit approval before any write.

- A workflow that requests `id-token: write` or calls AWS
- Any file that would hold a secret, an account id, an internal hostname, or personal data
- `scripts/pii-denylist.sha256`, the file that would hold hashes of personal data

## Yellow

Write a short plan under `docs/plans/` before editing.

- `*/action.yml` and the payload scripts next to it
- `lib/**`
- `hooks/**` and `.pre-commit-hooks.yaml`
- `.github/workflows/**`
- `.github/dependabot.yml`
- `AGENTS.md`
- `docs/ci-contract.md` (conformance enforces this file in the product repositories and in this one)
- `docs/architecture/zones.md` (this map)
- `docs/plans/*.md` (the short plan for a yellow change; the pull request that finishes it deletes the note)
- `scripts/**`, other than the denylist
- `fixtures/**` (weakening a must-fail fixture weakens a gate)

## Green

Implement and verify. Summarise intent in the pull request.

- Other files under `docs/**`
- `tests/**`
- `README.md`
- `LICENSE`
- `.github/PULL_REQUEST_TEMPLATE.md`
