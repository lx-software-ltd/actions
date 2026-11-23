# Play prerequisites

Sets the output `should_upload`. It is true only when the Play service account, the release track, and the four Android signing secrets are all set. A missing value skips and exits 0.

The Play upload `uses:` stays in the caller.

## Inputs

| Input | Required | Default | Meaning |
| --- | --- | --- | --- |
| `service-account` | no | empty | Play service-account JSON. |
| `track` | no | empty | Release track. |
| `keystore-base64` | no | empty | Base64-encoded keystore. |
| `keystore-password` | no | empty | Keystore password. |
| `key-password` | no | empty | Key password. |
| `key-alias` | no | empty | Key alias. |
| `upload-enabled` | no | empty | When set, only `true` continues. Empty does not check. |
| `package-name` | no | empty | Android package name. |
| `require-package-name` | no | `false` | `true` skips the upload when `package-name` is empty. |

## Example

```yaml
- id: play
  uses: lx-software-ltd/actions/play-prerequisites@<sha> # main <yyyy-mm-dd>
  with:
    service-account: ${{ secrets.GOOGLE_PLAY_SERVICE_ACCOUNT }}
    track: ${{ vars.ANDROID_RELEASE_TRACK }}
    keystore-base64: ${{ secrets.ANDROID_KEYSTORE_BASE64 }}
    keystore-password: ${{ secrets.ANDROID_KEYSTORE_PASSWORD }}
    key-password: ${{ secrets.ANDROID_KEY_PASSWORD }}
    key-alias: ${{ secrets.ANDROID_KEY_ALIAS }}
```
