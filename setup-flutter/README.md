# Set up Flutter

Installs Flutter `3.50.1` on the stable channel and caches the SDK. A caller that needs another version passes `flutter-version`. An empty version fails before the install.

The pin is `subosito/flutter-action` `1a449444c387b1966244ae4d4f8c696479add0b2` (v2.23.0).

## Inputs

| Input | Required | Default | Meaning |
| --- | --- | --- | --- |
| `flutter-version` | no | `3.50.1` | Flutter version. Empty fails. |
| `channel` | no | `stable` | Flutter channel. |
| `cache` | no | `true` | Cache the SDK. |

## Example

```yaml
- uses: lx-software-ltd/actions/setup-flutter@<sha> # main <yyyy-mm-dd>
```
