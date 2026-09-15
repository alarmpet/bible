# -*- coding: utf-8 -*-
"""SPARC Documentary Production Pipeline Engine.
Inspired by Ruflo's SPARC (Specification -> Pseudocode -> Architecture -> Refinement -> Completion)
methodology, providing structured, defect-free, test-driven documentary production.
"""
from __future__ import annotations

import datetime
import json
import sys
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SCRIPTS_DIR = Path(r"D:\module\bible\human_archive\scripts")
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from historical_agentdb_memory import HistoricalAgentDBMemory
from historical_parallel_engine import HistoricalParallelEngine
from sentence_fact_checker import SentenceHistoricalFactChecker


class SPARCDocumentaryPipeline:
    """Orchestrates 5-stage SPARC methodology tailored strictly for 20-minute master documentaries."""

    def __init__(self, ep_dir: Optional[Path] = None):
        self.ep_dir = ep_dir
        self.memory = HistoricalAgentDBMemory()
        self.narrative_engine = HistoricalParallelEngine()
        self.fact_checker = SentenceHistoricalFactChecker()

    def execute_sparc_cycle(
        self,
        topic: Dict[str, Any],
        ep_dir: Optional[Path] = None,
        target_duration_sec: Optional[float] = 1200.0,
        custom_sentences: Optional[List[str]] = None,
        target_shots: Optional[int] = None,
        on_event: Optional[Callable[[Dict[str, Any]], None]] = None
    ) -> Dict[str, Any]:
        """Execute full 5-stage SPARC cycle: Spec -> Pseudo -> Arch -> Refine -> Complete."""
        def emit(evt: Dict[str, Any]):
            if on_event:
                on_event(evt)

        work_ep_dir = ep_dir or self.ep_dir
        if not work_ep_dir:
            today_str = datetime.date.today().strftime("%Y-%m-%d")
            slug = topic.get("topic_id", "EPISODE").lower().replace("topic-", "")
            work_ep_dir = Path(r"D:\module\bible\human_archive\runs\nollam_file") / today_str / slug

        audit_dir = work_ep_dir / "audit"
        gen_dir = work_ep_dir / "generation"
        src_dir = work_ep_dir / "source"
        cand_dir = work_ep_dir / "candidate"
        for d in [audit_dir, gen_dir, src_dir, cand_dir, gen_dir / "downloads" / "approved", work_ep_dir / "audio" / "sentences_v4"]:
            d.mkdir(parents=True, exist_ok=True)

        topic_title = topic.get("title", "역사 및 과학 다큐멘터리")

        # ---------------------------------------------------------------------
        # [STAGE 1] S: SPECIFICATION
        # ---------------------------------------------------------------------
        emit({
            "type": "sparc_stage_start",
            "stage": "S",
            "stage_name": "Specification",
            "title": "[SPARC S] 기획 명세 수립 & AgentDB 1차 사료 검색",
            "progress": 20
        })
        time.sleep(0.3)

        # Query AgentDB for best matching parallel archetype and academic sources
        parallel_match = self.memory.query_parallel(topic_title)
        primary_sources = self.memory.query_primary_sources(topic_title, top_k=3)

        spec = {
            "title": topic_title,
            "target_duration_sec": target_duration_sec,
            "parallel_pair_id": parallel_match["pair_id"],
            "historical_parallel": parallel_match["historical_parallel"],
            "protagonist": parallel_match["protagonist"],
            "time_space_anchor": parallel_match["time_space_anchor"],
            "core_hook": parallel_match["core_hook"],
            "modern_lesson": parallel_match["modern_lesson"],
            "primary_sources": primary_sources,
            "target_shots": target_shots
        }
        (audit_dir / "sparc_stage1_specification.json").write_text(
            json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        emit({"type": "sparc_spec_ready", "spec": spec})

        # ---------------------------------------------------------------------
        # [STAGE 2] P: PSEUDOCODE (NARRATIVE OUTLINE)
        # ---------------------------------------------------------------------
        emit({
            "type": "sparc_stage_start",
            "stage": "P",
            "stage_name": "Pseudocode",
            "title": "[SPARC P] 5대 페이즈 서사 의사코드 & 감정선 설계",
            "progress": 40
        })
        time.sleep(0.3)

        narrative_arc = [
            {"phase": "phase_1_hook", "name": "콜드오픈 & 인지부조화 훅 (파일럿)", "target_pct": 15, "emotion": "경악과 호기심"},
            {"phase": "phase_2_origin", "name": "역사적 사건의 서막 & 황금기 번영", "target_pct": 20, "emotion": "경이로움과 매혹"},
            {"phase": "phase_3_crisis", "name": "기록의 충돌 & 시스템 붕괴의 서막", "target_pct": 30, "emotion": "긴장감과 위기"},
            {"phase": "phase_4_outcome", "name": "문명의 탈출 & 뼈아픈 역사의 결말", "target_pct": 20, "emotion": "참담함과 침묵"},
            {"phase": "phase_5_epilogue", "name": "현대로의 귀환 & 철학적 사이다 성찰", "target_pct": 15, "emotion": "깊은 여운과 지혜"}
        ]
        (audit_dir / "sparc_stage2_pseudocode.json").write_text(
            json.dumps(narrative_arc, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        emit({"type": "sparc_pseudocode_ready", "narrative_arc": narrative_arc})

        # ---------------------------------------------------------------------
        # [STAGE 3] A: ARCHITECTURE (DYNAMIC SHOTS & TIMELINE)
        # ---------------------------------------------------------------------
        emit({
            "type": "sparc_stage_start",
            "stage": "A",
            "stage_name": "Architecture",
            "title": "[SPARC A] 대본 연동 유동적 씬 매니페스트 & 샷스케일 결합",
            "progress": 60
        })
        time.sleep(0.4)

        base_manifest = self.narrative_engine.generate_dynamic_script(
            parallel_data=parallel_match,
            ep_dir=work_ep_dir,
            target_duration_sec=target_duration_sec,
            custom_sentences=custom_sentences,
            target_shots=target_shots
        )
        raw_shots = base_manifest["shots"]
        total_shots = len(raw_shots)

        (audit_dir / "sparc_stage3_architecture.json").write_text(
            json.dumps({"total_shots": total_shots, "total_duration_sec": base_manifest["total_duration_sec"]}, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        emit({"type": "sparc_architecture_ready", "total_shots": total_shots, "duration": base_manifest["total_duration_sec"]})

        # ---------------------------------------------------------------------
        # [STAGE 4] R: REFINEMENT (4-TIER FACT-CHECKING & RETOUCH)
        # ---------------------------------------------------------------------
        emit({
            "type": "sparc_stage_start",
            "stage": "R",
            "stage_name": "Refinement",
            "title": f"[SPARC R] 문장별 4단계 팩트체크(A/B/C/D) 전수 진단 & 퇴고 ({total_shots}개 샷)",
            "progress": 80
        })
        time.sleep(0.4)

        refined_shots = []
        fact_stats = {"A": 0, "B": 0, "C": 0, "D": 0}
        for s in raw_shots:
            orig = s["display_text"]
            res = self.fact_checker.audit_sentence(orig)
            grade = res["grade"]
            fact_stats[grade] = fact_stats.get(grade, 0) + 1

            revised = orig
            if grade == "C":
                revised = res.get("revised_text") or orig
            elif grade == "B":
                revised = res.get("revised_text") or orig
            elif grade == "D":
                revised = res.get("deep_alternative") or orig

            s_copy = dict(s)
            s_copy["display_text"] = revised
            s_copy["tts_text"] = revised
            s_copy["factcheck_grade"] = grade
            s_copy["factcheck_status"] = res.get("status")
            s_copy["primary_source"] = res.get("primary_source")
            refined_shots.append(s_copy)

        (audit_dir / "sparc_stage4_refinement.json").write_text(
            json.dumps({"statistics": fact_stats, "sample": refined_shots[:3]}, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        emit({"type": "sparc_refinement_ready", "statistics": fact_stats})

        # ---------------------------------------------------------------------
        # [STAGE 5] C: COMPLETION (DUAL-GATE MANIFEST & PERSISTENCE)
        # ---------------------------------------------------------------------
        emit({
            "type": "sparc_stage_start",
            "stage": "C",
            "stage_name": "Completion",
            "title": "[SPARC C] 최종 물리 매니페스트 배포 & AgentDB 궤적 등록",
            "progress": 95
        })
        time.sleep(0.4)

        shot_scale_counts = {"extreme_wide": 0, "medium_action": 0, "macro_close_up": 0, "top_down_insert": 0}
        for s in refined_shots:
            sc = s.get("shot_size", "medium_action")
            shot_scale_counts[sc] = shot_scale_counts.get(sc, 0) + 1

        final_manifest = {
            "metadata": {
                "channel": "역사이다 (History-Ida)",
                "title": topic_title,
                "topic_id": topic.get("topic_id", "TOPIC-SPARC-MASTER"),
                "historical_parallel": parallel_match["historical_parallel"],
                "protagonist": parallel_match["protagonist"],
                "core_hook": parallel_match["core_hook"],
                "modern_lesson": parallel_match["modern_lesson"],
                "primary_sources": parallel_match.get("primary_sources", []),
                "orchestration_type": "RUFLO_SPARC_5_STAGES",
                "factcheck_stats": fact_stats,
                "shot_scale_stats": shot_scale_counts,
                "generated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            },
            "total_duration_sec": base_manifest["total_duration_sec"],
            "total_shots": len(refined_shots),
            "pilot_shots_count": sum(1 for s in refined_shots if s.get("is_pilot")),
            "body_shots_count": len(refined_shots) - sum(1 for s in refined_shots if s.get("is_pilot")),
            "shots": refined_shots
        }

        # 1. master_1200s_manifest.json
        (gen_dir / "master_1200s_manifest.json").write_text(
            json.dumps(final_manifest, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        # 2. scene_script_manifest_v2.json
        v2_scenes = [{
            "scene_id": s["shot_id"],
            "order": s["order"],
            "duration_sec": s["scene_duration"],
            "narration": s["display_text"],
            "tts_text": s["tts_text"],
            "phase": s["phase"],
            "phase_label": s["phase_label"],
            "camera_motion": s["camera_motion"],
            "shot_size": s.get("shot_size"),
            "visual_prompt": s.get("visual_prompt", "")
        } for s in refined_shots]
        (src_dir / "scene_script_manifest_v2.json").write_text(
            json.dumps({"scenes": v2_scenes, "metadata": final_manifest["metadata"]}, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

        # 3. pilot_subtitles_1200s.ass (SSOT Semantic Subtitle Engine)
        from lib.semantic_subtitle_engine import SemanticSubtitleEngine
        sub_engine = SemanticSubtitleEngine(font_size=56, max_line_chars=24, max_clause_chars=40)
        sub_engine.compile_ass_subtitles(
            refined_shots,
            cand_dir / "pilot_subtitles_1200s.ass",
            title=f"History-Ida SPARC Master Subtitles - {topic_title}"
        )

        # 4. Record episode trajectory in AgentDB
        traj_id = self.memory.record_episode_trajectory(final_manifest, status="COMPLETED")

        emit({
            "type": "sparc_completed",
            "status": "SUCCESS",
            "message": f"🎉 Ruflo SPARC 5단계 다큐멘터리 제작 사이클 완료! (총 {len(refined_shots)}개 샷, {base_manifest['total_duration_sec']}초)",
            "trajectory_id": traj_id,
            "progress": 100
        })

        return final_manifest
