# Android signing

Decodes `keystore.p12` into `<working-directory>/android/app`. Any missing signing secret skips the step and exits 0.

## Inputs

| Input | Required | Default | Meaning |
| --- | --- | --- | --- |
| `working-directory` | yes | | Flutter app directory. |
| `keystore-base64` | no | empty | Base64-encoded keystore. |
| `keystore-password` | no | empty | Keystore password. |
| `key-password` | no | empty | Key password. |
| `key-alias` | no | empty | Key alias. |

## Example

```yaml
- uses: lx-software-ltd/actions/android-signing@<sha> # main <yyyy-mm-dd>
  with:
    working-directory: apps/example_app
    keystore-base64: ${{ secrets.ANDROID_KEYSTORE_BASE64 }}
    keystore-password: ${{ secrets.ANDROID_KEYSTORE_PASSWORD }}
    key-password: ${{ secrets.ANDROID_KEY_PASSWORD }}
    key-alias: ${{ secrets.ANDROID_KEY_ALIAS }}
```
