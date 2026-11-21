# SA-305 — lockfile checks

**Status**: This pull request
**Zone**: yellow

## Intent

Move the Node, Python, Flutter, and CocoaPods lockfile checks into composite actions. Each caller passes its own directories. The commands stay `npm ci`, a pin check that follows `-r`, `flutter pub get`, and `pod install --repo-update`.

## Fixtures

Node uses a real lockfile and a missing lockfile. Python uses a pinned include and an unpinned line. Flutter and CocoaPods skip when the project file is missing. Their fail fixtures put a stub on `PATH` and set `setup: false`, so this repository does not download Flutter or install CocoaPods. Product jobs leave `setup` at its default.

## Rollback

Revert this pull request.
