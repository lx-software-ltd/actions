# Audit fail pins

## Scope

The `pip-audit` and `npm-audit` fail jobs still fail on the same findings. The pins are written in the test job under `RUNNER_TEMP` and are not files on `main`.

Leave these alone:

- `fixtures/python-requirements/fail`, `fixtures/dependency-submission/fail`, and `fixtures/node-lockfiles/fail`. They stay in Dependabot, ignored, with the security-updates group.
- The `pip-audit` pass fixture and the `npm-audit` pass job, which audits `fixtures/node-lockfiles/pass`.
- The assertions: `PYSEC-2018-28` for Requests, and a non-zero `npm audit` for `ip@2.0.1`.

## Why

`fixtures/pip-audit/fail/requirements.txt` pins `requests==2.19.1`. Five GitHub advisories match that version, including PYSEC-2018-28. `fixtures/npm-audit/fail` pins `ip@2.0.1` (GHSA-2p57-rm9w-gvfp). Those six are the open advisories on the manifests Dependabot watches. `lodash@4.18.1` matches none.

`ignore` in `.github/dependabot.yml` stops the bump pull request. Alerts follow manifests on the default branch. A release bump of `requests` would make the fail job pass. `ip@2.0.1` has no patched release.

## Change

- `pip-audit-fail` writes `requests==2.19.1` to `$RUNNER_TEMP` and passes that path to `./pip-audit`.
- `npm-audit-fail` writes an `ip@2.0.1` `package.json` and lockfile under `$RUNNER_TEMP` and passes that directory to `./npm-audit`.
- Delete `fixtures/pip-audit/fail/requirements.txt` and `fixtures/npm-audit/fail/`.
- Drop `/fixtures/pip-audit/fail` and `/fixtures/npm-audit/fail` from `.github/dependabot.yml`. The unit test locks that absence.

## How to check

```sh
python3 -m unittest discover -s tests -v
python3 scripts/check_action_layout.py
python3 scripts/check_pii.py
```

`npm audit --omit=dev --audit-level=high` on the generated lockfile exits 1 with GHSA-2p57-rm9w-gvfp. The Requests line is the same pin the current fixture audits.

After merge, the dependency graph on `main` no longer has those two manifests. The six alerts clear when that graph refreshes. The two fail jobs still fail.
