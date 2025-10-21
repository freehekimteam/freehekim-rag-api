# Security Policy
- KVKK/GDPR: No personal data is ever stored or embedded.
- Secrets: Only via GitHub Environments; rotation every 90 days.
- Network: Qdrant/API reachable only via Cloudflare Tunnel; bind 127.0.0.1 on server.
- Backups: Encrypted snapshots; 14-day retention with rotation.
- Incidents: Report to security@hakancloud.com.

## Runtime Protections
- Per-IP rate limiting (default: 60 req/min; configurable via `RATE_LIMIT_PER_MINUTE`).
- Request body size limit (default: 1 MB; configurable via `MAX_BODY_SIZE_BYTES`).
- Uniform error responses avoid leaking internals; generic 500 message.
- Request ID header (`X-Request-ID`) for traceability.
- Optional API key: Enable `REQUIRE_API_KEY=true` and distribute a secret `API_KEY`. Clients must send `X-Api-Key`.
