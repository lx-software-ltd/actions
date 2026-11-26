# API contract

Fails when an OpenAPI file breaks the shared API contract in [`docs/api-contract.md`](../docs/api-contract.md).

The calling job needs `python3` on `PATH` and a checkout. The action does not install Python. `ubuntu-26.04` provides it.

The reader uses the standard library. It reads the `servers` URLs and the keys directly under `paths` from block-style YAML. Flow-style YAML fails, and the message says the reader cannot follow it. It does not read schema property names, problem-details members, `securitySchemes`, or the route table. Those stay with each product's tests.

## Inputs

| Input | Required | Default | Meaning |
| --- | --- | --- | --- |
| `origin` | yes | | Server URL every file must use, exactly. |
| `directory` | no | `docs/api` | Directory of contract files, relative to the workspace. |
| `admin-prefixes` | no | `/v1/admin/,/v1/user/` | Prefixes allowed in `admin.yaml`. `siutindei` adds `/v1/manager/`. |
| `legacy-paths` | no | empty | File of paths that may stay in any contract file, one path per line. |

The directory may contain only `public.yaml`, `admin.yaml`, `partner.yaml`, and `webhooks.yaml`, plus the `legacy-paths` file when that file is inside the directory. A missing contract file is allowed. Any other extra file fails. `/health` is allowed in `admin.yaml`.

A path in `public.yaml` is `/v1/public` or starts with `/v1/public/`. A path in `partner.yaml` is `/v1/partner` or starts with `/v1/partner/`. A path in `webhooks.yaml` is `/v1/webhooks` or starts with `/v1/webhooks/`. A path in `admin.yaml` is `/health`, an admin-prefix root, or starts with one of `admin-prefixes`. A path listed in `legacy-paths` is allowed in any file.

A path segment is lower case, with hyphens. An underscore is allowed only inside `{snake_case}`. `{proxy+}` is allowed only as the last segment, and not in `public.yaml`. A segment has no dot and no second version such as `v2`. One path is not listed in two files.

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

Pin a commit on `main` that contains `api-contract/action.yml`. `templates/workflows/lint.yml` does not call this action yet, because the shared pin does not contain it. Each product adds the step when it bumps that pin.
