# README, licence, and security policy

## Scope

The same three files in five repositories: `actions`, `evolvesprouts`, `findingalpha`, `lx-software`, and `siutindei`. This pull request changes `actions` only. Each sibling gets its own pull request.

`README.md` and `LICENSE` are green here. `SECURITY.md` is new and is not on the zone map, so this note treats it as yellow. The zone map itself stays as it is.

## What differs today

- `README.md`. `actions` and `lx-software` say what the repository is. `evolvesprouts` and `siutindei` open with a tagline. `findingalpha` still says nothing is built. None of the five links the licence or the security policy.
- `LICENSE`. The five files are byte-identical and match the Apache-2.0 text. No README says which licence applies.
- `SECURITY.md`. `actions` has none. `findingalpha` has 25 lines. The other three run from 97 to 139 lines and mix the reporting policy with feature lists that `docs/architecture/security.md` already covers. Two of them still carry "add email if applicable".

## Change

One README order in every repository:

1. What the repository is for, and that it is public.
2. What is here.
3. Working here. Existing how-to text moves under this heading.
4. Documentation.
5. Security. One line that links `SECURITY.md`.
6. Licence. One line that links `LICENSE`.

One `SECURITY.md` in every repository:

1. Supported versions.
2. Report a vulnerability. GitHub private vulnerability reporting is on in all five. No email address.
3. What to expect. The response targets the four product files already publish.
4. Rules every repository follows. Each line is checked against the five workflow directories, the rulesets, and the repository settings.
5. This repository. The only section that differs.

`LICENSE` does not change.

## Leave alone

- Workflows, actions, scripts, fixtures, the zone map, and `AGENTS.md`.
- The response targets. They move into a table and keep their values.
- Product controls. They stay in each product's `docs/architecture/security.md`.

## How to check

```sh
python3 -m unittest discover -s tests -v
python3 scripts/check_action_layout.py
python3 scripts/check_pii.py
```

Every relative link in `README.md` and `SECURITY.md` resolves to a tracked file.
