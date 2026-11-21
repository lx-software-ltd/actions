# CodeQL

Runs `github/codeql-action` init and analyze for one language. The caller passes the category it already uses, so the security tab grouping does not change.

The calling job needs a checkout, `contents: read`, `security-events: write`, and `actions: read`. Python or another language toolchain is the caller's step, before this action.

## Inputs

| Input | Required | Default | Meaning |
| --- | --- | --- | --- |
| `language` | yes | | One CodeQL language. |
| `queries` | no | `security-extended` | Query suite. |
| `config-file` | no | empty | CodeQL config. Omitted when empty. |
| `category` | no | empty | Passed to analyze when set. |

The CodeQL action is `33d7b85da1a04171e211befe2c739303b9a4c066` (`v4.39.3`).
