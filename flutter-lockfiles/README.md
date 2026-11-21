# Flutter lockfiles

Runs `flutter pub get` and fails when `pubspec.lock` is missing or `git diff` shows it changed. A missing `pubspec.yaml` is skipped and Flutter is not installed.

## Inputs

| Input | Required | Default | Meaning |
| --- | --- | --- | --- |
| `working-directory` | yes | | Directory with `pubspec.yaml`. |
| `flutter-version` | no | `3.47.9` | SDK when `setup` is true. |
| `setup` | no | `true` | `false` uses `flutter` already on PATH. |

Flutter is `subosito/flutter-action` `1a449444c387b1966244ae4d4f8c696479add0b2` (`v2.23.0`).

## Permissions

`contents: read`.
