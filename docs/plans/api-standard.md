# Plan: one API standard across the product repositories

**Status**: Ready to run. Nothing in this plan has been done yet.
**Zone**: yellow in this repository. Red in each product repository (see section 3).

The analysis behind this plan is the canvas
[API standard across the product repositories](https://cursor.com/canvas/store-a4f6a4d5-0af5-4c73-8b46-c72fb8812abb/9566106d-cb2e-4865-811e-e60252d80ef2).
This file stands on its own. An agent can run it without the canvas.

All dates are Hong Kong time.

## 1. Goal

`evolvesprouts`, `siutindei`, `lx-software` and `findingalpha` serve one API
shape: `https://api.<domain>/v1/<audience>/<resource>`, one credential per
audience, snake_case JSON, one error shape, one OpenAPI file per audience.
`actions` holds the written standard and a check for it.

The owner made these six choices on 26 Nov 2026. They are settled. Do not
reopen them.

| Choice | Decision |
| --- | --- |
| Name of the token audience | `/v1/partner` |
| Token header | `Authorization: Bearer <token>` |
| JSON field names | snake_case everywhere. `lx-software` and `findingalpha` are converted |
| Existing website routes | They move under `/v1/public/` with the other renames. The site prefix becomes `/api` |
| siutindei domain parameters | `ApiCustomDomainName` takes over from `ApiSecondaryCustomDomain*` now |
| Notice periods | None, for every audience. A caller changes on the day the server changes |

"No notice" covers callers that hold a credential or are deployed by the
owner on demand. It does not cover three things that cannot change on
demand. These keep working:

- A link inside an email that was already sent.
- A callback address held in a provider's dashboard, until the owner changes
  it there.
- A public website build that is live, until the next build is promoted.

## 2. Non-goals

These stay as they are. Do not start them in this run.

- Scope names (`<area>:read`, `<area>:write`), a stored digest-algorithm
  name, required token expiry.
- `Idempotency-Key`, money and time formats, upload naming, action naming
  (`/assets/delete` and similar), the shape of a `202` job.
- `nextToken` and `nextCursor` inside `lx-software` and `findingalpha`
  handlers. After this plan they appear on the wire as `next_token` and
  `next_cursor`. Making them one name is a later change.
- Renaming stack outputs to one `ApiBaseUrl`. `AdminApiBaseUrl` is unmarked
  text in `templates/workflows/deploy-admin-web.yml`, so the name stays and
  only its value changes.
- Generated API clients, a staging API, a shared authorizer package.
- `ai-cxo`. It has no API. It starts on the standard when it gets one.

## 3. How to run this plan

### Access

The agent needs write access to five repositories under `lx-software-ltd`:
`actions`, `findingalpha`, `lx-software`, `siutindei`, `evolvesprouts`. All
five are public. Nothing private goes into a commit, a pull request or a
plan note: no secret, account id, API id, certificate ARN, `execute-api`
hostname or personal data. `siutindei/docs/plans/siutindei-domain-consolidation.md`
contains identifiers of that kind. Do not copy them.

### Approval for red-zone paths

Most of this work is in red-zone paths of the product repositories. The
owner's kickoff message is the explicit approval those zone maps ask for. It
covers exactly these paths and no others:

| Repository | Red paths approved |
| --- | --- |
| `findingalpha` | `backend/infrastructure/**`, `contracts/**` |
| `lx-software` | `backend/infrastructure/**`, `backend/lambda/public_api_authorizer/**`, `contracts/**`, `scripts/manage-public-api-keys.py` |
| `siutindei` | `backend/infrastructure/**`, `backend/lambda/authorizers/**`, `backend/src/app/auth/**`, `scripts/deploy/build_amplify_config.py`, `.github/workflows/deploy-backend.yml` |
| `evolvesprouts` | `backend/infrastructure/**`, `backend/lambda/authorizers/**`, `.github/workflows/deploy-training.yml` |

Read each repository's `docs/architecture/zones.md` before the first write
there. Every other path follows its own zone: yellow paths get the plan note
below, green paths need nothing. If the work needs a red path that is not in
this table, stop and report. These stay untouched in every repository:
`_require_admin`, `write_blocked` in `lx-software`, `backend/db/**`, billing
files, `scripts/pii-denylist.sha256`, `.cursor/hooks*`,
`.pre-commit-config.yaml`.

The red zones also ask that a person pairs on the change. Here that is the
owner's review of each pull request before merging it.

Each product repository also wants a plan note. In the first pull request of
each repository, add `docs/plans/api-standard.md` from that repository's
`docs/plans/_template.md`. Keep it short: the goal, the files, the
invariants, a link to this file at a commit SHA. The last pull request in
that repository deletes the note. Where a repository has one pull request,
the note is its first commit and its last commit deletes it.

### Rules for the run

- Open pull requests. Never merge, never deploy, never run a deploy
  workflow, never create a `v*` tag.
- One branch per pull request. Inside one repository the pull requests are
  stacked: each branch starts from the one before it, and its base is that
  branch.
- Pull requests marked **draft** in section 5 are opened as drafts. Each
  carries a "Do not merge before" list as the first lines of its body.
- Use the repository's pull request template. Fill in Evidence with the
  commands run and their results.
- Line numbers in this plan come from the commits in section 15. They are
  hints. Search for the symbol when a line has moved.
- Run every check the repository's `AGENTS.md` names before pushing. Fix
  what the change breaks. Report what still fails, with its output.
- Tests come first in yellow and red paths: write or change the test, see it
  fail, then change the code.

### Stop and report when

- A fact in section 15 turns out to be false.
- A stack test shows a resource count over the limits in sections 10 and 11.
- A CloudFormation change set in a pull request's `cdk-diff` job shows a
  replacement of an API Gateway domain name, a Cognito pool or a database.
- A key appears in a response that the wire codec cannot round-trip
  (section 7) and the fix is not one of the three listed there.

## 4. The standard

This section becomes `actions/docs/api-contract.md` (work package A1). Copy
the rules. Leave out the migration detail.

### 4.1 Address

- The hostname is `https://api.<product-domain>`. It is a regional API
  Gateway custom domain with TLS 1.2 or later and a DNS-only record that
  points at the `ApiCustomDomainTarget` stack output.
- The custom domain maps to the stage at the root. There is no stage name in
  a path.
- The `execute-api` hostname is disabled. Every client uses `api.<domain>`.
- Every route starts with a major version, then an audience:
  `/v1/<audience>/<resource>`. `/health` is the only route without a
  version.
- A client is configured with the origin only, for example
  `https://api.siutindei.com`. Client code adds `/v1/...`.
- A website that calls the API through its own origin uses
  `https://<site>/api/<path>`, where `<path>` is the same path on
  `api.<domain>`. The edge forwards only an allow-list of `/v1/public/`
  routes.

### 4.2 Audiences

| Prefix | Caller | Credential |
| --- | --- | --- |
| `/v1/public/` | A website visitor, or an app user who has not signed in | None that names a person. Edge controls only: the usage-plan key that the edge adds, Turnstile on writes, device attestation, throttles |
| `/v1/user/` | Any signed-in Cognito user | `Authorization: Bearer <Cognito token>` |
| `/v1/admin/` | Staff | The same header, plus a Cognito group |
| `/v1/partner/` | Scripts, agents, monitors, other companies | `Authorization: Bearer <issued token>` |
| `/v1/webhooks/<provider>` | Mailchimp, Meta and similar | The provider's signature, checked in the handler |
| `/health` | Monitors and deploy checks | None |

- One audience has one kind of credential and one OpenAPI file.
- A product may add an audience for a product role. `siutindei` keeps
  `/v1/manager/`. It is documented in `admin.yaml`.
- A route under `/v1/public/` never returns personal data.
- Routes under `/v1/public/` are listed one by one in API Gateway. A greedy
  `{proxy+}` route is allowed only under a prefix whose method carries an
  authorizer.
- A handler for a partner route refuses a request that carries no authorizer
  context. A stack test proves that every method under `/v1/partner/` has
  the token authorizer and that no method under `/v1/public/` has it.

### 4.3 Credentials

- `x-api-key` has one meaning: the API Gateway usage-plan key on a REST API.
  It names a client application. It is not a secret and not a token.
- A token is a registered prefix, an underscore, and random characters:
  `esk_`, `stk_`, `lxpk_`, `fapk_`. Each prefix has a gitleaks rule. Only a
  digest is stored. The plaintext is shown once.
- The authorizer reads `Authorization`, accepts the scheme `Bearer` in any
  letter case, and denies on any error. It never decides on the HTTP method,
  because a cached answer is reused across methods. The handler checks
  writes and scopes.
- A revoked token stops working within 5 minutes. The authorizer cache is
  300 seconds at most.
- One stack parameter turns off every write made with a token, where the
  product has token writes.

### 4.4 Requests and responses

- Path segments are lower-case words joined by hyphens. Resources are plural
  nouns. A product is named by its repository name: `siutindei`,
  `evolvesprouts`, `lx-software`, `findingalpha`. No file extension. No
  second version inside a path.
- Path parameters are snake_case: `{job_id}`.
- JSON field names and query parameter names are snake_case. Enum values and
  the keys of a map whose keys are data (ids, currency codes) are not
  renamed.
- A list takes `limit` and an opaque `cursor`. It returns `items` and
  `next_cursor`, which is null on the last page.
- Every response made by a handler carries `x-request-id`. CORS exposes that
  header.
- CORS names origins. The allowed methods include every method that a
  browser route uses. A stack test compares the two lists.

### 4.5 Errors

A handler returns these members on every error. `Content-Type` stays
`application/json` through `/v1`.

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

- `code` is a stable lower_snake string for programs. The shared values are
  `invalid_request`, `unauthenticated`, `forbidden`, `not_found`,
  `conflict`, `rate_limited` and `internal_error`. A product may add more.
- `errors` is present only for field errors.
- The key a product returns today stays beside the new members through
  `/v1`: `error` in `evolvesprouts` and `siutindei`, `message` in
  `lx-software` and `findingalpha`.
- Status codes: 400 invalid input, 401 no valid credential, 403 not allowed,
  404 unknown route or record, 409 conflict, 429 too many requests.
- An error made by API Gateway itself has less. On a REST API the gateway
  response template returns `title`, `detail`, `code` (`gateway_error`),
  `request_id` and `message`. On an HTTP API the body is `{"message": "…"}`
  and cannot be changed. Clients accept both.

### 4.6 Health

`GET /health` is open, touches no database, returns `{"status": "ok"}`, and
has its own throttle. There is no second health route. A deeper check is a
direct Lambda invocation.

### 4.7 Change and documents

- Not breaking: a new route, a new optional input, a new response field, a
  new enum value. Clients ignore what they do not know.
- Breaking: anything removed or renamed, a changed type or meaning, stricter
  validation, a different credential. A breaking change needs a new major
  version of that route, for example `/v2/partner/orders`.
- A route that appears in sent email is never removed.
- `docs/api/` holds one OpenAPI 3 file per audience: `public.yaml`,
  `admin.yaml` (admin, user and product roles), `partner.yaml`,
  `webhooks.yaml`. `servers` is `https://api.<domain>` with no path. CI
  lints the files and compares them with the route table.

## 5. Pull requests and merge order

| Id | Repository | Content | Draft | Merge when |
| --- | --- | --- | --- | --- |
| A1 | `actions` | `docs/api-contract.md`, decisions | no | Any time |
| F1 | `findingalpha` | Whole cutover | no | Any time. Token holders change the same day |
| L1 | `lx-software` | CORS `PATCH`, error members, request id | no | Any time |
| L2 | `lx-software` | Whole cutover | no | After L1, and after F1 is deployed and passes its checks in section 13 |
| L3 | `lx-software` | Close `execute-api`, remove old webhook paths | yes | Not before 25 Dec 2026, and after the Meta callback is changed |
| S1 | `siutindei` | Domain parameter swap | no | Any time. Read the change set first |
| S2 | `siutindei` | Server cutover | no | After S1 is deployed, at a quiet hour |
| S3 | `siutindei` | Website on `/api/v1/public/` | no | After S2 is deployed and the Cloudflare policy is applied |
| S4 | `siutindei` | Remove the old website paths at the edge | yes | After the S3 site is promoted |
| E1 | `evolvesprouts` | Server: new paths beside old, token cutover | no | Any time. Token holders change the same day |
| E2 | `evolvesprouts` | Clients on the new paths | no | After E1 is deployed |
| E3 | `evolvesprouts` | Remove old paths, `/prod` and `/www` | yes | After the E2 sites are promoted, the variable is changed and the three callbacks are changed |
| A2 | `actions` | `api-contract` check action and the template step | no | After the product OpenAPI files exist on `main` |

Order of work for the agent: A1, F1, L1, L2, L3, S1, S2, S3, S4, E1, E2, E3,
A2. `findingalpha` goes first because it is the smallest and proves the wire
codec before `lx-software` takes it.

One run cannot finish two things:

- The product pin bump for A2. `scripts/bump_pins.py` refuses a SHA that is
  not on `main`, so the bump waits for the owner to merge A2. It is one
  command and one pull request per product.
- The three draft pull requests. Each waits for an owner step.

## 6. `actions`

### A1. The written standard (green)

1. Add `docs/api-contract.md` from section 4.
2. Add a short "API" section to `docs/decisions.md`: the six choices in
   section 1, the rule that `/v1/public/` routes are listed one by one, and
   the rule that a route in sent email is never removed.
3. Link the new file from `README.md` beside `docs/ci-contract.md`.

`docs/ci-contract.md` is not edited. Checks: the three commands in
`AGENTS.md`.

### A2. The check (yellow)

This file is the plan note for A2. A2 deletes it.

1. Add `api-contract/action.yml`, `api-contract/check.py` and a README.
   The payload is standard-library Python 3.12 with no YAML package, so it
   reads only what a line reader can read safely from block-style YAML: the
   `servers` URLs and the keys directly under `paths`.
2. Inputs: `origin` (for example `https://api.siutindei.com`), `directory`
   (default `docs/api`), `admin-prefixes` (default `/v1/admin/,/v1/user/`;
   `siutindei` adds `/v1/manager/`), `legacy-paths` (optional file, one
   path per line; `lx-software` lists its old routes that stay).
3. It fails when:
   - a file in the directory is not `public.yaml`, `admin.yaml`,
     `partner.yaml` or `webhooks.yaml`;
   - a `servers` URL is not exactly `origin`;
   - a path in `public.yaml` does not start with `/v1/public/`, a path in
     `partner.yaml` with `/v1/partner/`, a path in `webhooks.yaml` with
     `/v1/webhooks/`, or a path in `admin.yaml` with one of
     `admin-prefixes`. `/health` is allowed in `admin.yaml`. A path listed
     in `legacy-paths` is allowed in any file;
   - a path segment has an upper-case letter, an underscore outside braces,
     a dot, or is a second version such as `v2`;
   - a path parameter is not snake_case;
   - one path is in two files;
   - the file is flow-style YAML that the reader cannot follow. Say so in
     the message.
4. Fixtures under `fixtures/api-contract/`: one passing tree, and one
   failing tree per rule. Add the passing and failing jobs to
   `.github/workflows/test.yml` and to the `test` gate's `needs`. Add unit
   tests under `tests/`.
5. Add one step to the `lint-openapi` job in
   `templates/workflows/lint.yml`, after the Redocly step. The action is
   pinned by a SHA on `main`, like every other pin in the templates. The
   inputs sit in a `# template:set` block, because the origin differs by
   product.
6. Update `README.md`.

After the owner merges A2, each product runs `scripts/bump_pins.py` and adds
the new step to its `lint.yml`. Write that as the last line of the A2 pull
request body.

## 7. The wire codec for `lx-software` and `findingalpha`

Both products store camelCase attribute names in DynamoDB and return items
as stored. Renaming the storage is not safe. So the names change at the HTTP
boundary only: handlers, storage and TypeScript stay camelCase, and one
codec on each side converts.

Build the codec once in `findingalpha` (F1). Copy it to `lx-software` (L2)
without edits. The three shared files are byte-identical in both
repositories. Each file's header says so.

### 7.1 Files

| File | Content |
| --- | --- |
| `contracts/wire-format.json` | The field lists in 7.3. Product-specific |
| `contracts/wire-format-cases.json` | Input and output pairs that both implementations must pass. Shared |
| Python `wire_format.py` | In `backend/lambda/engine/` (`findingalpha`) and `backend/lambda/admin/` (`lx-software`). Shared |
| TypeScript `apps/admin_web/src/lib/wireFormat.ts` | Shared |

`scripts/sync-contracts.py` copies the contract to the Lambda and to
`apps/admin_web/src/lib/contracts/generated.ts`, as it does for the other
contracts. `scripts/check-contracts.py` checks the copies.

### 7.2 Key conversion

Two patterns:

- CAMEL: `^[a-z][a-zA-Z0-9]*$` with at least one upper-case letter.
- SNAKE: `^[a-z][a-z0-9]*(_[a-z][a-z0-9]*)+$`.

To the wire: a key in `renames` takes its listed name. Otherwise a CAMEL key
has every upper-case letter replaced by an underscore and the lower-case
letter. Any other key is unchanged.

From the wire: a key that is a value in `renames` takes the key it came
from. Otherwise a SNAKE key has every `_x` replaced by `X`. Any other key is
unchanged.

The two directions are exact inverses on CAMEL and SNAKE keys: `s3Key`
becomes `s3_key` and back, `top10Items` becomes `top10_items` and back. A
key with a hyphen, a colon, a dot, a leading capital or a leading digit is
never touched. Only keys are converted. Values, including enum values such
as `siuTinDei`, are never converted.

### 7.3 The contract

```json
{
  "renames": {"apiURL": "api_url"},
  "verbatimKeys": ["next_cursor"],
  "mapFields": {"holdOverrides": 1, "toolMatrix": 2},
  "opaqueFields": ["register"],
  "rootMaps": {"GET /v1/admin/fx/rates": 1},
  "excludedRoutes": ["/v1/webhooks/"]
}
```

The values above are examples. The real lists come from the code.

- `renames`: a key with two or more capitals in a row would become
  `api_u_r_l`. List it here with a readable name. The values are unique.
- `verbatimKeys`: a key that is already snake_case inside the handlers. It
  is not converted in either direction.
- `mapFields`: a key whose value is a map with data as its keys. The number
  is how many levels of keys are data. Those keys are kept. The values below
  them are converted as usual.
- `opaqueFields`: a key whose whole value passes through untouched.
- `rootMaps`: a route whose top-level body is itself such a map.
- `excludedRoutes`: path prefixes the codec skips in both directions.
  Webhooks and the legacy email-link routes go here.

`mapFields`, `opaqueFields` and `verbatimKeys` match a key name wherever it
appears. If one name is a data-keyed map in one response and an ordinary
object in another, rename the handler's key in one of the two places. That
is one of the three allowed fixes. The other two are adding a `renames`
entry and adding a list entry.

Known data-keyed maps to start from. Confirm each in the code.

- `lx-software`: the finance top level by house id, the board tool matrix by
  tool id then persona id, a seat's `tools`, `holdOverrides`,
  `boundaries.holds`, `modelBySeat`, staff overrides by seat id, résumé
  `layout.overrides` by paragraph id, FX rates by currency code, the
  dictionary form of `allowList`.
- `findingalpha`: `done` by task id, `sectors`, `shareSources`,
  `coverage.flows`, `coverage.stocks`, `coverage.shareFlows`, `groups`,
  `factors` and `z` by factor id. `register` (the whole `methodology.json`)
  and the backtest `equity.json` are opaque.

### 7.4 Where the codec runs in Python

At the top of the HTTP branch of `lambda_handler`, and nowhere else. SQS
batches and internal events are not touched.

Inbound, unless the route is excluded:

- JSON body: parse, convert keys from the wire, serialise again.
- `queryStringParameters` and `rawQueryString`: convert the names. Handlers
  read both.
- `pathParameters`: convert the names. Route templates use `{job_id}`.
  Handlers keep reading `jobId`.

Outbound, unless the route is excluded:

- Only when the response `Content-Type` is JSON, the body is a string, and
  `isBase64Encoded` is not set. Parse, convert keys to the wire, serialise.
- PDF, HTML and plain-text responses pass through.
- A body that does not parse passes through and is logged.

Running at the entry, and not inside `_json_response`, matters. Five
responses in `lx-software` do not use `_json_response`, and
`board_public_api.py` redacts a response body after the handler built it.
The codec runs after all of that.

Error bodies are built in camelCase like every other body (`requestId`). The
codec turns them into the names in section 4.5.

### 7.5 Where the codec runs in the admin site

In `apps/admin_web/src/lib/apiAdminClient.ts`, around the real `fetch` only.

- Request: convert the names in the path's query string. When the body is a
  JSON string, parse, convert, serialise. Other bodies pass through.
- Response: when the content type is JSON, convert the keys from the wire.
  `adminFetch` returns a `Response`, so return a new `Response` with the
  converted body and the same status and headers.
- The mock branch (`VITE_ADMIN_MOCK=1`) skips the codec. Mock handlers and
  fixtures stay camelCase. Only their path patterns change.

TypeScript types, hooks and components do not change.

### 7.6 Tests

- `contracts/wire-format-cases.json` is run by a Python unit test and by a
  Vitest test. It covers: plain keys, digits, a `renames` entry, a verbatim
  key, a one-level and a two-level map field, an opaque field, a root map,
  lists of objects, an enum value that looks like a key, and a key with a
  colon.
- Python handler tests reach `lambda_handler` through one helper. The helper
  converts the test's camelCase body and query to the wire, and asserts that
  converting back gives the same value. It calls `lambda_handler`. For a
  JSON response it asserts that the body round-trips, and that no key
  outside a map or opaque field is CAMEL or has two single-letter segments
  in a row. It returns the body converted back to camelCase.
  The existing assertions on camelCase keys therefore stay as they are.
- A guard test fails when a test file other than the helper calls
  `lambda_handler` for an HTTP event.
- Add wire-level tests that read the raw body: one per area, plus an error
  body, a list with a cursor, a query parameter and a path parameter.
- A response key that fails the helper is fixed in the contract, not in the
  helper.

## 8. `findingalpha` (F1)

One pull request. Backend deploy triggers the admin deploy, so the admin
site is broken for the minutes between the two. The owner is its only user.

### Routes

`backend/infrastructure/lib/api-routes.ts`:

| Today | After |
| --- | --- |
| `GET /health` | The same. The body becomes `{"status": "ok"}` |
| Every JWT route `/<path>` | `/v1/admin/<path>`. `/me` becomes `/v1/admin/me`, because the handler requires the `admin` group |
| `{taskId}`, `{jobName}`, `{runId}` | `{task_id}`, `{job_name}`, `{run_id}` |
| `GET /public` | `GET /v1/partner` |
| `GET /public/{proxy+}` | `GET /v1/partner/{proxy+}` |
| `PUT,POST /public/{proxy+}` | `PUT,POST /v1/partner/{proxy+}` |

Throttles keep their values and move to the new route keys.

### Steps

1. Plan note (section 3).
2. Infrastructure. `http-api.ts`, `lib/authorizers.ts`, `bin/app.ts`.
   - The key authorizer's identity source becomes
     `$request.header.Authorization`. The cache stays 60 seconds.
   - CORS: allowed headers `authorization` and `content-type`. Expose
     `x-request-id`. Add a stack test that the allowed methods cover every
     method on a JWT route.
   - `AdminApiBaseUrl` becomes `https://<custom domain>` when the custom
     domain condition is true, and the `execute-api` URL when it is false.
     The content security policy origin at `bin/app.ts:52` follows the same
     value.
   - `DisableExecuteApiEndpoint` is true when the custom domain is
     configured, and false when it is not. No email and no provider holds
     the old hostname in this product.
   - Update `findingalpha-stack.test.ts` (routes near 244, throttles near
     361, CORS near 424) and add tests for the three items above.
3. Authorizer. `backend/lambda/public_api_authorizer/`. Read the token from
   `Authorization`, accept `Bearer` in any case, deny when the scheme or
   the token is missing. Update its tests.
4. Routing. `api_handler.py`, `public_api.py`, `http_common.py`.
   - One function splits a path into an audience and an inner path:
     `/v1/admin/settings` gives `admin` and `/settings`.
   - The route table keeps inner paths. A route answers only under its own
     audience. A JWT route requested under another prefix is 404.
   - `public_api.resolve` strips `/v1/partner` where it stripped `/public`.
   - `/health` returns `{"status": "ok"}`.
5. Errors and request id. `_json_response` in `http_common.py` adds
   `x-request-id` from `requestContext.requestId`. Error bodies gain the
   members in section 4.5 and keep `message`.
6. Wire codec (section 7). Contract, Python, TypeScript, the test helper.
   The request fields today are `portfolioSize`, `confirmDeletion`, `stop`,
   `done`, `ingestEnabled`, `committeeEnabled`, `tradingEnabled`,
   `leverageEnabled` and `briefEmailEnabled`. The only query parameter is
   `limit`.
7. Admin site. `apiAdminClient.ts` gets the codec. Paths in the 15 hook
   files and in `lib/mock/routes/system.ts` gain `/v1/admin`.
8. Token tooling. `scripts/manage-public-api-keys.py` prints the new header
   and path in its hint. Update its test.
9. OpenAPI. Add `docs/api/admin.yaml` and `docs/api/partner.yaml`, a
   `redocly.yaml` copied from `evolvesprouts`, and a script that fails when
   the files and `api-routes.ts` disagree. Every path has its methods,
   parameters, security scheme and a summary. Error responses point at one
   shared `Problem` schema. Other bodies may be
   `type: object, additionalProperties: true` for now. State in each file
   that field names are snake_case.
10. Workflow. Add the `lint-openapi` block to `.github/workflows/lint.yml`
    exactly as `actions/templates/workflows/lint.yml` has it, and add the
    job to the `lint` gate's `needs`. The `openapi` capability turns on when
    `docs/api/*.yaml` exists, and conformance then requires the block.
11. Docs. Replace every `x-api-key` and `/public` reference (18 places).

### Done when

`npm test` in `backend/infrastructure`, the Python tests, the admin site's
`npm test`, `python3 scripts/check-contracts.py`, the Redocly lint and the
route comparison all pass.

## 9. `lx-software`

### L1. Additive fixes

1. Plan note.
2. `admin-http-api.ts` near line 84: add `PATCH` to the CORS allowed
   methods. The admin site sends `PATCH` from `useResume.ts`, and the
   preflight is refused today. Add a stack test that the allowed methods
   cover every method on a JWT route.
3. `http_common.py`: `_json_response` adds `x-request-id`. Error bodies gain
   the members in section 4.5 and keep `message` and `reason`. CORS exposes
   `x-request-id`.

Nothing is renamed in L1.

### L2. Cutover

#### Routes

`backend/infrastructure/lib/admin-api-routes.ts`, 181 entries. Apply these
rules to every entry.

| Today | After |
| --- | --- |
| `GET /health` | The same |
| `auth: "jwt"`, `/<path>` | `/v1/admin/<path>`. `/me` becomes `/v1/admin/me` |
| `auth: "apiKey"`, `/public/<path>` | `/v1/partner/<path>` |
| `/webhooks/meta`, `/webhooks/meta/siutindei` | `/v1/webhooks/meta`, `/v1/webhooks/meta/siutindei` |
| `/public/newsletter/<rest>`, `/public/outreach/<rest>` | `/v1/public/newsletter/<rest>`, `/v1/public/outreach/<rest>` |

Renames inside `<path>`, for JWT and token routes alike:

| Today | After |
| --- | --- |
| `/siu-tin-dei` | `/siutindei` |
| `/evolve-sprouts` | `/evolvesprouts` |
| `/fx/v2/rates` | `/fx/rates` |
| `/aws/usage.pdf` | `/aws/usage/pdf` |
| `{jobId}`, `{personaId}` and every other camelCase parameter | snake_case |

`/lx-software` keeps its hyphen, because that is the repository name.

Old routes that stay:

| Route | Until |
| --- | --- |
| `GET,POST /public/outreach/unsubscribe/{token}` | For good. It is in sent email |
| `GET /public/newsletter/confirm/{token}` | For good |
| `GET,POST /public/newsletter/unsubscribe/{token}` | For good |
| `GET,POST /webhooks/meta`, `GET,POST /webhooks/meta/siutindei` | L3 |

`/public/newsletter/subscribe` has no caller and no email link. It moves
with no old copy. The route count goes from 220 to about 229. The HTTP API
quota is 300.

The throttle classes keep their values. Their keys in `admin-http-api.ts`
(near line 196) follow the new route keys. Old routes that stay keep their
throttle.

#### Steps

1. Infrastructure.
   - Routes and throttles as above.
   - `admin-api-authorizers.ts`: the key authorizer's identity source
     becomes `$request.header.Authorization`. The cache stays 60 seconds.
   - CORS allowed headers: `authorization`, `content-type`. `x-api-key` goes.
   - `admin-outputs.ts` near line 188: `AdminApiBaseUrl` is
     `https://<custom domain>` when `UseApiCustomDomain` is true, and the
     `execute-api` URL when it is false.
     `scripts/deploy/check-admin-spa-settings.sh` keeps reading that output.
   - `bin/app.ts:78`: the content security policy allows the custom domain
     origin. Keep the `execute-api` origin beside it until L3.
   - `params/production.json`: `lxsoftware:SiutindeiAdminApiBaseUrl` becomes
     `https://api.siutindei.com`.
   - `execute-api` stays enabled in L2. The test at
     `lxsoftware-stack.test.ts:476` stays.
2. Authorizer. `backend/lambda/public_api_authorizer/handler.py` reads
   `Authorization` as in F1.
3. Routing. `dispatch.py`, `router.py`, `http_common.py`,
   `board_public_api.py`, `board_routes.py`.
   - The same audience split as F1. The route table keeps inner paths, with
     the renames above. `BOARD_BASE_PATH` becomes `/siutindei/board`.
   - The partner branch strips `/v1/partner` where `dispatch.py` near line
     307 stripped `/public`.
   - A small table maps each old route that stays onto its new path before
     matching.
   - `_require_admin` and `write_blocked` are not edited. If either reads a
     path, pass it the inner path it gets today.
   - Tests: an admin path under `/v1/partner` reaches only what the token
     scopes allow, a partner path with no authorizer context is refused, and
     each old route that stays still answers.
4. Email links. `board_newsletter.py` and `board_outreach.py` build
   `confirm_url`, `unsubscribe_url` and the `List-Unsubscribe` headers on
   the new `/v1/public/...` paths.
5. Cross-product client. `board_catalog_import.py` requests
   `v1/admin/imports/presign` and `v1/admin/imports` on the origin. In
   `siutindei`, `scripts/ops/board-importer` has the default
   `API_BASE=https://api.siutindei.com/v1`. Change it to the origin in S2.
6. Wire codec. Copy the three shared files from `findingalpha`. Write
   `contracts/wire-format.json` for this product. The query names in use
   are `taskId`, `meetingId` and `missingPlaceId`. Exclude
   `/v1/webhooks/`, `/webhooks/` and the old email-link routes. Move the
   tests onto the helper: about 77 test files assert on camelCase keys
   today.
7. Tests' path literals. About 524 literals in 36 test files and 72 in 7
   production files hold an old path. Change them with a script, review the
   diff, and do not commit the script.
8. Admin site. The codec in `apiAdminClient.ts`. `BOARD_API_BASE` in
   `src/lib/board/paths.ts` becomes `/v1/admin/siutindei/board`. About 251
   path literals in 40 files, and the mock patterns in
   `src/lib/mock/routes/index.ts`.
9. Token tooling. `scripts/manage-public-api-keys.py` hint text.
10. OpenAPI. `docs/api/admin.yaml`, `partner.yaml`, `public.yaml`,
    `webhooks.yaml`, `redocly.yaml`, and the comparison script, as in F1
    step 9. Generate the path list from the route table. The old routes that
    stay are listed with `deprecated: true`.
11. Workflow. The `lint-openapi` block, as in F1 step 10.
12. Docs. `docs/deployment/admin-website.md` (near 344 and 455),
    `docs/architecture/security.md` and every other place that names
    `x-api-key`, `/public/` or an old path. The Meta webhook instructions name the new path on
    `api.lx-software.com`.

#### Done when

`npm test` in `backend/infrastructure`, the Python tests, the admin site's
`npm test`, `python3 scripts/check-contracts.py`, the Redocly lint and the
route comparison pass. A search for `siu-tin-dei`, `evolve-sprouts`,
`fx/v2` and `x-api-key` finds only the old routes that stay and this plan's
note.

### L3. Close the old front door (draft)

Do not merge before both are true:

- The date is 25 Dec 2026 or later. `api.lx-software.com` went live on
  24 Nov 2026. Emails sent before then carry unsubscribe links on the
  `execute-api` hostname, and an unsubscribe link has to work for 30 days.
- The Meta developer console points both callbacks at
  `https://api.lx-software.com/v1/webhooks/meta` and
  `https://api.lx-software.com/v1/webhooks/meta/siutindei`.

Content: `DisableExecuteApiEndpoint` is true when `UseApiCustomDomain` is
true. Remove the four old webhook route keys and their entries in the legacy
table. Remove the `execute-api` origin from the content security policy.
Replace the test at `lxsoftware-stack.test.ts:476`. Delete the plan note.

## 10. `siutindei`

The API stack has 495 resources. CloudFormation allows 500, and
`backend/infrastructure/scripts/assert-existing-db.ts` asserts the exact
number. Each pull request below changes that number and the sentence in
`docs/architecture/aws-assets-map.md`. There is no room to serve a route on
two paths in API Gateway, so the old website paths are kept alive at the
edge.

### S1. Domain parameter swap

The production hostname sits on the construct `ApiSecondaryCustomDomain`,
fed by `ApiSecondaryCustomDomainName`. `ApiCustomDomainName` is empty and
its construct was never created. The swap rewires the parameters. It does
not touch the logical ids, so the domain is not recreated and the DNS target
does not change.

`backend/infrastructure/lib/api-stack.ts`, parameters near 619, constructs
near 3132:

1. Keep the construct ids `ApiSecondaryCustomDomain`,
   `ApiSecondaryCertificate` and `ApiSecondaryBasePathMapping` exactly. Feed
   them from `ApiCustomDomainName` and `ApiCustomDomainCertificateArn`. Put
   them under the condition `UseApiCustomDomain`. Add a comment that the ids
   are historical and must not change.
2. Delete the constructs `ApiCustomDomain`, `ApiCertificate` and
   `ApiBasePathMapping`, the two `ApiSecondary*` parameters and the
   condition `UseApiSecondaryCustomDomain`.
3. The condition `DisableExecuteApiEndpoint` uses `UseApiCustomDomain`.
4. Outputs: `ApiCustomDomainTarget` and `ApiCustomDomainUrl` come from the
   surviving construct. Remove `ApiSecondaryCustomDomainTarget` and
   `ApiSecondaryCustomDomainUrl`.
5. `params/production.json`: `ApiCustomDomainName` is `api.siutindei.com`.
   `ApiCustomDomainCertificateArn` is the placeholder that names the
   existing secret `CDK_PARAM_API_SECONDARY_CUSTOM_DOMAIN_CERTIFICATE_ARN`.
   Use that secret and no other. Remove the two `ApiSecondary*` entries.
   The secret keeps its name, so the owner has nothing to do.
6. `.github/workflows/deploy-backend.yml` and `cdk-diff.yml`: remove
   `ApiCustomDomainName` and `ApiCustomDomainCertificateArn` from
   `pass-empty`. Those lines are inside `# template:set` blocks. Change
   nothing outside the blocks.
7. `scripts/deploy/build_amplify_config.py` near line 47 reads
   `ApiCustomDomainUrl` only.
8. `assert-existing-db.ts`: the count is 493. `DisableExecuteApiEndpoint`
   must mention `UseApiCustomDomain`.
9. The params README, `aws-assets-map.md`, and
   `docs/plans/siutindei-domain-consolidation.md` (mark phase 4 done).
   Search both `siutindei` and `lx-software` for `ApiSecondary`.

Put this in the pull request body: the template diff shows the `DomainName`
property changing its reference, and that is expected. The `cdk-diff` job
builds a change set. It must show no replacement of
`AWS::ApiGateway::DomainName`. If the owner sees a replacement, do not
merge. A replacement would fail and roll back, because the name already
exists, but it should not get that far.

After deploy: the `ApiCustomDomainTarget` output equals the old
`ApiSecondaryCustomDomainTarget` value, and `https://api.siutindei.com`
answers as before.

### S2. Server cutover

Merge at a quiet hour. API Gateway and CloudFront are separate stacks in one
deploy run. Between the two stack updates, a search from the live site that
is not in a cache can fail. Say so in the pull request body.

#### Routes

| Today | After |
| --- | --- |
| `GET /health`, IAM | `GET /health`, open, `{"status": "ok"}` |
| `GET /v1/activities/search` | `GET /v1/public/activities/search` |
| `POST /v1/listing-events` | `POST /v1/public/listing-events` |
| `/v1/partner/*` with `x-partner-key` | The same paths with `Authorization: Bearer` |
| `/v1/admin/*`, `/v1/manager/*`, `/v1/user/*` | No change |

#### Steps

1. Plan note.
2. API stack.
   - Move the two website routes in place. Keep the device attestation
     authorizer, `apiKeyRequired`, the cache key parameters and every method
     setting. Count: plus 2.
   - Partner authorizer near line 2085: identity source
     `method.request.header.Authorization`, cache 300 seconds.
     `assert-existing-db.ts` near line 352 asserts the header and 900.
     Change both assertions.
   - `/health`: authorization `NONE`, a method throttle on the stage. The
     handler returns `{"status": "ok"}` for an HTTP request without opening
     a database connection. The database check stays for a direct
     invocation.
   - Gateway responses near line 2389: `DEFAULT_4XX` and `DEFAULT_5XX` get
     the body template in section 4.5 and the header `x-request-id` from
     `context.requestId`. Add `MISSING_AUTHENTICATION_TOKEN` with status
     404. That is safe only when no IAM method is left, because a missing
     IAM signature gives the same response type. Check that `/health` was
     the last one. Count: plus 1.
   - The count is 496. Update the assertion and the document.
3. WAF. `lib/constructs/api-rate-limit.ts` lines 41, 151 and 209. The
   partner rule keys on the `authorization` header under `/v1/partner/`. Log
   redaction covers `authorization`. Partner requests now send
   `Authorization`, so check the session rule's scope: the two rules must
   not both count one request.
4. Authorizer code. `backend/lambda/authorizers/api_key/handler.py` and
   `backend/src/app/auth/api_key_authorizer.py` read `Authorization` as in
   F1. Update `tests/test_api_key_authorizer.py` and the `test_partner_*`
   tests.
5. Handlers. `x-request-id` on every response. Error bodies gain the members
   in section 4.5 and keep `error`. See `exceptions.py` near 35 and
   `responses.py` near 215.
6. Edge. `backend/infrastructure/lib/public-www-stack.ts`.
   - The behaviours on `/v1/activities/search` and `/v1/listing-events` stay
     and rewrite the path to the new one before the request goes to the
     origin.
   - Add behaviours on `/api/v1/public/activities/search` and
     `/api/v1/public/listing-events` that remove `/api`.
   - All four keep today's cache policy, origin request policy, forwarded
     headers and the `X-Origin-Verify` header.
   - A behaviour takes one viewer-request function. Where the edge-verify
     function is attached, put the rewrite in that function. Keep the
     `addDependency` chain that creates functions one at a time.
7. Mobile app. `apps/siutindei_app/lib/services/api_service.dart` calls
   `/v1/public/activities/search`. `/v1/user/areas` does not change.
   The domain plan says no build has been published.
8. `scripts/ops/board-importer`: `API_BASE` is the origin, and the request
   paths start with `/v1/admin/`.
9. OpenAPI. `git mv docs/api/search.yaml docs/api/public.yaml` and change
   the paths. `partner.yaml` lines 11 and 1586 name the new header. Line 14
   already says 5 minutes. `admin.yaml` documents the open `/health`.
   Update `scripts/check_openapi_routes.py` and regenerate
   `apps/admin_web/src/types/api-admin.generated.ts`.
10. `backend/db/seed/seed_data.sql:296` mentions `x-partner-key`.
    `backend/db/**` is not approved. Leave the file and list the line in
    the pull request body.
11. Docs.

#### Done when

`npm run test:infra`, `scripts/ci/repo-checks.sh`, the Python tests, the
Flutter tests and the OpenAPI checks pass.

### S3. Website on the new paths

1. `apps/public_www`: `search-client.ts` and `listing-events-ingest.ts` call
   `/api/v1/public/activities/search` and `/api/v1/public/listing-events`.
2. `scripts/cloudflare/public_www_edge_policy.json`: the four expressions on
   `http.request.uri.path eq "/v1/activities/search"` match either path.
   Check every other rule in the file for a path. Update
   `tests/test_cloudflare_edge_policy.py`.
3. The pull request body says: apply the policy with
   `scripts/cloudflare/edge_policy.py apply --yes` before promoting this
   site build. Without it the new path has no rate limit.

### S4. Remove the old edge paths (draft)

Do not merge before the S3 site build is promoted to production.

Remove the two old behaviours and their rewrite. The Cloudflare policy
matches the new path only. The owner applies it again. Delete the plan note.

## 11. `evolvesprouts`

The API stack has 483 resources. Every route uses one Lambda integration,
`adminIntegration`. The token routes are 30 resources, 30 `OPTIONS` methods
and 48 methods. E1 folds them into one greedy route. That frees about 100
resources, which is the room E1 needs to serve the website routes on old and
new paths together. Expected counts: about 380 after the fold, about 470
after E1, about 375 after E3. Add a stack test that prints the count and
fails over 495.

### E1. Server

Token holders change on the day E1 deploys: new path, new header. Nothing
else breaks, because every other old path stays.

#### Routes

| Today | After E1 | After E3 |
| --- | --- | --- |
| Domain mapping `prod` | `prod` and a root mapping | Root only |
| `GET /health`, IAM | Open, `{"status": "ok"}` | |
| `/v1/public/<token route>`, `x-api-token`, 48 methods | `ANY /v1/partner/{proxy+}`, `Authorization: Bearer`. The old routes are removed | |
| `GET /v1/calendar/public` | Also `GET /v1/public/calendar` | New only |
| `GET /v1/assets/public` | Also `GET /v1/public/assets` | New only |
| `GET /v1/assets/public/{id}/download` | Also `GET /v1/public/assets/{id}/download` | New only |
| Every other website route `/v1/<path>` | Also `/v1/public/<path>` | New only |
| `GET,POST /v1/<provider>/webhook` | Also `GET,POST /v1/webhooks/<provider>` | New only |
| `/v1/admin/*`, `/v1/user/*` | No change | |

The other website routes are: `calendar/availability`, `reservations`,
`reservations/payment-intent`, `contact-us`, `forms/{form_slug}/answers`,
`forms/{form_slug}/contact-context`, `polls/{poll_slug}/answers`,
`polls/{poll_slug}/control`,
`polls/{poll_slug}/questions/{question_id}/results`, `discounts/validate`,
`assets/free`, `assets/free/request`, `assets/share/{token}`,
`assets/email-download/{token}`. The providers are `mailchimp`, `whatsapp`
and `meta`.

No token route has the name of a website route, so nothing collides under
`/v1/public/`.

#### Steps

1. Plan note.
2. API stack. `backend/infrastructure/lib/api-stack.ts`, routes near 3386.
   - Root mapping beside `prod`, near line 3962. API Gateway accepts an
     empty mapping and a named one on one domain. If the base path mapping
     resource refuses, use `AWS::ApiGatewayV2::ApiMapping`.
   - Token authorizer near line 2947: identity source
     `method.request.header.Authorization`, cache 300 seconds. Replace the
     token route tree with `partner` and `{proxy+}`, method `ANY`, that
     authorizer. Check that the authorizer's policy allows every method
     under `/v1/partner/`.
   - New website routes under `/v1/public/`, each with the same settings as
     its old route: `apiKeyRequired`, and the device attestation authorizer
     on the two `assets` routes that have it. List them one by one. No
     greedy route here.
   - New webhook routes. Whatever is attached to the old webhook methods
     (alarms, metrics, throttles) is attached to the new ones too.
   - `/health` and the gateway responses as in S2 step 2.
   - Stack tests: the count, the partner and public authorizer rule from
     section 4.2, both mappings present.
     `assertApiCustomDomainKeepsProdPath` near line 1021 of
     `api-stack.test.ts` stays for now.
3. Edge. `cloudfront-www-proxy-functions.ts`, `public-www-stack.ts` near
   598, and the training stack.
   - Add an allow-list function for `/api/v1/public/...` that removes
     `/api`, and a behaviour `api/*` on the public site and the training
     site. It mirrors `WWW_PROXY_ALLOWLIST_FUNCTION` route for route.
   - The `www/*` behaviours and their function stay unchanged.
   - `PublicWwwApiBaseUrl` has the pattern `^https://[^/]+/[^/]+/?$`. Relax
     it to accept an origin with no path, in every parameter that has it.
     With no path the CloudFront origin path is omitted.
   - Update `cloudfront-www-proxy-functions.test.ts` and the stack tests.
4. Authorizer code. `backend/lambda/authorizers/api_token/handler.py` and
   `backend/src/app/auth/api_token_authorizer.py` read `Authorization` as in
   F1. Update `tests/test_api_token_authorizer.py`.
5. Router. `backend/src/app/api/admin.py`, `_ROUTES` near line 110.
   - Token routes move to `/v1/partner/...`. A static segment wins over a
     parameter, as in API Gateway.
   - Each website and webhook route is listed on both paths.
   - Token handlers refuse a request with no token authorizer context. Check
     `backend/src/app/api/public/token_auth.py` and add the test.
   - Move the package `backend/src/app/api/public/` to `api/partner/` and
     the tests `tests/api/test_public_*.py` to match, as one commit that
     only moves and renames. `public` now means the open audience.
   - The `/prod` strip in `admin_request.py` stays.
6. Handlers. `x-request-id` and the error members, keeping `error`,
   `detail` and `field`. See `exceptions.py` near line 35.
7. OpenAPI. `docs/api/public.yaml` holds the open routes on their new
   paths. The token routes move to a new `partner.yaml`. The webhooks go to
   a new `webhooks.yaml`. Every `servers` entry is
   `https://api.evolvesprouts.com`. `admin.yaml` near line 1160 names the
   new header. Update `scripts/check-cdk-admin-api-routes.mjs` for the
   greedy partner route and the new paths.
8. Docs. Every `x-api-token` reference.
   `docs/architecture/infrastructure-map.md` says the API hostname is
   proxied by Cloudflare. It is not. Correct it.

#### Done when

`npm run test:infra`, `npm run lint` and `npm run typecheck` in
`backend/infrastructure`, the Python tests, `check-cdk-admin-api-routes.mjs`
and the Redocly lint pass.

### E2. Clients

1. Public site. `apps/public_www/src/lib/crm-api-client.ts` and
   `api-paths.ts`: the prefix is `/api` and the paths are `/v1/public/...`.
   About 31 files hold a path. Simplify the base URL handling that exists
   only for `/www`.
2. Training site. `training-api-config.ts`, `forms-api.ts`, `polls-api.ts`.
   `.github/workflows/deploy-training.yml` sets
   `NEXT_PUBLIC_API_BASE_URL: /www` near line 62. It becomes `/api`, and the
   comment above it follows. `actions` has no template for this workflow.
3. Every other holder of `/www`: build scripts,
   `scripts/cloudflare/**`, the staging Worker, smoke tests. Search for
   `/www/` and `'/www'`.
4. Admin site. The paths already start with `/v1/admin/`. Check that
   `config.ts` and `api-admin-client.ts` work with a base URL that has no
   path. Regenerate `admin-api.generated.ts`.
5. Media distribution, in `api-stack.ts` near line 3811. The viewer paths
   `/v1/assets/share/*` and `/v1/assets/email-download/*` on the media
   hostname stay for good, because they are in sent email. `share_links.py`
   keeps building them. The distribution rewrites them to
   `/v1/public/assets/share/{token}` and
   `/v1/public/assets/email-download/{token}`, and its origin path loses
   `/prod`. Keep the existing dependency between the stage and this
   distribution.
6. Smoke tests use the new paths.

After E2 deploys, the owner promotes the public site and the training site.

### E3. Remove the old paths (draft)

Do not merge before all four are true:

- The E2 builds of the public site and the training site are in production.
- The repository variable `NEXT_PUBLIC_API_BASE_URL` is
  `https://api.evolvesprouts.com`, and Deploy Backend and Deploy Admin Web
  have run since. `gh variable list` shows the value.
- Mailchimp, Meta and WhatsApp call `/v1/webhooks/<provider>` on
  `https://api.evolvesprouts.com`.
- Every token holder uses `/v1/partner/` with no `/prod`.

Content:

1. Remove the old website routes and the old webhook routes from API
   Gateway and from `_ROUTES`, with the `/www/v1/...` aliases near lines
   127 to 377.
2. Remove the `prod` mapping and the `/prod` strip in `admin_request.py`
   near line 106. Outputs lose `/prod`. Replace
   `assertApiCustomDomainKeepsProdPath` with a test that the only mapping is
   the root.
3. Remove the `www/*` behaviours, `WWW_PROXY_ALLOWLIST_FUNCTION` and their
   tests.
4. Docs, including `docs/plans/api-domain-staging-gate.md`. Delete the plan
   note.

## 12. Owner steps

The agent cannot do these.

| When | Step |
| --- | --- |
| Before F1, L2, S2, E1 | Tell every token holder the new path and header. They change on the deploy day |
| Before promoting the S3 site | `scripts/cloudflare/edge_policy.py apply --yes` in `siutindei` |
| After S4 deploys | Apply the Cloudflare policy again |
| After E1 deploys | Set `NEXT_PUBLIC_API_BASE_URL` to `https://api.evolvesprouts.com`. Run Deploy Backend, then Deploy Admin Web |
| After E1 deploys | Change the Mailchimp, Meta and WhatsApp callbacks to `https://api.evolvesprouts.com/v1/webhooks/<provider>`. Meta and WhatsApp repeat their verification call. Watch the Mailchimp inactivity alarm |
| After E2 deploys | Promote the public site and the training site |
| After L2 deploys | Change both Meta callbacks to `https://api.lx-software.com/v1/webhooks/...` |
| 25 Dec 2026 or later | Merge L3 |
| After A2 merges | Start the pin bump in each product |

## 13. Checks after each deploy

Run these from any machine. None needs a credential.

| After | Check | Expected |
| --- | --- | --- |
| F1 | `GET https://api.findingalpha.app/health` | 200, `{"status": "ok"}`, an `x-request-id` header |
| F1 | `GET https://api.findingalpha.app/v1/admin/me` with no token | 401 |
| F1 | `GET https://api.findingalpha.app/me` | 404 |
| F1 | The admin site loads and saves a setting | Works. The request body in the browser's network tab is snake_case |
| L1 | `OPTIONS` preflight for `PATCH` from the admin origin | `Access-Control-Allow-Methods` includes `PATCH` |
| L2 | `GET https://api.lx-software.com/v1/admin/me` with no token | 401 |
| L2 | `GET https://api.lx-software.com/public/newsletter/confirm/x` | The same page as before, not a gateway 404 |
| S1 | The stack output `ApiCustomDomainTarget` | Equal to the old `ApiSecondaryCustomDomainTarget` value |
| S1 | The admin site and a search on the live site | Work as before |
| S2 | `GET https://api.siutindei.com/health` | 200, `{"status": "ok"}` |
| S2 | A search on the live site | Works |
| S2 | `GET https://api.siutindei.com/nothing` | 404 |
| E1 | `GET https://api.evolvesprouts.com/health` and `/prod/health` | 200 on both |
| E1 | `GET https://api.evolvesprouts.com/v1/webhooks/mailchimp` | The same body as `/prod/v1/mailchimp/webhook` |
| E1 | `GET https://api.evolvesprouts.com/v1/partner/contacts` with no token | 401 |
| E2 | A booking and a contact form on the staging site | Work |
| E2 | A share link from an old email | Still downloads |
| E3 | `GET https://api.evolvesprouts.com/prod/health` | 403 or 404 |

One effect to expect on the two REST APIs. CloudFormation creates the new
API Gateway deployment before it deletes removed methods. A removed route
can therefore keep answering until the next change to the API. That is
harmless after S2 and E1, because the old routes keep their authorizers.
After E3, check that an old path is gone. If it still answers, any later API
change removes it, or the owner creates a deployment by hand.

## 14. Rollback

Every pull request is reverted by reverting its merge commit and deploying.
The points below are the exceptions and the order.

- F1, L2: one revert restores paths, header and field names together. Token
  holders go back to the old header.
- S1: the revert restores the `ApiSecondary*` parameters. The domain is not
  touched in either direction.
- S2: revert and deploy. The edge and the API move back together, with the
  same short gap.
- E1: token holders go back to `/v1/public/` and `x-api-token`. Everything
  else in E1 is additive.
- E3: before reverting, set `NEXT_PUBLIC_API_BASE_URL` back only if clients
  need `/prod` again. The root mapping stays in every case.
- L3: the revert re-enables `execute-api`.
- A callback changed in a provider's dashboard is changed back by hand.

## 15. Facts this plan relies on

Checked on 26 Nov 2026. Verify the ones marked "verify" before relying on
them.

| Repository | Commit read | Fact |
| --- | --- | --- |
| `actions` | `b2200fd` | `openapi` capability probe is `docs/api/*.yaml`. The `lint-openapi` block is at `templates/workflows/lint.yml` near line 200 |
| `findingalpha` | `b2907d5` | HTTP API. `api.findingalpha.app` exists. The admin site uses the `execute-api` URL through `AdminApiBaseUrl`. No email and no webhook |
| `lx-software` | `ad6c47d` | HTTP API, 220 route keys. `api.lx-software.com` went live on 24 Nov 2026. `PublicApiBaseUrl`, when set, wins over the custom domain for email links: verify it is not set to the `execute-api` URL |
| `lx-software` | | No other repository calls `api.lx-software.com`. No site posts to `/public/newsletter/subscribe` |
| `siutindei` | `ed2a763` | REST API, 495 resources, asserted. `api.siutindei.com` is on the `ApiSecondaryCustomDomain` construct. No mobile build is published: verify with the owner's note in the domain plan |
| `siutindei` | | The search route uses its own Lambda and a method cache |
| `evolvesprouts` | `44b6c1e` | REST API, 483 resources (synthesised for this plan, not asserted in the repository). One integration for every route. `execute-api` is already disabled. `api.evolvesprouts.com` is not proxied by Cloudflare |
| `evolvesprouts` | | The Flutter app is a placeholder with no API call. The only API URL variable set is `NEXT_PUBLIC_API_BASE_URL`, and it ends in `/prod` |
| all | | A REST Lambda authorizer with a cache refuses a request that lacks its identity header before the authorizer runs. So one authorizer cannot accept an old header or a new one, and the header changes in one step |

Corrections to the analysis in the canvas:

- The siutindei swap does not recreate the domain. It rewires parameters
  onto the construct that already holds the hostname.
- `/me` in `lx-software` and `findingalpha` requires the `admin` group. It
  goes to `/v1/admin/me`, not `/v1/user/me`.
- There is no `/health/ready`. `siutindei` has no room for another route.
- `api.evolvesprouts.com` is DNS-only today.

## 16. Open questions

None block the run. The owner may answer them on the pull requests.

- `siutindei` S2 has a short gap for uncached searches. Freeing about ten
  resources elsewhere in that stack would allow old and new paths together
  and remove the gap. Nothing was found that is safe to remove without the
  owner.
- The `evolvesprouts` partner routes become one greedy route. API Gateway
  no longer rejects an unknown partner path by itself. The router does.
  `siutindei` already works this way.
- The secret `CDK_PARAM_API_SECONDARY_CUSTOM_DOMAIN_CERTIFICATE_ARN` keeps
  its old name after S1. Renaming it is an owner step with no effect on
  callers.
