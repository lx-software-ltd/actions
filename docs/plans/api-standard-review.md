# Review: API standard pull requests, third round

**Status**: Open. Work through it, then delete this file with the plan note.
**Zone**: yellow (a plan note). The fixes inherit the zones and the approval
in section 3 of `api-standard.md`.

Reviewed on 26 Nov 2026 between 16:56 and 17:10 Hong Kong time, against the
plan in `api-standard.md`. The second round's items are listed at the end
with their status. Most are fixed. This round found new blockers in the
fixes themselves.

## Heads reviewed

| Pull request | Head | CI |
| --- | --- | --- |
| [actions#99](https://github.com/lx-software-ltd/actions/pull/99) A1 | `d3b1b61` | Green |
| [actions#100](https://github.com/lx-software-ltd/actions/pull/100) A2 | `80cb52e` | Green |
| [findingalpha#119](https://github.com/lx-software-ltd/findingalpha/pull/119) F1 | `6408c95` | Green |
| [findingalpha#120](https://github.com/lx-software-ltd/findingalpha/pull/120) F2, draft | `69c43a5` | Green |
| [lx-software#714](https://github.com/lx-software-ltd/lx-software/pull/714) L1 | `d4b106e` | Green |
| [lx-software#715](https://github.com/lx-software-ltd/lx-software/pull/715) L2 | `e46ff79` | Green |
| [lx-software#717](https://github.com/lx-software-ltd/lx-software/pull/717) L3, draft | `4c9010c` | Green |
| [siutindei#982](https://github.com/lx-software-ltd/siutindei/pull/982) S1 | `820cc2e` | Green |
| [siutindei#983](https://github.com/lx-software-ltd/siutindei/pull/983) S2 | `bcaa500` | Green |
| [siutindei#985](https://github.com/lx-software-ltd/siutindei/pull/985) S3 | `cda8322` | Green |
| [siutindei#986](https://github.com/lx-software-ltd/siutindei/pull/986) S4, draft | `b9da035` | Green |
| [evolvesprouts#2335](https://github.com/lx-software-ltd/evolvesprouts/pull/2335) E1 | `33e2474` | Green |
| [evolvesprouts#2336](https://github.com/lx-software-ltd/evolvesprouts/pull/2336) E2 | `008606d` | Red: `Build Android` could not reach the Gradle plugin repository. Unrelated. Rerun it |
| [evolvesprouts#2338](https://github.com/lx-software-ltd/evolvesprouts/pull/2338) E3, draft | `2f8b570` | Green |

Line numbers are at those heads.

## Verdict

| Pull request | Verdict |
| --- | --- |
| L1 | Ready to merge |
| A1 | Ready to merge. One nit |
| S1 | Ready once the owner has built a change set and seen no replacement of the API domain |
| E1, E2, E3 | Ready after R3-7. No blocker |
| A2 | Ready after R3-8 and R3-9 |
| F1, F2 | Hold: R3-1 |
| L2, L3 | Hold: R3-2, R3-3 |
| S2, S3, S4 | Hold: R3-4 |

## Blockers

### R3-1. findingalpha F1: the token check gives 500 on a DynamoDB error

`backend/lambda/public_api_authorizer/handler.py:177` now catches
`BotoCoreError` only. `botocore.exceptions.ClientError` is not a subclass of
`BotoCoreError`, so throttling or an internal DynamoDB error escapes the
handler and API Gateway returns 500 where the plan wants a deny. The test
stub at `test_handler.py:26-30` declares `class ClientError(BotoCoreError)`,
which hides it.

Fix: `except (ClientError, BotoCoreError) as exc:`, and make the stub's
`ClientError` subclass `Exception`.

### R3-2. lx-software L2: the backend deploy deletes an export the live admin-web imports

On `main`, `bin/app.ts:78` passes `lxsoftware.httpApi.apiEndpoint`, so the
deployed admin-web stack imports CDK's automatic export of that endpoint
(`ExportsOutputFnGetAttHttpApi…ApiEndpoint…`). L2 no longer references the
endpoint, so the backend template drops that export. The backend deploys
first, and CloudFormation refuses to delete an export another stack imports.
The update rolls back.

The new `lxsoftware-CspApiExecuteApiOrigin` output also has an empty value
when the custom domain is off, and CloudFormation rejects an empty export.
Production sets the domain, so production would not hit that part.

Fix: build the content security policy origin as
`Fn.join(" ", [Fn.importValue("lxsoftware-AdminApiBaseUrl"), lxsoftware.httpApi.apiEndpoint])`.
That keeps the automatic export under its old name, and the
`CspApiExecuteApiOrigin` output can go. Add a stack test that the backend
still exports the old name.

findingalpha F1 already does this correctly: it keeps the old export in
`app-assembly.ts:40`.

### R3-3. lx-software L3: the same failure one release later

L3 deletes the export that L2's admin-web imports. With the R3-2 fix, that
is the execute-api endpoint export. Keep it in L3, and remove it in a later
pull request after L3's admin-web has deployed. Pin it with a stack test.

### R3-4. siutindei S2: gateway error bodies will not be JSON

`backend/infrastructure/lib/api-stack.ts` near 2395 to 2425 starts the
`DEFAULT_4XX` and `MISSING_AUTHENTICATION_TOKEN` templates with a chain of
`#set(...)` and `#if(...)` lines to choose a title. AWS processes gateway
response templates with "a non-VTL mapping template supporting only simple
variable substitutions"
([gateway responses](https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-gatewayResponse-definition.html)).
evolvesprouts E1 records the same thing at `api-stack.ts:3282`: an earlier
Velocity template there leaked `#set` and `#if` text. Every gateway 401,
403, 404 and 429 would start with literal directives, and a client that
parses JSON fails on it.

Fix: drop the chain. Use one fixed title per gateway response, as
evolvesprouts E1 does, or give each needed response type its own gateway
response with a literal title. Each extra response is one resource, and the
stack is at 496 of 500.

## Should fix

- **R3-5. siutindei S2 and evolvesprouts E1: `x-request-id` on gateway
  errors is a literal.** Both set the header to `'$context.requestId'`.
  Gateway response headers take "any incoming request parameter value or a
  static custom value"
  ([gatewayResponse object](https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-swagger-extensions-gateway-responses.gatewayResponse.html)).
  A quoted value is static, so clients receive the text `$context.requestId`.
  The body's `request_id` substitutes correctly. Drop the header from
  gateway responses in both, and fix the siutindei comment near 2376 and the
  assertion that locks the literal in `assert-existing-db.ts`.
- **R3-6. siutindei S2: the gateway error CORS origin is the mobile app's.**
  Now that the header names are right (S2-2), `Access-Control-Allow-Origin`
  reaches clients as `corsAllowedOrigins[0]`, which is
  `capacitor://localhost`. Browser errors from the admin site stay blocked.
  Choose the origin as the WAF does near `api-stack.ts:3390`.
- **R3-7. evolvesprouts E1: `detail` is dropped from most handler errors.**
  `backend/src/app/exceptions.py:40` emits `detail` only when it differs
  from `error`. Section 4.5 lists `detail` on every handler error. Emit
  `detail or message`. The admin client fix already removes the "X (X)"
  text.
- **R3-8. actions A2: evolvesprouts cannot adopt the check without an
  undocumented step.** `{grantId}` must stay (round 2, B1), and the check
  rejects it as not snake_case on E1, E2 and E3. A legacy entry is the way
  out, but `check.py:370` skips every rule for a legacy path while
  `api-contract/README.md:20` describes a prefix exemption. State that in
  the README, and add "evolvesprouts adds
  `/v1/admin/assets/{id}/grants/{grantId}` to `docs/api/legacy-paths.txt`" to
  the rollout steps at `:42-46`. Run the `{proxy+}` rule before the legacy
  skip, so a legacy entry cannot admit `/v1/public/{proxy+}`.
- **R3-9. actions A2: the notes on #98 have no end.** A2 says #98 "stays
  open and unmerged" but not that it is closed. Write: close #98 unmerged
  once A2 merges. Put the README rollout order at the end of the A2 body, in
  place of the old one-line instruction.
- **R3-10. findingalpha F1: confirm the custom domain is on before merging.**
  F1 makes admin-web import `findingalpha-AdminApiBaseUrl`, whose value
  changes when the custom domain is switched on or off. CloudFormation
  refuses to change an imported export. The repository variable
  `API_CUSTOM_DOMAIN_NAME` is set and `api.findingalpha.app` is live, so
  this should be fine. State in the F1 body that the name and the
  certificate are both set.
- **R3-11. lx-software L3: `check_admin_spa_config.py` checks nothing.**
  Nothing sets `ADMIN_SPA_CONFIG_URL` and the admin site has no
  `config.json`, so every deploy prints a skip. If someone set it, the check
  would fetch the old site's HTML and fail the deploy. Drop the script and
  its call, and assert in `check-admin-spa-settings.sh` that `api_url`
  contains no `execute-api`.
- **R3-12. findingalpha F2: drop the precondition from the API
  `Description`** (`http-api.ts:175`) and its two test assertions.
- **R3-13. siutindei S2: the new authorizer permission can race.** It has
  no dependency on the deployment, so partner calls can fail for a few
  seconds during the update. Add the dependency or note the window in the
  body. Say "merge at a quiet hour" in the body, as plan section 10 asks.
- **R3-14. siutindei S2: squash-merge.** The seed file was edited and then
  reverted inside the branch. The net diff is empty, but a merge commit
  keeps the edit in `main`'s history.

## Nits

- A1: `api-contract.md:50` and `decisions.md:75` say "for one deploy" twice.
- A2: a schema property named `servers` under an operation is flagged as a
  path-level `servers`; a non-path key under `paths` and `paths: &anchor`
  report flow-style YAML; subdirectories of `docs/api` are ignored; the PR
  body's fixture wording is misleading.
- F1: `adminFetch` passes the route without the method, so a future
  `rootMaps` entry would not match in TypeScript; a non-JSON 304 still
  throws; nothing records that the kept execute-api export goes in the next
  release; `httpApiEndpoint` is unused.
- L1: plain-text responses in `board_newsletter.py`, `board_outreach.py` and
  `board_meta.py` lack `x-request-id`.
- L2: `docs/deployment/admin-website.md:405` is garbled; `byStage` and
  `byStatus` in `board_progress.py` are status-keyed maps missing from
  `mapFields`; `test_check_contracts.py` uses a fixed `/tmp` path;
  `Stack#addDependency` is deprecated.
- L3: `board-alias-wire-cache.md:29` still says "both credential headers or
  neither".
- S2: 413 and 415 gateway errors read "Bad Request" (moot after R3-4).
- S3, S4: `PUBLIC_API_RATE_PATH` in `edge_policy.py:50` is unused.
- S4: one off-host script or a missing chunk fails the whole bundle check.
- E1: the router test says it reads the media rewrite function but reads
  only the www proxy functions; a malformed or invalid token gets 403, not
  401.
- E3: the cutover check accepts 3xx; `.env.example:44` and
  `publish-promotion-summary.sh:12` still name `/www`.

## Second-round items

| Item | Status |
| --- | --- |
| B1 evolvesprouts grant route | Fixed. Logical id equals `main` on E1, E2, E3 |
| B2 evolvesprouts `/v1/public` 404s | Fixed. Every `public.yaml` path and both media rewrite targets reach their handler on E1, E2, E3. A router test fails on 12 paths without the fix |
| B3 admin-web condition | findingalpha fixed. lx-software fixed for the condition, broken for exports (R3-2, R3-3) |
| B4 lx-software IP-keyed cache | Fixed. L2 TTL 0 with a test; L3 `Authorization` plus source IP, 60 s |
| B5 lx-software catalog import | Fixed, with full-URL tests |
| B6 siutindei seed file | Fixed. Net diff empty in S2 to S4; bodies name line 296 (R3-14) |
| B7 siutindei change set | Body corrected. The owner still builds the change set |
| A1-1, A1-2, A1-3 | Fixed |
| A2-1 rollout order | Partly (R3-9) |
| A2-2 plan note | Partly (R3-9) |
| A2-3 to A2-6 checker holes | Fixed. Every adversarial input now fails |
| F1-1 to F1-4 | Fixed |
| F2-1 | Partly (R3-12) |
| L2-1, L2-2, L2-3 | Fixed. Codec files byte-identical to findingalpha `6408c95` |
| L3-1 | Partly (R3-11) |
| S2-1 legacy key rate rule | Fixed; S4 removes it |
| S2-2 gateway headers | Partly. Names fixed; value literal (R3-5); origin wrong (R3-6) |
| S2-3 authorizer replacement | Fixed. New construct id, methods and permission moved |
| S2-4, S2-5, S2-6 | Fixed |
| S3-1, S3-2, S4-1 | Fixed |
| E1-1 to E1-5 | Fixed; E1-5 overreached (R3-7) |
| E3-1, E3-2 | Fixed |
| X-1 redirects | Fixed in L3, S4, E3 |

## Verified this round

- Local suites pass on every head: findingalpha (Python 494, infra 39,
  admin 67), lx-software (admin Python about 2,030, infra 91, admin 500),
  siutindei (`test:infra` 34, targeted Python up to 109), evolvesprouts
  (`test:infra`, lint, typecheck, targeted Python 422 to 428).
- Synth: no template names a condition it does not define, in findingalpha
  and lx-software.
- Resource counts: siutindei 493, 496, 496, 496. evolvesprouts 472, 473,
  386.
- The A2 checker passes findingalpha, lx-software and siutindei at their
  heads, and rejects only `{grantId}` in evolvesprouts.

## Not verified

No change set, deploy or live probe was run. Still unverified against AWS:

- that the REST authorizer replacement in S2 and the identity-source
  removal in E1 take effect on update;
- that API Gateway accepts an empty base path mapping beside `prod` (E1);
- WAF capacity in siutindei S2, estimated at 300 to 400 of 1,500.

R3-4 and R3-5 rest on the AWS documentation and on the evolvesprouts
comment, not on a live probe. A `put-gateway-response` on a scratch REST API
would settle both.
