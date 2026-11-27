# Dependabot path for the actions pin

Zone: yellow. The note stays until the pull request that finishes this change deletes it.

Issue 102. Checked 27 Nov 2026.

## What is true

Callers pin one full commit SHA. The same line carries `# main YYYY-MM-DD`. The pre-commit `rev` is that SHA. Conformance fails when the pins differ. `scripts/bump_pins.py` rewrites all three and refuses a SHA that is not contained in `main`.

This repository has no tags. `git ls-remote --tags origin` is empty. `release-tags-create` blocks a `v*` tag. Organization admin is the bypass.

Dependabot resolves a GitHub Action from git tags. Its SHA update returns no commit unless a version tag exists. With no tag, cooldown has no candidate. That is why pull request 66 updated `bridgecrewio/checkov-action` and `github/codeql-action`, and findingalpha pull requests 2 and 33 updated `bridgecrewio/checkov-action`, while no job has moved an `lx-software-ltd/actions` pin.

The four product `github-actions` entries run weekly and set `cooldown.default-days` to 7. None excludes this repository. This repository's Dependabot file sets no cooldown. The platform default is 3 days.

The dependency name is the `uses` path. `lx-software-ltd/actions/require-jobs` is the name for that action. `lx-software-ltd/actions/*` covers every action in this repository.

Dependabot rewrites a workflow `uses` line. It leaves `.pre-commit-config.yaml` alone. It rewrites a trailing comment when a version ends that comment. `# main YYYY-MM-DD` is not a version.

A tagged pin updates to the latest tag's commit. An untagged pin updates to the head of the branch that contains it, and only when some version tag already exists. A tag on a later commit, while the pin itself has no tag, sends the update to `main` head.

The four products pin `133492f777ad088cdd0ef2e3d133843f79c13e93` (`Fold lockfile and Semgrep jobs under the required gates`, 27 Nov 2026 03:27 UTC), in workflows and in `.pre-commit-config.yaml`. The gates in this repository pin `1a3cca7c38163f8164c262323601c34a4df5b7a4` (`# main 2026-11-20`). Both commits are on `main`.

## Decision

The owner creates the tags. This repository's pull request does not. `release-tags` still blocks update and deletion.

The first tags go on both pinned commits, `1a3cca7c38163f8164c262323601c34a4df5b7a4` and `133492f777ad088cdd0ef2e3d133843f79c13e93`, so each pin follows tags. The later of those two is the latest tag. The next tag is the bump under test. Dependabot then has a candidate.

The cooldown exclusion waits for a log. The third tag, inside 7 days, is the product measurement. The `findingalpha` log has to say the candidate was filtered, or the exclusion stays out. `docs/decisions.md` keeps the sentence that the exclusion is not a measured result until that log exists.

`bump_pins.py` still writes the date comment and the pre-commit `rev` on the Dependabot branch. One pull request, one SHA.

## This change

### Tag

The owner puts a semver tag on `1a3cca7c38163f8164c262323601c34a4df5b7a4` and a later semver tag on `133492f777ad088cdd0ef2e3d133843f79c13e93`. Callers stay on the full SHA. The comment stays `# main YYYY-MM-DD`.

The product pin is already `133492f777ad088cdd0ef2e3d133843f79c13e93`, committed 27 Nov 2026. A third semver tag, on a later `main` commit, is what gives `findingalpha` a candidate. That commit has to be inside 7 days when the update runs.

### Measure

After the two pin tags, the owner runs the `github-actions` update once in this repository. The gate pin is the older SHA, and the latest tag is today's product pin, so the log is the cooldown case for the platform default of 3 days. Record, for `lx-software-ltd/actions/require-jobs`:

- the dependency name in the log
- the current SHA and the proposed SHA
- `Filtered out (cooldown)` or `Returning current version/ref (no viable filtered release)`, or the pull request that updates the pin

After the third tag, the owner runs the same update in `findingalpha`. The product pin is still `133492f777ad088cdd0ef2e3d133843f79c13e93`, and the new tag is inside 7 days, so that log is the product cooldown case. Record the same three lines.

A log that does not mention this dependency, or that reports no release, stops the change. No `exclude` is added.

### Exclusion

When the log shows cooldown, each product `github-actions` block keeps `default-days: 7` and gains:

```yaml
    cooldown:
      default-days: 7
      exclude:
        - "lx-software-ltd/actions/*"
```

The pattern is the name the log prints when that name is different. npm, pip, and pub keep their own cooldown. `siutindei` keeps the `infrastructure` label on this ecosystem.

This repository gains a cooldown block only when its own log shows the same skip. That block sets `default-days: 3` and the same `exclude`, so the platform default stays written down.

### Conformance on the Dependabot branch

Before merge, from the product checkout:

```sh
python3 /path/to/actions/scripts/bump_pins.py . <sha Dependabot wrote> --date <yyyy-mm-dd>
```

The script moves every workflow pin, the date comment, and the pre-commit `rev` onto that SHA. A SHA that is not contained in `main` is refused.

No `pre-commit` ecosystem entry. That would open a second pull request. No workflow pushes onto the Dependabot branch.

When the gate pin in this repository moves, the same pull request updates the SHA named in `docs/decisions.md`, `docs/ci-contract.md`, `AGENTS.md`, and `require-jobs/README.md`. `tests/test_workflow_conformance.py` uses that SHA as the fixture for a valid gate, and it updates with the pin.

### Decisions

The log picks the sentence in `docs/decisions.md`. Cooldown filtered the pin, and the exclusion is the measured result. Or it did not, and the exclusion stays out. The tag sentence stays: a `v*` tag exists so Dependabot can open the bump, the owner creates it, and `bump_pins.py` still writes the rev and the date.

## After this change

Issue 102 stays open until the tags exist, the log is recorded, the four product configs exclude `lx-software-ltd/actions/*` when the log says cooldown, and one product pull request has moved the workflow pin, the rev, and the date together with conformance green.

`bump_pins.py` remains the command for a bump that is not a Dependabot pull request.

## How to check

The measurement is the Dependabot log. The product YAML is not in this repository, so no unit test here asserts the `exclude` line.

```sh
python3 -m unittest discover -s tests -v
python3 scripts/check_action_layout.py
python3 scripts/check_pii.py
```
