# Task 8 report — download correlation and worker recovery

Implemented `DownloadRegistry` with durable storage hooks, exact shot/prompt/attempt bindings, filename validation, duplicate completion idempotency, and restart restoration that pauses missing or interrupted downloads. Connected Chrome download completion events in the service worker to `DOWNLOAD_COMPLETED` messages.

Verification: `node --test tests/extension/*.test.js` — 26 passed, 0 failed.