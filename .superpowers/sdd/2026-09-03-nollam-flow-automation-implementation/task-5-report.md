# Task 5 report — fail-closed queue state machine

## Result

Implemented the extension core retry policy, legal state transitions, and serialized shot queue.

## Changed files

- `human_archive/flow_automation/extension/core/retry-policy.js`
- `human_archive/flow_automation/extension/core/state-machine.js`
- `human_archive/flow_automation/extension/core/queue.js`
- `human_archive/flow_automation/tests/extension/retry-policy.test.js`
- `human_archive/flow_automation/tests/extension/state-machine.test.js`
- `human_archive/flow_automation/tests/extension/queue.test.js`

## Guarantees

- Retryable transient failures retry only before the configured limit.
- Authentication, CAPTCHA, paid-credit, project/mode mismatch, ambiguous attribution, selector/update failures, and exhaustion pause.
- The queue keeps at most one active shot and cannot advance until `SHOT_ACCEPTED`.
- Stop requests prevent further selection.
- Delay generation uses `crypto.getRandomValues()` and the inclusive configured range.
- `selectNextShot(snapshot, mode)` selects retry work or the next non-terminal shot.

## Verification

Command: `node --test tests/extension/*.test.js`

Result: 16 tests passed, 0 failed.

The repository has unrelated pre-existing working-tree changes; only the Task 5 implementation and report were staged.