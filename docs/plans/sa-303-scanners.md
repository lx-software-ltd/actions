# SA-303 — shared scanners

**Status**: This pull request
**Zone**: yellow

## Intent

Move Gitleaks, Checkov, CodeQL, and Semgrep into composite actions. Callers keep their synth step, rule packs, and exclude list. The finding count changes only by the in-source suppressions the filter removes, and that count is printed.

## Shared library

`lib/filter_sarif.py` drops SARIF results whose suppression kind is `inSource`. Checkov calls it. Semgrep calls `$GITHUB_ACTION_PATH/../lib/filter_sarif.py` and exits if that path is not a file.

## Container path

`semgrep-lib-path` runs `uses: ./semgrep` inside `semgrep/semgrep`. The scan script refuses to continue when the shared library path does not resolve. A green job means the path resolves in that container. The fallback, copying the filter into `semgrep/`, is unused while this job is green.

## Finding count

The filter test keeps an unsuppressed result, drops one `inSource` result, and reports the removed count. Gitleaks keeps version `8.30.1` and the same digest. Checkov is `v12.3141.0`. CodeQL is `v4.39.3` with the caller's language, queries, config, and category. Semgrep is `semgrep scan` plus the caller's `--config` and `--exclude-rule` values. A product pull request passes those current values and compares the printed removed count with the count from the previous run.

## Rollback

Revert this pull request.
