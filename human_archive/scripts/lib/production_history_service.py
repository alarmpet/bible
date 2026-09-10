# -*- coding: utf-8 -*-
"""Production History Service.

Single Source of Truth (SSOT) domain service for production video history cataloging,
metadata normalization, and active/archive run scanning.
"""
from __future__ import annotations

import datetime
import json
import logging
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger(__name__)

MODULE_ROOT = Path(r"D:\module")
DEFAULT_RUNS_DIR = MODULE_ROOT / "bible" / "human_archive" / "runs"
DEFAULT_DB_PATH = MODULE_ROOT / "bible" / "human_archive" / "data" / "production_video_history.json"


class ProductionHistoryService:
    """Domain service encapsulating production video catalog operations."""

    def __init__(
        self,
        *,
        history_db_path: Optional[Path] = None,
        runs_base_dir: Optional[Path] = None,
        get_current_ep_dir: Optional[Callable[[], Path]] = None,
    ):
        self.history_db_path = history_db_path or DEFAULT_DB_PATH
        self.runs_base_dir = runs_base_dir or DEFAULT_RUNS_DIR
        self._get_current_ep_dir = get_current_ep_dir

    @property
    def current_ep_dir(self) -> Optional[Path]:
        if self._get_current_ep_dir is not None:
            try:
                p = self._get_current_ep_dir()
                if p and p.is_dir():
                    return p
            except Exception:
                return None
        return None

    def read_history_records(self) -> List[Dict[str, Any]]:
        """Read registered history records from JSON database."""
        if not self.history_db_path.exists():
            return []
        try:
            data = json.loads(self.history_db_path.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except (OSError, json.JSONDecodeError) as e:
            logger.warning(f"Error reading history database {self.history_db_path}: {e}")
            return []

    def register_video(self, entry: Dict[str, Any]) -> None:
        """Atomically register a video entry to history database preventing duplicates."""
        self.history_db_path.parent.mkdir(parents=True, exist_ok=True)
        records = self.read_history_records()

        # Deduplicate by filename or video_id
        target_name = entry.get("filename") or Path(entry.get("file_path", "")).name
        target_id = entry.get("video_id")
        records = [
            r for r in records
            if r.get("filename") != target_name and r.get("video_id") != target_id
        ]
        records.insert(0, entry)

        temp_db = self.history_db_path.with_suffix(".tmp")
        temp_db.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
        temp_db.replace(self.history_db_path)

        # Mirror to root workspace if accessible
        root_db = MODULE_ROOT / "production_video_history.json"
        try:
            root_db.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError:
            pass

    def collect_projects(self) -> List[Dict[str, Any]]:
        """Collect and normalize completed video projects from DB and physical run folders."""
        projects: List[Dict[str, Any]] = []
        seen_paths: Set[str] = set()

        # 1. Registered database records (Highest priority SSOT)
        for record in self.read_history_records():
            path_str = record.get("absolute_path") or record.get("file_path", "")
            path = Path(path_str)
            if not path.is_file() or str(path) in seen_paths:
                continue
            seen_paths.add(str(path))

            vid_id = record.get("video_id") or path.stem
            title = record.get("title") or path.stem
            dur_sec = float(record.get("duration_sec", 0.0))
            dur_str = record.get("formatted_duration") or (
                f"{int(dur_sec // 60):02d}:{int(dur_sec % 60):02d}" if dur_sec > 0 else ""
            )

            projects.append({
                "video_id": vid_id,
                "title": title,
                "episode_code": f"NOLLAM-{path.stem.upper()[:24]}",
                "variant": record.get("variant", "등록된 프로덕션 마스터"),
                "duration_str": dur_str,
                "duration_sec": dur_sec,
                "file_path": str(path),
                "file_name": path.name,
                "file_size_mb": record.get(
                    "file_size_mb",
                    round(path.stat().st_size / (1024 * 1024), 2)
                ),
                "date_created": record.get(
                    "created_at",
                    datetime.datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
                ),
                "status": record.get("status", "MASTER_COMPLETED"),
                "badge_color": record.get("badge_color", "emerald"),
                "is_current": True,
                "description": record.get("description", "등록된 프로덕션 영상"),
            })

        # 2. Dynamic Run Directories Scan
        episodes_to_scan: List[Path] = []
        active_ep = self.current_ep_dir
        if active_ep and active_ep.is_dir():
            episodes_to_scan.append(active_ep)

        if self.runs_base_dir.is_dir():
            # Scan nollam_file hierarchy (YYYY-MM-DD/slug)
            nollam_root = self.runs_base_dir / "nollam_file"
            if nollam_root.is_dir():
                for ep_cand in sorted(nollam_root.glob("*/*"), reverse=True):
                    if ep_cand.is_dir() and ep_cand not in episodes_to_scan:
                        episodes_to_scan.append(ep_cand)
            # Scan top-level run dirs
            for ep_cand in sorted(self.runs_base_dir.glob("*"), reverse=True):
                if ep_cand.is_dir() and ep_cand not in episodes_to_scan and ep_cand.name != "nollam_file":
                    episodes_to_scan.append(ep_cand)

        for ep in episodes_to_scan:
            for folder in (ep, ep / "output", ep / "candidate", ep / "generation"):
                if not folder.is_dir():
                    continue
                for path in sorted(folder.glob("*.mp4"), key=lambda item: item.stat().st_mtime, reverse=True):
                    name = path.name.lower()
                    if not path.is_file() or str(path) in seen_paths:
                        continue
                    if any(token in name for token in (".part", "assembled", "motion", "visual", "raw", "clip")):
                        continue

                    seen_paths.add(str(path))
                    is_pilot = "pilot" in name or "perfect" in name
                    is_active = (ep == active_ep)

                    # Extract metadata from manifest if available
                    dur_sec = 0.0
                    dur_str = ""
                    title = ep.name
                    desc = f"{ep.name} 에피소드 렌더링 산출물"

                    manifest_p = ep / "generation" / "master_1200s_manifest.json"
                    if manifest_p.exists():
                        try:
                            m_data = json.loads(manifest_p.read_text(encoding="utf-8"))
                            title = m_data.get("title") or m_data.get("metadata", {}).get("title") or title
                            dur_sec = float(m_data.get("total_duration") or m_data.get("total_duration_sec") or 0.0)
                            if dur_sec > 0:
                                dur_str = f"{int(dur_sec // 60):02d}:{int(dur_sec % 60):02d} ({dur_sec:.1f}s)"
                        except Exception:
                            pass

                    projects.append({
                        "video_id": f"{ep.name}-{path.stem}",
                        "title": title,
                        "episode_code": f"NOLLAM-{ep.name.upper()[:24]}",
                        "variant": "파일럿 비디오" if is_pilot else "마스터 다큐멘터리",
                        "duration_str": dur_str,
                        "duration_sec": dur_sec,
                        "file_path": str(path),
                        "file_name": path.name,
                        "file_size_mb": round(path.stat().st_size / (1024 * 1024), 2),
                        "date_created": datetime.datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M"),
                        "status": "PILOT_COMPLETED" if is_pilot else "MASTER_COMPLETED",
                        "badge_color": "purple" if is_pilot else "emerald",
                        "is_current": is_active,
                        "description": desc,
                    })

        projects.sort(
            key=lambda item: (1 if item.get("is_current") else 0, item.get("date_created", "")),
            reverse=True
        )
        return projects

    def get_video(self, video_id: str) -> Optional[Dict[str, Any]]:
        """Find single video metadata by video_id."""
        for p in self.collect_projects():
            if p.get("video_id") == video_id:
                return p
        return None
