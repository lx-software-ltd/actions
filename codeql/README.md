# CodeQL

Runs `github/codeql-action` init and analyze for one language. The caller passes the category it already uses, so the security tab grouping does not change.

The calling job needs a checkout, `contents: read`, `security-events: write`, and `actions: read`. Python or another language toolchain is the caller's step, before this action.

## Inputs

| Input | Required | Default | Meaning |
| --- | --- | --- | --- |
| `language` | yes | | One CodeQL language. |
| `queries` | no | `security-extended` | Query suite. For Python and JavaScript this also runs the alert-suppression query, so an in-source `lgtm` or `noqa` mark is uploaded. |
| `config-file` | no | empty | CodeQL config. Omitted when empty. |
| `category` | no | empty | Passed to analyze when set. |

The CodeQL action is `1bd86f2fdb4b86187fa4059f16f31a3202acc9ea` (`v4.39.4`).
