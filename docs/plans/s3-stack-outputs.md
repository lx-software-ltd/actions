# Stack outputs in the S3 deploy

Zone: yellow. The note stays in this pull request.

`s3-cloudfront-deploy` reads the bucket and the distribution from stack outputs when `stack` and `region` are set. The reader is `lib/stack_outputs.py`. `cfn-stack-outputs` uses that module too. The S3 action does not load the other action's file.

A missing bucket output fails the deploy. A missing or empty distribution output prints a warning and skips invalidation. A missing stack is still the caller's notice, not this action's skip.

No product workflow passes `stack` until this commit is on `main`.
