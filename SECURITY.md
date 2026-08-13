# Security notes

This document reflects FastAPI `2.0.0` and WordPress plugin `2.0.1`.

## Current model

- The browser sends form data only to WordPress.
- WordPress validates and sanitizes fields before relaying them.
- WordPress authenticates to Cloud Run with a server-side integration secret.
- FastAPI validates the payload again and compares secrets in constant time.
- Client-generated idempotency keys prevent ordinary network retries from
  appending duplicate rows.
- Ability modifiers, totals, and weighted evaluation scores are recalculated by
  FastAPI; displayed browser calculations are previews only.
- Cloud Run uses its assigned Google service account through Application Default
  Credentials.
- The Google Sheet is shared only with authorized people and the runtime service
  account.
- `.env`, `credentials.json`, local data, and virtual environments are excluded
  from Git, Docker build context, and Cloud source uploads.

## Important limitations

- A static shared secret authenticates the WordPress server, not the individual
  person submitting the form.
- The Cloud Run service is publicly reachable because hosted WordPress cannot
  use Google IAM easily; the application secret protects the write endpoint.
- CORS is not authentication. This design does not rely on CORS for protection.
- Google Sheets is convenient storage, not a transactional database.
- Spreadsheet-based duplicate checks are sufficient for this demonstration but
  are not atomic under heavy concurrent traffic; production scale should use a
  transactional idempotency store.
- Idempotency prevents retry duplicates, not intentional repeat submissions
  created with new keys.
- The current weighted evaluation workflow is API-only; it does not authenticate
  an individual judge or provide a WordPress evaluation UI.

## Before real contest or company use

- Move all infrastructure into a company-owned Google Cloud project.
- Use a staging WordPress site before production installation.
- Require authenticated judges or another verifiable participant identity.
- Replace the static header with timestamped HMAC request signing to reduce
  replay risk.
- Add rate limiting, deadline enforcement, and business-level duplicate rules
  such as one evaluation per authenticated judge and subject.
- Store raw ratings and the server-calculated weighted result for auditability.
- Protect spreadsheet headers/formulas and restrict sharing.
- Add structured logs, monitoring, and alerts without logging secrets or
  unnecessary personal data.
- Document retention, privacy, tie-breaking, and correction rules.
- Rotate any secret that appears in terminal output, screenshots, chat, or Git.

## Reporting a vulnerability

Do not include credentials, private spreadsheet data, or active secret values in
an issue. Revoke or rotate exposed credentials first, then report the behavior
using redacted reproduction steps.
