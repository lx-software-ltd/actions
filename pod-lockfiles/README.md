# Pod lockfiles

Runs `pod install --repo-update` and fails when `Podfile.lock` is missing or `git diff` shows it changed. A missing `Podfile` is skipped.

The calling job in a product repository runs on macOS. This action does not choose the runner.

## Inputs

| Input | Required | Default | Meaning |
| --- | --- | --- | --- |
| `working-directory` | yes | | Directory with the `Podfile`. |
| `setup` | no | `true` | `false` uses `pod` already on PATH. `true` runs `gem install cocoapods`. |

## Permissions

`contents: read`.
