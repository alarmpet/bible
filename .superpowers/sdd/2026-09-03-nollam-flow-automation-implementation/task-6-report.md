# Task 6 report — MV3 extension and native-host dispatcher

## Result

Implemented the minimal Manifest V3 extension connection and Python native-host dispatcher.

## Changed files

- `human_archive/flow_automation/extension/manifest.json`
- `human_archive/flow_automation/extension/service-worker.js`
- `human_archive/flow_automation/native_host/host.py`
- `human_archive/flow_automation/tests/test_host.py`
- `human_archive/flow_automation/tests/extension/manifest.test.js`

## Guarantees

- Requests only the approved MV3 permissions and `https://labs.google/*` host access.
- Restricts content scripts to Flow project pages.
- Uses `chrome.runtime.connectNative('com.nollam.flow_automation')` with reconnect and `LOAD_JOB`.
- Validates job-bound native messages and returns durable `JOB_STATE` responses.
- Rejects unapproved retry limits/modes and unsupported commands with fail-closed `JOB_PAUSED` responses.
- Appends submission/pause/stop events before returning side-effect commands.

## Verification

- `python -m pytest flow_automation/tests/test_host.py flow_automation/tests/test_protocol.py -v`: 15 passed.
- `node --test flow_automation/tests/extension/*.test.js`: 18 passed.