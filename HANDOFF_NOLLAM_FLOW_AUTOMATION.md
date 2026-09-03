# NOLLAM Flow Automation Handoff

## 목적

Google Flow 프로젝트에서 지정된 이미지 생성 작업을 확장프로그램과 네이티브 호스트로 순차 실행하고, 다운로드 파일명·샷 ID·프롬프트 해시를 검증한 뒤 후속 렌더링으로 넘기는 작업이다.

## 현재 작업 범위

- Flow 프로젝트 URL: `https://labs.google/fx/ko/tools/flow/project/b0aa7ff4-49c0-4841-b333-7f4e52ddcc12`
- 작업 ID: `NOLLAM-20260903-HIMALAYA-GLOF-v1`
- 파일 형식: image / 16:9
- 파일 수: 20 shots
- 총 길이: 120 seconds
- 실행 파일: `D:\module\bible\human_archive\runs\nollam_file\2026-09-02\himalaya-glof-water-crisis\generation\automation_job.json`
- 원본 105샷은 보존되어 있으며, 실행용으로 첫 20샷만 별도 생성했다.

## 완료된 구현

최근 커밋 순서:

- `ba306af` Task 5 queue/retry/state machine
- `861984e` MV3 manifest/service worker/native dispatcher
- `43a4790` Flow selectors/completion detector/adapter
- `36b6d24` download registry and completion correlation
- `83b2595` side panel UI
- `d1c594e` native host launcher/install template
- `78def06` semantic review/contact-sheet approval
- `d14ba7c`, `a76064a` render gate and explicit render manifest
- `9698af2` offline resumable E2E test
- `388f7eb` runbook/readme
- `e4bdd4d` side-panel job-file loading
- `cc0360e` toolbar side-panel action
- `8e2d553` 20-shot pilot job and native job initialization
- `07aba9e` side-panel message transport fix

핵심 수정 파일:

- `D:\module\bible\human_archive\flow_automation\extension\sidepanel\index.js`
- `D:\module\bible\human_archive\flow_automation\extension\service-worker.js`
- `D:\module\bible\human_archive\flow_automation\native_host\host.py`

## 발견한 원인과 수정 내용

1. 사이드패널은 `chrome.runtime.connect()` 포트로 메시지를 보냈지만 서비스워커는 `chrome.runtime.onMessage`만 처리하고 있었다. 파일 선택과 버튼 클릭이 모두 유실되던 원인이다.
2. 사이드패널 명령이 네이티브 메시지 envelope로 포장되지 않았다. 서비스워커에서 `makeEnvelope()`로 변환하도록 수정했다.
3. `SET_ACTIVE_JOB`에서 받은 실제 job JSON을 서비스워커가 `LOAD_JOB` payload로 네이티브 호스트에 전달하도록 수정했다.
4. 네이티브 호스트가 시작 직후 항상 `_default_context()` 예외를 내던 부분을 제거하고 첫 `LOAD_JOB` payload에서 작업 컨텍스트를 초기화하도록 수정했다.

## 검증 결과

- Python Flow Automation 전체: 61 passed
- JavaScript extension 전체: 29 passed
- 실제 native host subprocess에 job JSON 주입: `JOB_STATE`, 20 shots 응답 확인
- Chrome 진단:
  - Chrome 실행 중
  - 공식 ChatGPT Chrome 확장프로그램 설치 및 활성화
  - 공식 native host manifest 정상

## 현재 외부 차단 상태

Chrome 제어 런타임을 통해 직접 탭을 조작하려 했으나 다음 오류로 런타임이 종료됐다.

`trusted Node process exited unexpectedly`

Chrome 자체, 공식 ChatGPT 확장프로그램, native host manifest는 정상으로 진단됐다. 따라서 현재 남은 문제는 NOLLAM 코드가 아니라 Codex 세션의 Chrome 제어 런타임 초기화 문제다. Windows 재부팅이나 NOLLAM 코드 재설치는 우선순위가 아니다.

## 다음 LLM이 수행할 작업

1. 새 Codex 대화에서 Chrome 제어 연결을 다시 시도한다.
2. 연결이 되면 Flow URL의 실제 탭을 확인한다.
3. NOLLAM 확장프로그램을 `chrome://extensions`에서 Reload한다.
4. 사이드패널을 열고 위 `automation_job.json`을 선택한다.
5. 화면에 작업 ID와 `20 shots`가 표시되는지 확인한다.
6. `Generate Missing` 클릭 후 네이티브 응답과 첫 샷 상태를 확인한다.
7. 버튼이 여전히 비활성화되면 사이드패널 콘솔과 서비스워커 오류를 확인한다.

## 주의사항

- 105샷 원본 전체를 실행하지 말 것. 이번 파일은 20샷/120초 파일이다.
- `Generate All`은 실제 생성 크레딧을 소비할 수 있으므로 먼저 `Generate Missing`을 사용한다.
- Flow의 유료 크레딧 사용, 모호한 결과, 프로젝트 URL 불일치는 반드시 fail-closed/pause 해야 한다.
- 작업 JSON을 다시 만들 때는 반드시 위 프로젝트 URL과 작업 ID를 유지한다.

