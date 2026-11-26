# API contract

`evolvesprouts`, `siutindei`, `lx-software` and `findingalpha` serve one API shape. The address, the audiences, the credentials, the JSON and the errors below are the rules. A product may add an audience for a product role. It may not invent a second shape.

## Address

The hostname is `https://api.<product-domain>`. It is a regional API Gateway custom domain with TLS 1.2 or later. DNS is a DNS-only record that points at the `ApiCustomDomainTarget` stack output.

The custom domain maps to the stage at the root. A path has no stage name.

The `execute-api` hostname is disabled. Every client uses `api.<domain>`.

Every route starts with a major version and then an audience: `/v1/<audience>/<resource>`. `GET /health` is the only route without a version.

A client is configured with the origin only, for example `https://api.siutindei.com`. Client code adds `/v1/...`.

A website that calls the API through its own origin uses `https://<site>/api/<path>`. `<path>` is the same path on `api.<domain>`. The edge forwards only an allow-list of `/v1/public/` routes.

## Audiences

| Prefix | Caller | Credential |
| --- | --- | --- |
| `/v1/public/` | A website visitor, or an app user who has not signed in | None that names a person. The edge may add a usage-plan key, and a write may require Turnstile or device attestation. Throttles apply |
| `/v1/user/` | Any signed-in Cognito user | `Authorization: Bearer <Cognito token>` |
| `/v1/admin/` | Staff | The same header, plus a Cognito group |
| `/v1/partner/` | Scripts, agents, monitors and other companies | `Authorization: Bearer <issued token>` |
| `/v1/webhooks/<provider>` | Mailchimp, Meta and similar | The provider's signature, checked in the handler |
| `/health` | Monitors and deploy checks | None |

One audience has one kind of credential and one OpenAPI file.

A product may add an audience for a product role. `siutindei` keeps `/v1/manager/`. That audience is documented in `admin.yaml`.

A route under `/v1/public/` never returns personal data.

Routes under `/v1/public/` are listed one by one in API Gateway. A greedy `{proxy+}` route is allowed only under a prefix whose method carries an authorizer.

A handler for a partner route refuses a request that carries no authorizer context. A stack test proves that every method under `/v1/partner/` has the token authorizer, and that no method under `/v1/public/` has it.

## Credentials

`x-api-key` has one meaning: the API Gateway usage-plan key on a REST API. It names a client application. It is not a secret and it is not a token.

A token is a registered prefix, an underscore and random characters: `esk_`, `stk_`, `lxpk_`, `fapk_`. Each prefix has a gitleaks rule. Only a digest is stored. The plaintext is shown once.

The authorizer reads `Authorization`. It accepts the scheme `Bearer` in any letter case, and it denies on any error. It never decides on the HTTP method, because a cached answer is reused across methods. The handler checks writes and scopes.

A revoked token stops working within 5 minutes. The authorizer cache is 300 seconds at most.

Where a product has token writes, one stack parameter turns every one of them off.

## Requests and responses

Path segments are lower-case words joined by hyphens. Resources are plural nouns. A product is named by its repository name: `siutindei`, `evolvesprouts`, `lx-software`, `findingalpha`. A path has no file extension and no second version.

Path parameters are snake_case: `{job_id}`.

JSON field names and query parameter names are snake_case. Enum values are not renamed. The keys of a map whose keys are data, such as ids or currency codes, are not renamed.

A list takes `limit` and an opaque `cursor`. It returns `items` and `next_cursor`. `next_cursor` is null on the last page.

Every response made by a handler carries `x-request-id`. CORS exposes that header.

CORS names origins. The allowed methods include every method that a browser route uses. A stack test compares the two lists.

## Errors

A handler returns these members on every error. `Content-Type` stays `application/json` through `/v1`.

```json
{
  "type": "about:blank",
  "title": "Not Found",
  "status": 404,
  "detail": "No task has that id.",
  "code": "not_found",
  "request_id": "…",
  "errors": [{"field": "email", "message": "Enter an email address."}]
}
```

`code` is a stable lower_snake string for programs. The shared values are `invalid_request`, `unauthenticated`, `forbidden`, `not_found`, `conflict`, `rate_limited` and `internal_error`. A product may add more.

`errors` is present only for field errors.

The key a product already returns stays beside the new members through `/v1`: `error` in `evolvesprouts` and `siutindei`, `message` in `lx-software` and `findingalpha`.

Status codes are 400 for invalid input, 401 for no valid credential, 403 for not allowed, 404 for an unknown route or record, 409 for a conflict, and 429 for too many requests.

An error made by API Gateway itself has less. On a REST API the gateway response template returns `title`, `detail`, `code` (`gateway_error`), `request_id` and `message`. On an HTTP API the body is `{"message": "…"}` and cannot be changed. Clients accept both.

## Health

`GET /health` is open. It touches no database. It returns `{"status": "ok"}`. It has its own throttle. There is no second health route. A deeper check is a direct Lambda invocation.

## Change and documents

These are not breaking: a new route, a new optional input, a new response field, a new enum value. Clients ignore what they do not know.

These are breaking: anything removed or renamed, a changed type or meaning, stricter validation, a different credential. A breaking change needs a new major version of that route, for example `/v2/partner/orders`.

A route that appears in a sent email is never removed.

`docs/api/` holds one OpenAPI 3 file per audience: `public.yaml`, `admin.yaml` (admin, user and product roles), `partner.yaml`, `webhooks.yaml`. `servers` is `https://api.<domain>` with no path. CI lints the files and compares them with the route table.
