# Bible & Modern Story Video Production Pipeline

성경 힐링 영상 파이프라인(`bible_healing/`)과 현대 드라마 대본·영상 파이프라인(`modern/`)의 통합 저장소입니다.

---

## 1. 요구 환경 (Prerequisites)

- **OS**: Windows 10/11 (권장) 또는 Linux
- **Python**: Python 3.10 이상 (테스트 및 코어 검증 3.10 ~ 3.14 지원)
- **외부 도구 (렌더링 & 오디오)**:
  - [FFmpeg](https://ffmpeg.org/) (시스템 PATH 등록 권장)
- **선택적 TTS 엔진 (로컬 음성 합성 실행 시)**:
  - Supertonic3 로컬 TTS 서버 (`http://127.0.0.1:3093`)
  - 또는 Fun-CosyVoice3 환경

---

## 2. 빠른 시작 (Quick Start)

다른 PC에서 처음 저장소를 내려받아 환경을 구성하는 순서입니다.

### 1) 저장소 복제 (Clone)
```powershell
git clone https://github.com/alarmpet/bible.git
cd bible
```

### 2) 가상환경 생성 및 의존성 설치
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
```

### 3) 파이프라인 단위 테스트 검증
```powershell
pytest
```
> 모든 150+ 개 테스트가 정상 통과(PASSED)하면 기본 환경 구성이 완료된 것입니다.

---

## 3. 모듈별 파이프라인 안내

### A. 구약 힐링 낭독 영상 파이프라인 (`bible_healing/`)

공개 성경(개역한글) 텍스트와 감성적 나레이션, 이중 보이스(여성 나레이터 + 남성 성경 낭독), 앰비언트 배경 영상 및 번인 자막을 결합하여 장편(약 100분) 영상을 제작합니다.

- **주요 진입점 (풀 파이프라인 실행)**:
  ```powershell
  python bible_healing/scripts/run_full_media_pipeline.py --job bible_healing/runs/ep01_anxious_night/hermes_jobs/full
  ```
- **단계별 실행 (준비 단계)**:
  1. 성경 원문 파싱: `python bible_healing/scripts/parse_osis_to_json.py`
  2. 에피소드 스크립트 빌드: `python bible_healing/scripts/build_episode.py --episode ep01_anxious_night`
  3. QA 및 길이 예측: `python bible_healing/scripts/qa_healing_script.py --episode ep01_anxious_night`
  4. Hermes 작업 패킹: `python bible_healing/scripts/pack_to_hermes.py --episode ep01_anxious_night --mode full`
- **핵심 문서**:
  - `CLAUDE.md`: 구약 힐링 작업 규칙 및 필수 게이트
  - `MEDIA_RULES.md`: 미디어 규칙 및 음성/자막/배경 규격
  - `bible_healing/README.md`: 상세 운영 가이드

---

### B. 현대 드라마 대본 파이프라인 (`modern/`)

현대 드라마 콘텐츠 기획부터 분량 통제, 캐릭터 일관성, 15비트 플롯 설계, 자동 품질 감사까지 지원하는 파이프라인입니다.

- **스토리 품질 감사 CLI 실행**:
  ```powershell
  python modern/scripts/audit_story_quality.py --text modern/runs/smoke_g4/final.txt --contract modern/templates/project_contract.yaml
  ```
- **캐릭터 작명 스크립트**:
  ```powershell
  python modern/name_picker.py 중산 여 --n 6
  ```
- **핵심 문서**:
  - `modern/README.md`: 현대 파이프라인 구조 및 가이드
  - `modern/v12_modern_main_SONNET.md`: 메인 생성 프롬프트
  - `modern/HANDOFF.md`: 대본 작업 핸드오프

---

## 4. 저장소 디렉터리 구조

```text
├── bible_healing/           # 성경 힐링 파이프라인
│   ├── assets/              # 보이스 레퍼런스(voice_refs) 및 배경 소스
│   ├── config/              # 보이스/미디어 룰 락 설정 (media_rules_lock.json 등)
│   ├── data/                # 성경 원문 및 파싱 데이터 (verses, narration_banks)
│   ├── scripts/             # 오디오 필터링, 자막(ASS) 생성, 풀 파이프라인 스크립트
│   └── tests/               # 단위 및 통합 테스트
├── modern/                  # 현대 드라마 파이프라인
│   ├── config/              # 콘텐츠 레인, 분량 매트릭스, QA 기준
│   ├── scripts/             # 품질 감사 CLI, TTS 어댑터
│   ├── templates/           # 프로젝트 계약, 팩트시트, 스토리 바이블 템플릿
│   └── tests/               # 품질 게이트 및 스모크 테스트
├── docs/                    # 기술 사양서 및 렌더링 정책 문서
├── CLAUDE.md                # AI 어시스턴트 및 작업자 규칙 가이드
├── MEDIA_RULES.md           # 미디어 제작 규격 및 오디오/비디오 정책
├── PATHS.md                 # 프로젝트 경로 단일 관리 매핑
├── pytest.ini               # pytest 설정
├── requirements.txt         # 파이썬 의존성 패키지 목록
└── README.md                # 프로젝트 안내 문서 (본 문서)
```

---

## 5. 라이선스 및 데이터 출처

- 성경 원문: 개역한글(KRV) 공개 텍스트 ([seven1m/open-bibles](https://github.com/seven1m/open-bibles))
- 나레이션 및 현대 대본 프롬프트: 자체 창작물
