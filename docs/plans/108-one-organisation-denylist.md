# One organisation denylist

Zone: red for the header comments in `scripts/pii-denylist.sha256`. Yellow for the checker, the action wording, the test workflow, the fixtures, `AGENTS.md`, and `docs/ci-contract.md`. The digest lines stay byte for byte. The file stays in `scripts/`. This note is deleted by the pull request that finishes the work.

Issue 108. The 31 organisation digests apply in all five repositories, including `lx-software`. The published owner name in `lx-software` `site.json` stays allowed because `.json` is not scanned.

The checker loads `scripts/pii-denylist.sha256` from its own checkout (`Path(__file__).parents[1]`). A missing organisation file fails. An empty organisation file passes and checks nothing. The caller's `scripts/pii-denylist.sha256` is added when it exists. That default path is optional. An explicit `denylist-path` must exist. The two files are one set. There is no opt-out.

Shared payload stays under `../lib/`. This file is the exception, recorded in `AGENTS.md`, because moving it would be a second red-zone write.

Product pin bumps and deletions are separate pull requests, after the merge commit is tagged.
