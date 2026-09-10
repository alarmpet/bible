"""Media streaming routes for the NOLLAM studio."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Callable, Iterator

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse


def _stream_file(path: Path, request: Request, media_type: str) -> StreamingResponse:
    file_size = path.stat().st_size
    range_header = request.headers.get("range")
    range_match = re.fullmatch(r"bytes=(\d+)-(\d*)", range_header or "")

    if range_match:
        start = int(range_match.group(1))
        end = int(range_match.group(2)) if range_match.group(2) else file_size - 1
        if start >= file_size or start > end:
            return StreamingResponse(
                iter(()),
                status_code=416,
                headers={"Content-Range": f"bytes */{file_size}"},
                media_type=media_type,
            )
        end = min(end, file_size - 1)
        chunk_size = end - start + 1

        def iter_chunk() -> Iterator[bytes]:
            with path.open("rb") as source:
                source.seek(start)
                remaining = chunk_size
                while remaining > 0:
                    data = source.read(min(128 * 1024, remaining))
                    if not data:
                        break
                    remaining -= len(data)
                    yield data

        return StreamingResponse(
            iter_chunk(),
            status_code=206,
            headers={
                "Content-Range": f"bytes {start}-{end}/{file_size}",
                "Accept-Ranges": "bytes",
                "Content-Length": str(chunk_size),
                "Content-Type": media_type,
            },
        )

    def iter_full() -> Iterator[bytes]:
        with path.open("rb") as source:
            while chunk := source.read(128 * 1024):
                yield chunk

    return StreamingResponse(
        iter_full(),
        status_code=200,
        headers={
            "Accept-Ranges": "bytes",
            "Content-Length": str(file_size),
            "Content-Type": media_type,
        },
    )


def create_media_router(
    *,
    get_current_ep_dir: Callable[[], Path],
    get_manifest_path: Callable[[], Path],
    fallback_manifest_path: Path,
    history_db_path: Path,
    final_master_path: Path,
    canonical_master_path: Path,
) -> APIRouter:
    """Create master, thumbnail, and narration media routes."""
    router = APIRouter(prefix="/api/media", tags=["media"])

    def resolve_manifest_path() -> Path:
        active_path = get_manifest_path()
        return active_path if active_path.exists() else fallback_manifest_path

    def read_manifest(path: Path) -> dict[str, Any]:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}

    @router.get("/master_video")
    async def stream_master_video(request: Request) -> StreamingResponse:
        target_video: Path | None = None
        if history_db_path.exists():
            records = read_manifest(history_db_path)
            if isinstance(records, list) and records:
                candidate = Path(records[0].get("absolute_path", ""))
                if candidate.exists() and candidate.is_file():
                    target_video = candidate

        active_ep = get_current_ep_dir()
        if target_video is None and active_ep and active_ep.exists():
            for candidate in (
                active_ep / "NOLLAM-SAN-JOSE-GALLEON-MASTER.mp4",
                active_ep / "candidate" / "NOLLAM-SAN-JOSE-GALLEON-MASTER.mp4",
                active_ep / "output" / "NOLLAM-SAN-JOSE-GALLEON-MASTER.mp4",
            ):
                if candidate.exists():
                    target_video = candidate
                    break
            if target_video is None:
                for folder in (active_ep / "output", active_ep / "candidate", active_ep):
                    if not folder.exists():
                        continue
                    candidates = sorted(
                        folder.glob("*.mp4"),
                        key=lambda item: item.stat().st_mtime,
                        reverse=True,
                    )
                    target_video = next(
                        (
                            candidate
                            for candidate in candidates
                            if not candidate.name.endswith(".part")
                            and "raw" not in candidate.name.lower()
                            and "clip" not in candidate.name.lower()
                        ),
                        None,
                    )
                    if target_video is not None:
                        break

        if target_video is None:
            target_video = final_master_path if final_master_path.exists() else canonical_master_path
        if not target_video.exists() or not target_video.is_file():
            raise HTTPException(status_code=404, detail="마스터 비디오 파일을 찾을 수 없습니다.")
        return _stream_file(target_video, request, "video/mp4")

    @router.get("/thumbnail/{shot_id}")
    async def get_shot_thumbnail(shot_id: str) -> FileResponse:
        active_ep = get_current_ep_dir()
        for base_dir in (
            active_ep / "generation" / "downloads" / "approved",
            active_ep / "images",
        ):
            for extension in (".jpg", ".jpeg", ".png"):
                path = base_dir / f"{shot_id}{extension}"
                if path.exists() and path.stat().st_size > 0:
                    media_type = "image/jpeg" if extension in (".jpg", ".jpeg") else "image/png"
                    return FileResponse(path, media_type=media_type)
            matches = list(base_dir.glob(f"{shot_id}__*.*"))
            if matches and matches[0].exists() and matches[0].stat().st_size > 0:
                media_type = "image/jpeg" if matches[0].suffix.lower() in (".jpg", ".jpeg") else "image/png"
                return FileResponse(matches[0], media_type=media_type)

        approved_manifest = active_ep / "generation" / "approved_asset_manifest.json"
        if approved_manifest.exists():
            data = read_manifest(approved_manifest)
            for asset in data.get("assets", []):
                if asset.get("shot_id") == shot_id or asset.get("scene_id") == shot_id:
                    path = Path(asset.get("file_path", ""))
                    if path.exists() and path.stat().st_size > 0:
                        media_type = "image/jpeg" if path.suffix.lower() in (".jpg", ".jpeg") else "image/png"
                        return FileResponse(path, media_type=media_type)

        manifest_path = resolve_manifest_path()
        if manifest_path.exists():
            data = read_manifest(manifest_path)
            shot = next(
                (
                    item
                    for item in data.get("shots", [])
                    if item.get("shot_id") == shot_id or item.get("scene_id") == shot_id
                ),
                None,
            )
            if shot:
                path = Path(shot.get("image_path", ""))
                if path.exists() and path.stat().st_size > 0:
                    media_type = "image/jpeg" if path.suffix.lower() in (".jpg", ".jpeg") else "image/png"
                    return FileResponse(path, media_type=media_type)
        raise HTTPException(status_code=404, detail=f"이미지 파일 없음: {shot_id}")

    @router.get("/audio/{shot_id}")
    async def get_shot_audio(shot_id: str) -> FileResponse:
        manifest_path = resolve_manifest_path()
        shot = None
        if manifest_path.exists():
            data = read_manifest(manifest_path)
            shot = next(
                (
                    item
                    for item in data.get("shots", [])
                    if item.get("shot_id") == shot_id or item.get("scene_id") == shot_id
                ),
                None,
            )

        candidates = []
        if shot and shot.get("wav_path"):
            candidates.append(Path(shot["wav_path"]))
        active_ep = get_current_ep_dir()
        candidates.extend(
            [
                active_ep / "audio" / "sentences_v4" / f"{shot_id}.wav",
                active_ep / "audio" / "sentences" / f"{shot_id}.wav",
                fallback_manifest_path.parent.parent / "audio" / "sentences_v4" / f"{shot_id}.wav",
                fallback_manifest_path.parent.parent / "audio" / "sentences" / f"{shot_id}.wav",
            ]
        )
        for path in candidates:
            if path.exists() and path.stat().st_size > 0:
                return FileResponse(path, media_type="audio/wav", headers={"Accept-Ranges": "bytes"})
        raise HTTPException(status_code=404, detail=f"오디오 파일 없음: {shot_id}")

    return router
