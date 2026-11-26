# Review: API standard pull requests, second round

**Status**: Open. Work through it, then delete this file with the plan note.
**Zone**: yellow (a plan note). The fixes inherit the zones and the approval
in section 3 of `api-standard.md`.

Reviewed on 26 Nov 2026 between 15:55 and 16:15 Hong Kong time, against the
plan in `api-standard.md`. CI was green on every pull request. None of the
blockers below is visible to CI: `cdk-diff` builds no change set on a pull
request, and the tests that exist check the wrong thing.

The first round's fixes are in place: each product accepts the old token
header for one deploy, `execute-api` stays open in the cutover pull
requests, and `GET /v1/partner` stays. One of those fixes introduced
blocker B4.

## Heads reviewed

| Pull request | Head |
| --- | --- |
| [actions#99](https://github.com/lx-software-ltd/actions/pull/99) A1 | `e9694f3` |
| [actions#100](https://github.com/lx-software-ltd/actions/pull/100) A2 | `0b7b662` |
| [findingalpha#119](https://github.com/lx-software-ltd/findingalpha/pull/119) F1 | `51b995b` |
| [findingalpha#120](https://github.com/lx-software-ltd/findingalpha/pull/120) F2, draft | `4b879ef` |
| [lx-software#714](https://github.com/lx-software-ltd/lx-software/pull/714) L1 | `46a1954` |
| [lx-software#715](https://github.com/lx-software-ltd/lx-software/pull/715) L2 | `227a5b5` |
| [lx-software#717](https://github.com/lx-software-ltd/lx-software/pull/717) L3, draft | `37d8657` |
| [siutindei#982](https://github.com/lx-software-ltd/siutindei/pull/982) S1 | `820cc2e` |
| [siutindei#983](https://github.com/lx-software-ltd/siutindei/pull/983) S2 | `dd84020` |
| [siutindei#985](https://github.com/lx-software-ltd/siutindei/pull/985) S3 | `2d85eff` |
| [siutindei#986](https://github.com/lx-software-ltd/siutindei/pull/986) S4, draft | `9f9f193` |
| [evolvesprouts#2335](https://github.com/lx-software-ltd/evolvesprouts/pull/2335) E1 | `4212b8c` |
| [evolvesprouts#2336](https://github.com/lx-software-ltd/evolvesprouts/pull/2336) E2 | `5b05131` |
| [evolvesprouts#2338](https://github.com/lx-software-ltd/evolvesprouts/pull/2338) E3, draft | `d2cb9ad` |

Line numbers are at those heads.

## Verdict

| Pull request | Verdict |
| --- | --- |
| L1 | Ready to merge |
| A1 | Ready after one wording fix (A1-1) |
| F1, F2 | Hold: B3 |
| L2, L3 | Hold: B3, B4, B5 |
| S1 | Hold: B7 |
| S2, S4 | Hold: B6 |
| S3 | Hold behind S2 |
| E1, E2, E3 | Hold: B1, B2 |
| A2 | Hold: should-fix items |

## Blockers

### B1. evolvesprouts E1: the admin grant route rename fails the stack update

`backend/infrastructure/lib/api-stack.ts` near 3668 renames
`{grantId}` to `{grant_id}` and deletes the comment that warned against
exactly this. The logical id changes, CloudFormation creates the new
resource before it deletes the old one, and API Gateway refuses a second
variable segment under `/grants`. The update fails and rolls back. The plan
also says `/v1/admin/*` does not change.

Fix: restore `{grantId}` and the comment.

### B2. evolvesprouts E1, E2, E3: most new `/v1/public/...` routes return 404

API Gateway has the new routes and `_with_public_aliases` in
`backend/src/app/api/admin.py` near 348 sends them to the old handlers, but
five handlers parse the old prefixes themselves:

- `public_forms.py` near 27 and `public_polls.py` near 39 know only
  `/v1/forms/`, `/v1/polls/` and the `/www` forms.
- `public_free_assets.py` near 43 knows only `/v1/assets/free`.
- `public_assets.py` near 36 requires `assets/public`.
- `share_assets.py` near 34 and 50 requires three segments starting
  `assets/share` or `assets/email-download`.

Broken in E1: every forms and polls route, `GET /v1/public/assets/free`,
`GET /v1/public/assets`, `/v1/public/assets/{id}/download`, and the share
and email-download routes. Calendar, availability, reservations,
payment-intent, contact-us, discounts and free/request work.

E2 makes it live: the media distribution rewrites emailed share links to
the broken paths, and both sites move to them. E3 fixes forms, polls and
free assets, but not `public_assets.py` or `share_assets.py`.

Fix, in E1: map `/v1/public/<x>` to the path the handler expects before
calling it, in `_match_handler`, or teach the five handlers both prefixes.
Add a router test that sends every path in `docs/api/public.yaml` and
every path the media rewrite produces, and fails on a 404 from the handler.

### B3. findingalpha F1, lx-software L2, and their drafts: the admin-web template names a condition it does not have

- findingalpha: `backend/infrastructure/bin/app.ts:52` passes
  `backend.httpApiEndpoint`, which `lib/http-api.ts` near 175 builds with
  `Fn::If` on `UseApiCustomDomain`.
- lx-software: `bin/app.ts:78` passes `cspApiConnectOrigin`, which
  `admin-http-api.ts` near 187 builds the same way. L3 keeps the pattern
  near 192.

CDK turns the references inside into imports and copies the `Fn::If` as
is. The admin-web templates do not define `UseApiCustomDomain`, so
CloudFormation rejects them. `cdk synth` already warns (E1028). In
findingalpha, synth also creates an export whose value is the
`ApiCustomDomainName` parameter. CloudFormation refuses an empty export, so
the backend stack probably fails too while that parameter is empty.

siutindei and evolvesprouts do not have this problem.

Fix:

1. Pass `cdk.Fn.importValue("<stack>-AdminApiBaseUrl")`. That output already
   resolves the condition inside the API stack. lx-software needs the
   two-origin form until L3, so add a second output for it.
2. `adminWeb.addDependency(<api stack>)`.
3. findingalpha: keep `backend.exportValue(httpApi.apiEndpoint)` for one
   release. The deployed admin-web stack still imports that export, and
   dropping it fails the backend deploy.
4. Add a stack test in both products: every condition named by `Fn::If` in
   a template exists in that template's `Conditions`.

### B4. lx-software L2: the token check reuses one caller's approval for the whole IP address

`backend/infrastructure/lib/admin-api-authorizers.ts` near 100 sets
`identitySource: ["$context.identity.sourceIp"]` with a 60 second cache. The
cache key is the IP address alone. For 60 seconds after one valid token is
accepted, any request from that address, with no token or another token,
reuses that token's `keyId`, scopes and write flag. A denial also blocks
valid callers from that address for 60 seconds. The stack test near
`lxsoftware-stack.test.ts:631` asserts the 60 seconds, and the L2 plan note
`docs/plans/2026-11-26-board-alias-wire-cache.md` says "TTL stays 60".

The other three products set the cache to 0 for the same overlap. L3 is
correct: `Authorization` plus source IP, 60 seconds.

Fix: `resultsCacheTtl: cdk.Duration.seconds(0)` in L2, assert
`AuthorizerResultTtlInSeconds: 0`, and correct the plan note.

### B5. lx-software L2: catalog import loses `/v1`

L2 sets `SiutindeiAdminApiBaseUrl` to `https://api.siutindei.com`, but
`backend/lambda/admin/board_catalog_import.py:901` and `:924` still join
`admin/imports/presign` and `admin/imports`. Both requests get 404. The
tests only check `url.endswith(...)`.

Fix: join `v1/admin/imports/presign` and `v1/admin/imports`, and assert the
full URL.

### B6. siutindei S2 and S4: `backend/db/seed/seed_data.sql` is edited

S2 changes lines 296 to 298 and S4 changes the file again, while the S4
body says the seed data is unchanged. `backend/db/**` is not approved.

Fix: revert the file in both, and list the line in both bodies.

### B7. siutindei S1: the change set the merge condition needs was never built

The S1 body says the `cdk-diff` job builds a change set. It did not: on a
pull request that job only warns that `AWS_DIFF_ROLE_NAME` is unset.

The template comparison is clean. The domain is `ApiSecondaryCustomDomain…`
and the mapping `ApiSecondaryBasePathMapping…` on `main` and on S1. The
domain's only changes are the `DomainName` and `RegionalCertificateArn`
references and its condition, and both references resolve to the same
values. No replacement is expected.

Fix: correct the body. Before merging, the owner builds a change set for
the branch by hand, or sets `AWS_DIFF_ROLE_NAME`, and confirms no
replacement of `AWS::ApiGateway::DomainName`.

## Should fix

### actions

- **A1-1.** `docs/api-contract.md:50` lets the old header stay "once logs
  show no legacy use over the window the owner sets". That is a notice
  period. `docs/decisions.md:75` says one deploy. Use the decisions
  wording in both, and say the removal is the next pull request in each
  product.
- **A1-2.** `decisions.md:75` says "an issued token keeps working across
  that day". Not true where the path also moves (findingalpha, evolvesprouts).
  Say the token validates under either header for one deploy, and the
  holder changes the path on the deploy day.
- **A1-3.** `api-contract.md:50` says "the cache key includes both headers,
  or neither". Both is impossible, and neither with a cache is B4. Write:
  the cache is off during the overlap and returns when the old header goes.
- **A2-1.** The rollout order in the PR body and `api-contract/README.md:80`
  fails conformance. The step stays out of the template until A2 is on
  `main`, which is right, but then: a second actions pull request adds the
  step pinned at A2's merge SHA and deletes
  `test_lint_template_omits_the_action_until_it_is_on_main`; each product
  bumps to that SHA and adds the step in one pull request, and only after
  its own L2, S2 or E1 is on `main`. Write that order down.
- **A2-2.** No pull request deletes a plan note. The note is
  `docs/plans/api-standard.md` on #98, which A2 does not build on. Either
  stack A1 on #98 and delete the note and this file in A2, or close #98
  unmerged and say so in the A2 body.
- **A2-3.** `check.py` near 112 skips every line under a path key, so a
  `servers:` under a path or operation is never checked. Fail on it.
- **A2-4.** A quoted `"paths":` or `'paths':` is never opened and the file
  passes. A file with no `paths` block passes. Fail on both.
- **A2-5.** The segment rule is a denylist. `/v1/public/a?x=1`, `//`, a
  trailing `/`, `items:search`, `a#b`, `{a__b_}` pass. Use
  `^[a-z0-9]+(-[a-z0-9]+)*$` for literal segments,
  `^[a-z][a-z0-9]*(_[a-z0-9]+)*$` for parameters, and reject empty
  segments.
- **A2-6.** `admin-prefixes` is not validated: `/v1/admin` without a slash
  admits `/v1/adminevil`. Require `^/v1/[a-z0-9-]+/$`. Require `origin` to
  match `^https://[a-z0-9.-]+$`.

### findingalpha

- **F1-1.** `contracts/wire-format.json:17` excludes the backtest routes, so
  their bodies and their error bodies stay camelCase (`requestId`). A real
  backtest output converts cleanly. `docs/api/admin.yaml` near 250 already
  claims snake_case. Set `excludedRoutes` to `[]` and add a raw wire test.
- **F1-2.** The data-keyed map guard in `test_wire_format.py` near 40
  checks only `shareSources`, and the round-trip helper cannot catch a
  snake_case data key missing from `mapFields`. Assert all nine maps are in
  the contract: `done`, `sectors`, `shareSources`, `flows`, `stocks`,
  `shareFlows`, `groups`, `factors`, `z`. Add raw wire tests for
  universe, screens and owner tasks.
- **F1-3.** `apps/admin_web/src/lib/apiAdminClient.ts:104` builds
  `new Response(body, {status})`. That throws for 204, 205 and 304. Pass
  `null` for those or for an empty body. Add `adminFetch` tests with a
  stubbed `fetch`.
- **F1-4.** `scripts/check_openapi_routes.py` never runs in CI. Call it
  from `scripts/ci/test-python.sh` or a unit test.
- **F2-1.** Move the preconditions to the first lines of the body as a "Do
  not merge before" list. Drop the precondition written into the API's
  `Description`.

### lx-software

- **L2-1.** `evolvesprouts_finance.py:272` changes a stored ledger
  description from `[evolve-sprouts]` to `[evolvesprouts]`. The next sync
  rewrites every refund line. Revert it and the mock fixture near
  `fixtures.ts:177`.
- **L2-2.** `bySubscription` and `byOnboardingStep` in `board_progress.py`
  are keyed by status names such as `past_due`. Add both to `mapFields`
  with depth 1.
- **L2-3.** `scripts/check-contracts.py` near 44 skips the byte check
  against findingalpha when no sibling checkout exists, which is always in
  CI, and hardcodes an agent path. Print the skip, or fetch the files from
  findingalpha at a pinned commit.
- **L3-1.** `scripts/check_admin_spa_config.py` is not run by anything, and
  `scripts/deploy/check-admin-spa-settings.sh` already does the job. Wire it
  in or drop it. If kept, see X-1.

### siutindei

- **S2-1.** The partner WAF rule in `lib/constructs/api-rate-limit.ts` near
  149 now keys on `authorization`. A rate rule does not count requests
  without its key header, so callers on `x-partner-key` are not limited,
  and with the cache off each of their requests runs the authorizer. Add a
  second rule keyed on `x-partner-key` for S2, with its metric in the
  alarm. S4 removes it.
- **S2-2.** `gatewayResponseHeaders` near `api-stack.ts:2379` uses keys
  that start `method.response.header.`. CDK adds that prefix itself, so the
  headers never reach clients. The CORS headers on gateway errors have had
  the same fault since before this work. `'$context.requestId'` is also a
  quoted literal. Use bare header names and `context.requestId`. If API
  Gateway refuses a `context` value there, drop `x-request-id` from gateway
  errors; the body carries `request_id`. The stack test near the CORS
  assertion uses `endsWith` and passes the bad keys; tighten it.
- **S2-3.** The partner authorizer clears `IdentitySource` with a deletion
  override. If the update does not clear the live `x-partner-key` source,
  every Bearer-only request gets 401 before the Lambda. Give the S2
  authorizer a new construct id so CloudFormation creates a fresh one, or
  add `aws apigateway get-authorizer` and one probe per header to the
  post-deploy checks.
- **S2-4.** The open `/health` raises Checkov alert 239 (`CKV_AWS_59`).
  Suppress it on that one method with a reason.
- **S2-5.** Add the stack test from plan section 4.2: every
  `/v1/partner/` method has the partner authorizer and no `/v1/public/`
  method has it. Add a test that the `/health` HTTP path opens no database
  connection.
- **S2-6.** The rollback paragraph says reverting the API alone restores
  the old paths. It does not; CloudFront would rewrite to paths that no
  longer exist. Reverting S2 reverts both.
- **S3-1.** `scripts/deploy/deploy-public-www.sh:382` invalidates only
  `/v1/activities/search*`. Add `/api/v1/public*` in S3, not S4.
- **S3-2.** The new Cloudflare `check` reads a local file, not the zone, and
  matches a substring. Match the exact expression, read stdin only with
  `--policy -`, and tell the owner to run `edge_policy.py plan` after
  `apply` and expect no difference.
- **S4-1.** `scripts/check_public_www_bundle.py` near 76 reads only the
  scripts on the root page. The search client is in code-split chunks, so
  the check can pass while the old path is live. Scan the search pages and
  the chunks the build manifest lists. See also X-1.

### evolvesprouts

- **E1-1.** `api-stack.ts` near 3613 adds `GET /v1/admin/health` and moves
  the database check behind it. Plan section 4.6: no second health route;
  the deep check is a direct invocation. Drop the route and run
  `check_health()` for an event with no `httpMethod`.
- **E1-2.** The gateway error template near 3296 has no `message` member.
  Plan section 4.5 keeps it. Add `"message": $context.error.messageString`.
- **E1-3.** `ANY /v1/public/{proxy+}` near 3818 carries the token
  authorizer, so every unknown `/v1/public/` path gets 403. Add the section
  4.2 stack test, with an exemption for this one alias in E1 and none in
  E3.
- **E1-4.** A request with no token gets 403 from a `Deny`. The plan's
  post-deploy check and `partner.yaml` say 401. Raise `Unauthorized` when no
  token is presented and re-raise it before the catch-all, or change both
  documents.
- **E1-5.** `exceptions.py:36` copies the message into `detail`, and
  `apps/admin_web/src/lib/api-admin-client.ts` near 52 renders
  `error (detail)`, so admin errors read "X (X)". Skip `detail` when it
  equals `error`.
- **E3-1.** The "Do not merge before" list names `NEXT_PUBLIC_API_BASE_URL`
  only. `vars.PUBLIC_WWW_API_BASE_URL`,
  `vars.PUBLIC_WWW_MEDIA_REQUEST_API_BASE_URL` and
  `vars.NEXT_PUBLIC_WWW_API_BASE_URL` can override it. If a backend one
  still ends in `/prod` after E3, the whole site API fails. List all three,
  or make the parameters reject a path in E3.
- **E3-2.** `scripts/check_api_cutover_preconditions.py` near 100 ignores
  the bundle's status, so a 404 passes, and a `ValueError` from
  `_https_url` ends in a traceback. See also X-1.

### Across products

- **X-1.** The three live-check scripts (L3, S4, E3) check the scheme before
  `urlopen`, but `urlopen` follows redirects, including https to http. The
  Semgrep alerts are cleared by suppression, not by closing this. Use an
  opener whose redirect handler refuses a non-https target, cap the bytes
  read, and in S4 fetch only from the origin's host.

## Nits

- L1: `_problem_field`'s `setdefault` branch does nothing; HTML and PDF
  responses carry no `x-request-id`.
- L2: `/aws/usage.pdf` remains in `aws_billing.py:6` and `:348` and in
  `docs/deployment/admin-website.md` near 843; `params/README.md:57` says
  `/public/*`.
- F1: `wireFormat.ts:70` reads inherited keys, so `constructor` converts
  differently from Python; use `Object.hasOwn`. `adminFetch` passes no
  route to the codec. `docs/architecture/security.md:69` says
  `GET /api-keys`. The authorizer catches `ClientError` only; a
  `BotoCoreError` gives 500. The plan note is deleted in F1, not in F2.
- S2: gateway errors for 429, invalid key, WAF block and not found get the
  title "Bad Request".
- E1: each of the three OpenAPI files carries all 116 component schemas,
  which is most of the +11,851 lines. The `/www` function changed only in
  whitespace, which still updates it. `API_TOKEN_HEADER` in `api_keys.py`
  is unused. The package-move commit `a1142063` is not a pure move and does
  not import on its own.
- E2: the `/prod/` branch in the media rewrite never runs; no behaviour
  matches `prod/v1/assets/...`.
- E3: `X-Api-Token` is still in the CORS headers near 3138 and 3283; docs
  still describe `/www/*`; the body says 386 resources, synth gives 389.
- A2: unclear messages for single-quoted path keys, `x-` keys under
  `paths`, comments after `paths:` or a URL, and a schema property named
  `paths`; `{proxy+}` passes in `webhooks.yaml`; a duplicate key in one file
  is reported as two files; a stale legacy entry is not reported; a unit
  test runs `git fetch`; the CI fail job runs one failing tree; the
  926-line siutindei fixture could be a small purpose-built one.

## Verified correct

- lx-software: all 181 original routes map onto their new names with the
  same methods, auth kind and throttle. L2 has 234 route keys, L3 225.
  `path_class`, `path_allowed`, `write_blocked` and redaction receive the
  path shape they expect, and the old board path is converted before them.
  Owner-only writes return 403 on new and old board paths.
- The wire codec passes the shared cases in Python and Vitest, and its three
  files are byte-identical in findingalpha and lx-software. It runs after
  redaction, skips SQS, internal events, base64 and non-JSON bodies, and the
  admin mock branch.
- findingalpha: the authorizer parses both headers correctly, the cache is
  0 with source IP as the only identity source, the old root and `/public`
  paths return 404, and `lint.yml` matches the actions template.
- siutindei: S1 keeps the domain and mapping logical ids. The moved website
  methods are identical apart from their resource. The CloudFront functions,
  run in Node, rewrite both old paths, strip `/api`, and keep the query
  string. The Cloudflare expressions cover both paths. S4 restores
  `Authorization` with a 300 second cache.
- evolvesprouts: E1 keeps the domain, the `prod` mapping, the API, the stage
  and the authorizers on their logical ids and adds one root mapping. Both
  token headers reach the authorizer. The two edge allow-lists come from one
  table. E3 restores `Authorization` with a 300 second cache.
- Resource counts: siutindei 493 after S1, 496 after S2. evolvesprouts 483
  on `main`, 475 after E1, 476 after E2, 389 after E3.
- The A2 checker gives the expected result on every product branch.
- No account id, API id, certificate ARN, `execute-api` hostname or
  CloudFront hostname was added in any pull request.

## Not verified

No change set or deploy was run. Three things are therefore unverified
against AWS:

- that removing a REST authorizer's identity source takes effect on update
  (S2-3, and the same pattern in E1);
- that API Gateway accepts the corrected gateway header mapping (S2-2);
- that API Gateway accepts an empty base path mapping beside `prod` (E1).

Not run locally: Redocly in every product, the Flutter and Playwright
suites, and the full Python suites of siutindei and evolvesprouts. CI ran
those.
