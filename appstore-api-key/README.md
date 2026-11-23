# App Store Connect API key

Writes `APPSTORE_ISSUER_ID`, `APPSTORE_API_KEY_ID`, and `APPSTORE_API_PRIVATE_KEY` to `GITHUB_ENV`. A JSON payload wins. When every input is empty the step skips and exits 0. A partial key fails.

The TestFlight upload stays in the caller. It is one `uses:` and is not wrapped.

## Inputs

| Input | Required | Default | Meaning |
| --- | --- | --- | --- |
| `api-key-json` | no | empty | JSON object with `issuer_id`, `key_id`, and `private_key`. |
| `issuer-id` | no | empty | Used when the JSON is empty. |
| `api-key-id` | no | empty | Used when the JSON is empty. |
| `api-private-key` | no | empty | Used when the JSON is empty. |

## Example

```yaml
- uses: lx-software-ltd/actions/appstore-api-key@<sha> # main <yyyy-mm-dd>
  with:
    api-key-json: ${{ secrets.APPSTORE_API_KEY_JSON }}
    issuer-id: ${{ secrets.APPSTORE_ISSUER_ID }}
    api-key-id: ${{ secrets.APPSTORE_API_KEY_ID }}
    api-private-key: ${{ secrets.APPSTORE_API_PRIVATE_KEY }}
```
