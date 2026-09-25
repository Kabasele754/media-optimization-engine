# CDN and edge delivery

MOE derivative paths are content-addressed and pipeline-versioned, so generated media can be cached as immutable.

Recommended public cache policy for derivatives and panorama tiles:

```text
Cache-Control: public, max-age=31536000, immutable
```

Originals are regeneration sources and should not be publicly exposed by default.

For Cloudflare R2 or another S3-compatible backend, keep the same manifest contract; only the resulting storage/CDN URLs change.
