# API contract

Fails when an OpenAPI file breaks the shared API contract in [`docs/api-contract.md`](../docs/api-contract.md).

The calling job needs `python3` on `PATH` and a checkout. The action does not install Python. `ubuntu-26.04` provides it.

The reader uses the standard library. It reads the `servers` URLs and the keys directly under `paths` from block-style YAML. Flow-style YAML fails, and the message says the reader cannot follow it. It does not read schema property names, problem-details members, `securitySchemes`, or the route table. Those stay with each product's tests.

## Inputs

| Input | Required | Default | Meaning |
| --- | --- | --- | --- |
| `origin` | yes | | Server URL every file must use, exactly. It matches `^https://[a-z0-9.-]+$`. |
| `directory` | no | `docs/api` | Directory of contract files, relative to the workspace. |
| `admin-prefixes` | no | `/v1/admin/,/v1/user/` | Prefixes allowed in `admin.yaml`. Each one matches `^/v1/[a-z0-9-]+/$`. `siutindei` adds `/v1/manager/`. |
| `legacy-paths` | no | empty | File of paths that may stay in any contract file, one path per line. |

The directory may contain only `public.yaml`, `admin.yaml`, `partner.yaml`, and `webhooks.yaml`, plus the `legacy-paths` file when that file is inside the directory. A missing contract file is allowed. Any other extra file fails. A subdirectory fails. `/health` is allowed in `admin.yaml`.

A path in `public.yaml` is `/v1/public` or starts with `/v1/public/`. A path in `partner.yaml` is `/v1/partner` or starts with `/v1/partner/`. A path in `webhooks.yaml` is `/v1/webhooks` or starts with `/v1/webhooks/`. A path in `admin.yaml` is `/health`, an admin-prefix root, or starts with one of `admin-prefixes`. A path listed in `legacy-paths` is allowed in any file. It skips the other path rules (prefix, segment, parameter). `{proxy+}` is still rejected.

A literal segment matches `^[a-z0-9]+(-[a-z0-9]+)*$`. A parameter matches `^[a-z][a-z0-9]*(_[a-z0-9]+)*$` inside braces. An empty segment fails. A segment has no second version such as `v2`. One path is not listed in two files, and a path repeated in one file is duplicated in that file. A legacy path that is not in a contract file fails.

Only the top-level `paths` key is the paths object. A quoted `paths` key is not opened, and a file with no `paths` block fails. A schema property named `paths` is not the paths object. A key directly under `paths` that does not start with `/` is not a path. An anchor on `paths` is not accepted. A schema property named `servers` is not the document servers list and is not a path-level servers key. A `servers` key under a path or operation fails. The checker cannot see authorizers, so `{proxy+}` is allowed only as the last segment in `partner.yaml` and `admin.yaml`, where the product tests prove the authorizer.

## Permissions

The calling job needs `contents: read` for the checkout. The action does not call the GitHub API.

## Example

```yaml
      - name: Check the API contract
        uses: lx-software-ltd/actions/api-contract@<40-hex> # main <yyyy-mm-dd>
        with:
          # template:set
          origin: https://api.example.com
          admin-prefixes: /v1/admin/,/v1/user/
          # template:end
```

`templates/workflows/lint.yml` does not call this action. Calling it from the template before this action is on `main` fails conformance. The order is:

1. Merge the pull request that adds this action.
2. A second actions pull request adds the lint step pinned at that merge SHA and deletes `test_lint_template_omits_the_action_until_it_is_on_main`.
3. Each product bumps to that SHA and adds the step in one pull request, and only after its own L2, S2 or E1 is on `main`.
4. `evolvesprouts` adds `/v1/admin/assets/{id}/grants/{grantId}` to `docs/api/legacy-paths.txt`.
