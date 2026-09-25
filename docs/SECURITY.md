# Security

## Upload validation

The engine validates image content rather than trusting filename extensions. Upload limits cover bytes and decoded pixel count. Derivatives are re-encoded.

## API keys

Production management endpoints should require a long random API key:

```env
MEDIA_ENGINE_REQUIRE_API_KEY=1
MEDIA_ENGINE_API_KEYS=<secret>
```

Keep keys in deployment secrets and rotate them when necessary.

## Control-plane trust boundary

The optional control plane cannot remotely set database/Redis credentials, API keys, storage credentials, bucket names, arbitrary module paths, or executable content.

## Local autonomy

Normal runtime does not require the control plane. It uses local settings and the persisted last-known-good snapshot.

## Network placement

Prefer a private Docker/VPS network for management APIs and expose public derivatives through Nginx/CDN. If internet-accessible, enforce TLS, API keys, rate limiting and upload limits.

## Originals

Originals are regeneration sources and should be private by default. The provided Nginx configuration denies direct access to `/media/media_engine/originals/`. `MEDIA_ENGINE_PUBLIC_ORIGINAL_FALLBACK=0` remains the recommended production setting.

## Metrics

`/internal/metrics` should be scraped from a trusted internal network, not exposed publicly.
