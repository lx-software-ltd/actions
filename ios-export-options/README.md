# iOS export options

Writes `ios/ExportOptions.plist` in the Flutter app directory. A provisioning profile selects manual signing. An empty profile stays automatic.

The plist uses the App Store method, with bitcode off and the `Apple Distribution` certificate.

## Inputs

| Input | Required | Default | Meaning |
| --- | --- | --- | --- |
| `working-directory` | yes | | Flutter app directory. |
| `team-id` | yes | | Apple team id. |
| `bundle-id` | yes | | Bundle id, including the caller's default. |
| `provisioning-profile` | no | empty | Manual profile name. |

## Example

```yaml
- uses: lx-software-ltd/actions/ios-export-options@<sha> # main <yyyy-mm-dd>
  with:
    working-directory: apps/example_app
    team-id: ${{ vars.APPLE_TEAM_ID }}
    bundle-id: ${{ vars.IOS_BUNDLE_ID }}
    provisioning-profile: ${{ vars.IOS_PROVISIONING_PROFILE }}
```
