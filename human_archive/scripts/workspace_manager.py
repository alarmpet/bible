# -*- coding: utf-8 -*-
"""Thread-Safe Workspace Context Manager for Episode Isolation (TDAAH Architecture).
Dynamically provisions and manages episode-specific directories, constitutions,
and state vectors without cross-contaminating existing projects.
"""
from __future__ import annotations

import datetime
import json
import re
import shutil
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

RUNS_ROOT = Path(r"D:\module\bible\human_archive\runs\nollam_file")
DEFAULT_EPISODE = RUNS_ROOT / "2026-09-02" / "himalaya-glof-water-crisis"


class WorkspaceContextManager:
    """Manages active episode workspace and provisions new isolated workspaces."""

    def __init__(self, default_ep_dir: Path = DEFAULT_EPISODE):
        self._lock = threading.Lock()
        self._current_ep_dir = default_ep_dir if default_ep_dir.exists() else DEFAULT_EPISODE

    @property
    def current_ep_dir(self) -> Path:
        with self._lock:
            return self._current_ep_dir

    def set_current_ep_dir(self, new_dir: Path) -> bool:
        with self._lock:
            if new_dir.exists() and new_dir.is_dir():
                self._current_ep_dir = new_dir
                return True
            return False

    def create_episode_workspace(
        self,
        topic_slug: str,
        topic_title: str,
        category: str = "다큐멘터리",
        target_duration_sec: float = 1200.0,
    ) -> Path:
        """Create a new isolated episode workspace with full 2-tier memory bootstrap."""
        with self._lock:
            today_str = datetime.date.today().strftime("%Y-%m-%d")
            clean_slug = re.sub(r"[^a-zA-Z0-9_\-]+", "-", topic_slug.lower()).strip("-")
            if not clean_slug:
                clean_slug = f"episode-{datetime.datetime.now().strftime('%H%M%S')}"

            ep_dir = RUNS_ROOT / today_str / clean_slug
            ep_dir.mkdir(parents=True, exist_ok=True)

            # Create essential directories
            (ep_dir / "audit").mkdir(exist_ok=True)
            (ep_dir / "images").mkdir(exist_ok=True)
            (ep_dir / "source").mkdir(parents=True, exist_ok=True)
            (ep_dir / "audio" / "sentences_v4").mkdir(parents=True, exist_ok=True)
            (ep_dir / "candidate" / "motion_clips").mkdir(parents=True, exist_ok=True)
            (ep_dir / "generation" / "downloads" / "approved").mkdir(parents=True, exist_ok=True)

            now_iso = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            now_kor = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

            # 1. Bootstrap AGENTS.md
            agents_md = f"""# AGENTS.md — 에피소드 전용 AI 헌법 및 런타임 불변식
- **에피소드 ID**: `{clean_slug}`
- **주제명**: {topic_title}
- **장르/분야**: {category}
- **목표 런타임**: {target_duration_sec:.1f}초 (20분 ±30%)

## 불변식 (Invariants)
1. 105개 씬 유동 분할 및 오디오 타임라인 오차 0.0s 엄수
2. Google Flow CDP 1-Shot-1-Completion 순차 생성 및 3초 쿨다운
3. 1080p Lanczos 정규화 및 SHA-256 매니페스트 바인딩
4. 테스트 주도 자가치유 (pytest 통과 필수)
"""
            (ep_dir / "AGENTS.md").write_text(agents_md, encoding="utf-8")

            # 2. Bootstrap TASK.md
            task_md = f"""# TASK.md — 활성 작업 계약서
## [과업명] {topic_title} 20분 마스터 다큐멘터리 제작

- **상태**: `[/] 진행 중 (In Progress)`
- **우선순위**: P0
- **생성 일시**: {now_kor}

### 마일스톤 체크리스트
- [x] 에피소드 독립 작업공간 초기화 ({clean_slug})
- [ ] Gate 1: 120초 오프닝 파일럿 쾌속 생성 및 마스터 시네마 검증
- [ ] Gate 2: 20분 전체 105개 씬 Google Flow CDP 일괄 생성
- [ ] FFmpeg 마스터 비디오 최종 합성 및 4중 안티-환각 게이트 승인
"""
            (ep_dir / "TASK.md").write_text(task_md, encoding="utf-8")

            # 3. Bootstrap PROGRESS.md
            progress_md = f"""# PROGRESS.md — 에피소드 진척 및 마일스톤
## {today_str}

### [{now_kor}] 에피소드 작업공간 동적 프로비저닝 완료
- **주제**: {topic_title}
- **경로**: `{ep_dir}`
- **상태**: 2계층 외재화 기억 체계 초기화 완료.
"""
            (ep_dir / "PROGRESS.md").write_text(progress_md, encoding="utf-8")

            # 4. Bootstrap ERRORS.md (Include verified solutions)
            errors_md = f"""# ERRORS.md — 과거 결함 레지스트리 및 해결 지식베이스
본 문서는 {clean_slug} 프로덕션 중 발생한 결함과 기검증된 5대 해결책을 계승합니다.

### [ERR-001] 30초 고정 그리드 무음 결함 -> 105개 씬 유동 분할 적용
### [ERR-002] Google Flow 비디오 모드 기본값 -> ensure_image_mode() 강제
### [ERR-003] Google Flow 과거 카드 오감지 -> 신규 URL 차집합 판정
### [ERR-004] write_to_file 경로 위반 -> scratch 임시 작성 후 복사
### [ERR-005] Web GUI JS 문법 오류 -> padStart 표준 함수 사용
"""
            (ep_dir / "ERRORS.md").write_text(errors_md, encoding="utf-8")

            # 5. Bootstrap EPISODE_STATE.json
            state_data = {
                "episode_id": clean_slug,
                "title": topic_title,
                "category": category,
                "target_duration_sec": target_duration_sec,
                "current_duration_sec": 0.0,
                "timing_drift_sec": 0.0,
                "total_scenes": 105,
                "completed_scenes": 0,
                "failed_scenes": 0,
                "active_task_id": f"TASK-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}",
                "cdp_port": 9222,
                "cdp_connected": True,
                "cdp_mode": "IMAGE_16_9",
                "harness_tests_passing": True,
                "workflow_stage": "WORKSPACE_INITIALIZED",
                "last_updated": now_iso,
            }
            (ep_dir / "EPISODE_STATE.json").write_text(
                json.dumps(state_data, ensure_ascii=False, indent=2), encoding="utf-8"
            )

            # Set as active episode
            self._current_ep_dir = ep_dir
            return ep_dir


# Global Singleton Instance
workspace_mgr = WorkspaceContextManager()
