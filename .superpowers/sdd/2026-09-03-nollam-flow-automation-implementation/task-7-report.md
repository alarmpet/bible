# Task 7 report — Flow fixture adapter and completion detector

Implemented versioned Flow selectors, baseline/new-card attribution, preflight guards, and prompt submission adapter.

- New cards must be absent from the baseline, have nonzero media dimensions, and report stable observations.
- Old cards, busy generation, ambiguous results, and changed UI fail closed.
- Preflight requires the exact expected Flow project URL and image mode.
- Added sanitized fixture placeholders and deterministic detector tests.

Verification: `node --test tests/extension/*.test.js` — 22 passed, 0 failed.