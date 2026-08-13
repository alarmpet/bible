# -*- coding: utf-8 -*-
"""Assemble upload-ready package: meta, chapters, checklist, path index."""
from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from paths_bh import CONFIG, episode_dir


def main() -> None:
    ep = "ep01_anxious_night"
    ed = episode_dir(ep)
    job = ed / "hermes_jobs" / "full"
    pkg = ed / "upload_package"
    pkg.mkdir(parents=True, exist_ok=True)

    # prefer 100m final if present
    final_100 = job / "final-bible-healing-ep01-100m.mp4"
    final = final_100 if final_100.exists() else job / "final-bible-healing-ep01.mp4"
    if not final.exists():
        raise SystemExit(f"no final mp4 in {job}")

    dest_video = pkg / final.name
    if not dest_video.exists() or dest_video.stat().st_size != final.stat().st_size:
        shutil.copy2(final, dest_video)

    srt = job / "subtitles-ko.srt"
    if srt.exists():
        shutil.copy2(srt, pkg / srt.name)

    ch_path = job / "reports" / "chapter_timestamps.json"
    chapters = json.loads(ch_path.read_text(encoding="utf-8")) if ch_path.exists() else {}

    # rebuild chapter block scaled if using extended final
    extend_rep = job / "reports" / "extend_duration_report.json"
    duration_note = chapters.get("total_time", "?")
    mins = 86
    if extend_rep.exists():
        er = json.loads(extend_rep.read_text(encoding="utf-8"))
        mins = int(round(float(er.get("final_minutes") or 100)))
        duration_note = f"{mins}분"
    else:
        duration_note = "86분"

    title = f"[{mins}분] 불안한 밤을 위한 시편 · 위로 낭독과 현대 해석 | 개역한글"

    ch_block = chapters.get("youtube_description_block") or ""
    desc = f"""잠이 오지 않는 밤, 마음이 앞일을 걱정할 때 —
구약의 시편과 이사야 말씀을 천천히 읽어 드립니다.

점잖은 여성 나레이션으로 오늘의 마음을 짚고,
말씀 구절은 별도의 온유한 보이스로 낭독합니다.
현대적 해석은 위로·공감·치유 방향이며, 가르침이나 정죄가 아닙니다.

⏱ {duration_note} · 취침 전 / 산책 / 혼자 있는 밤에

━━ 챕터 ━━
{ch_block}

━━━━━━━━━━━━━━━━
📖 사용 본문
저작권이 만료된 『성경전서 개역한글판』 계열 공개 본문
(현대 해설·나레이션은 채널 오리지널)

⚠️ 면책
본 콘텐츠는 신앙·위로 목적의 낭독입니다.
의료·심리치료·법률 상담을 대체하지 않습니다.
몸과 마음이 위급할 때는 가까운 전문 기관의 도움을 받으시기 바랍니다.

#시편 #성경낭독 #힐링 #수면 #위로 #개역한글 #구약 #잠자며듣는말씀
"""

    (pkg / "TITLE.txt").write_text(title + "\n", encoding="utf-8")
    (pkg / "DESCRIPTION.txt").write_text(desc, encoding="utf-8")
    (pkg / "TAGS.txt").write_text(
        "시편, 성경낭독, 힐링, 수면, 위로, 개역한글, 구약, 잠자며듣는말씀, 이사야, 불안, 평안\n",
        encoding="utf-8",
    )
    if ch_path.exists():
        shutil.copy2(ch_path, pkg / "chapters.json")

    checklist = f"""# 업로드 검수 체크리스트 — ep01

생성: {datetime.now(timezone.utc).isoformat()}

## 파일
- [ ] 영상: `{dest_video.name}`
- [ ] 자막: `subtitles-ko.srt` (선택 업로드)
- [ ] 제목: TITLE.txt
- [ ] 설명: DESCRIPTION.txt (챕터 포함)
- [ ] 태그: TAGS.txt

## 재생 검수
- [ ] 오프닝 저작권·면책 고지 들림
- [ ] 여성 나레이션 / 말씀 보이스 구분 명확
- [ ] 구절 인용 어색한 끊김 없음
- [ ] 엔딩 면책·소프트 CTA
- [ ] 유닛 사이 침묵 패드 자연스러움 (100분본)

## 정책
- [ ] 개역개정 미사용 확인
- [ ] 의료 대체 주장 없음
- [ ] 제목에 분량 표기 일치

## 경로
영상 원본: `{final}`
패키지: `{pkg}`
"""
    (pkg / "CHECKLIST.md").write_text(checklist, encoding="utf-8")
    (pkg / "README.md").write_text(
        f"# upload_package\n\n- video: `{dest_video.name}`\n- paste TITLE/DESCRIPTION/TAGS into YouTube\n- follow CHECKLIST.md\n",
        encoding="utf-8",
    )
    print(json.dumps({"ok": True, "pkg": str(pkg), "video": str(dest_video), "title": title}, ensure_ascii=False))


if __name__ == "__main__":
    main()
