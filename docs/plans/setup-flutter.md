# Flutter setup

Zone: yellow. The note stays in this pull request.

`setup-flutter` installs one Flutter version through `subosito/flutter-action` at `1a449444c387b1966244ae4d4f8c696479add0b2` (v2.23.0). The default is 3.50.1 on stable, with the SDK cache on. An empty version fails before that action runs.

Product workflows keep their current Flutter step until this commit is on `main`.
