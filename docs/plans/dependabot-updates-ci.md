# Dependabot update job

## Scope

Change `.github/dependabot.yml` only, plus a unit test that locks the fail-fixture entries.

Leave the fail-fixture manifests where they are. `requests==2.19.1`, `ip@2.0.1`, and the other vulnerable pins stay.

## Why

The Dependabot update job for `requests` in `/fixtures/pip-audit/fail` fails with `all_versions_ignored`. The same config is on the npm fail fixtures, so that job fails the same way once an advisory is grouped.

`ignore: dependency-name: "*"` is what keeps a security bump from turning a fail fixture green. Version updates already honour it and finish. Security updates are grouped by the organisation setting. That group records `all_versions_ignored` when an advisory still matches, and the update job fails.

A `security-updates` group in this file is the grouping for the directories it configures. The organisation catch-all applies only to directories this file does not list. `exclude-patterns: "*"` drops every dependency from the group, so each ignore stays an individual update. The individual path records no error.

## Change

On the pip and npm fail-fixture entries, keep `ignore` and add:

```yaml
groups:
  fail-fixtures:
    applies-to: security-updates
    patterns:
      - "*"
    exclude-patterns:
      - "*"
```

## How to check

```sh
python3 -m unittest discover -s tests -v
python3 scripts/check_action_layout.py
python3 scripts/check_pii.py
```

After merge, the next Dependabot security update for those directories completes. It opens no pull request. The fail fixtures stay on the vulnerable pins.
