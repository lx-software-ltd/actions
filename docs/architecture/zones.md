# Agent work zones

Autonomy follows blast radius. A change that touches more than one zone uses the stricter zone. If implementation spreads into a stricter zone, stop and ask.

## Red

Plan in chat and wait for explicit approval before any write.

- A workflow that requests `id-token: write` or calls AWS
- Any file that would hold a secret, an account id, an internal hostname, or personal data

## Yellow

Write a short plan under `docs/plans/` before editing.

- `*/action.yml` and the payload scripts next to it
- `lib/**`
- `hooks/**` and `.pre-commit-hooks.yaml`
- `.github/workflows/**`

## Green

Implement and verify. Summarise intent in the pull request.

- `docs/**`
- `tests/**`
- `fixtures/**`
- `README.md`
