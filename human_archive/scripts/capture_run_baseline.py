# -*- coding: utf-8 -*-
"""Capture and verify immutable inventory baseline for documentary runs."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def compute_file_sha256(path: Path) -> str:
    """Compute SHA-256 hash of a file efficiently."""
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest().upper()


def get_git_info(cwd: Path) -> tuple[str, bool]:
    """Get current git HEAD hash and dirty state if git is available."""
    try:
        head_res = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True,
        )
        git_head = head_res.stdout.strip()

        status_res = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True,
        )
        is_dirty = bool(status_res.stdout.strip())
        return git_head, is_dirty
    except Exception:
        return "UNKNOWN", False


def probe_media_file(path: Path) -> dict[str, Any]:
    """Extract stream, codec, and duration metadata using ffprobe."""
    try:
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_format",
            "-show_streams",
            "-of", "json",
            str(path),
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(res.stdout)
        fmt = data.get("format", {})
        streams = data.get("streams", [])
        return {
            "duration_sec": float(fmt.get("duration", 0.0)),
            "size_bytes": int(fmt.get("size", path.stat().st_size)),
            "bit_rate": int(fmt.get("bit_rate", 0)),
            "streams": [
                {
                    "index": s.get("index"),
                    "codec_type": s.get("codec_type"),
                    "codec_name": s.get("codec_name"),
                    "width": s.get("width"),
                    "height": s.get("height"),
                    "sample_aspect_ratio": s.get("sample_aspect_ratio"),
                    "display_aspect_ratio": s.get("display_aspect_ratio"),
                    "r_frame_rate": s.get("r_frame_rate"),
                    "avg_frame_rate": s.get("avg_frame_rate"),
                    "pix_fmt": s.get("pix_fmt"),
                    "sample_rate": s.get("sample_rate"),
                    "channels": s.get("channels"),
                }
                for s in streams
            ],
        }
    except Exception as e:
        return {"error": str(e), "size_bytes": path.stat().st_size if path.exists() else 0}


def build_dir_inventory(root_dir: Path, exclude_patterns: list[str] | None = None) -> list[dict[str, Any]]:
    """Build detailed file inventory recursively for a directory."""
    root_dir = root_dir.resolve()
    if not root_dir.exists():
        return []

    excludes = exclude_patterns or [".audit_*", "__pycache__", "*.pyc", "*.tmp", "*.part"]
    inventory: list[dict[str, Any]] = []

    for path in sorted(root_dir.rglob("*")):
        if path.is_file():
            # Check exclusions
            rel = path.relative_to(root_dir).as_posix()
            if any(path.match(p) for p in excludes):
                continue
            if "__pycache__" in rel:
                continue

            stat = path.stat()
            mtime_utc = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()
            sha256 = compute_file_sha256(path)
            inventory.append({
                "relative_path": rel,
                "bytes": stat.st_size,
                "sha256": sha256,
                "mtime_utc": mtime_utc,
            })

    return inventory


def capture_baseline(
    run_root: Path,
    code_roots: list[Path],
    output_path: Path,
    final_media_name: str = "final_pompeii_ep01.mp4",
) -> dict[str, Any]:
    """Capture full recursive baseline without mutating source directory."""
    run_root = run_root.resolve()
    output_path = output_path.resolve()

    # Disallow writing baseline inside run_root to prevent mutating target
    try:
        output_path.relative_to(run_root)
        raise ValueError(f"Output path cannot be inside the run root: {output_path}")
    except ValueError as e:
        if "cannot be inside" in str(e):
            raise
        # Outside run_root is valid

    git_head, git_dirty = get_git_info(run_root)

    run_inv = build_dir_inventory(run_root)
    total_bytes = sum(item["bytes"] for item in run_inv)

    code_inventories: dict[str, list[dict[str, Any]]] = {}
    for c_root in code_roots:
        c_root_resolved = c_root.resolve()
        code_inventories[c_root.name] = build_dir_inventory(c_root_resolved)

    # Check final media file if present
    final_media_path = run_root / final_media_name
    final_info: dict[str, Any] = {}
    if final_media_path.exists():
        final_sha = compute_file_sha256(final_media_path)
        meta = probe_media_file(final_media_path)
        final_info = {
            "path": final_media_name,
            "sha256": final_sha,
            "bytes": final_media_path.stat().st_size,
            "metadata": meta,
        }

    baseline_data = {
        "schema_version": 1,
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "git_head": git_head,
        "working_tree_dirty": git_dirty,
        "run_root": str(run_root),
        "run_root_summary": {
            "total_files": len(run_inv),
            "total_bytes": total_bytes,
        },
        "final_media_info": final_info,
        "run_inventory": run_inv,
        "code_inventories": code_inventories,
    }

    # Write atomically
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temp_file = output_path.parent / f".tmp_{output_path.name}_{os.getpid()}"
    temp_file.write_text(json.dumps(baseline_data, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(temp_file, output_path)

    return baseline_data


def verify_baseline(
    run_root: Path,
    code_roots: list[Path],
    baseline_file: Path,
) -> bool:
    """Verify that current directory state exactly matches recorded baseline."""
    baseline_file = baseline_file.resolve()
    if not baseline_file.exists():
        print(f"❌ Baseline file not found: {baseline_file}")
        return False

    baseline_data = json.loads(baseline_file.read_text(encoding="utf-8"))
    recorded_inv = {item["relative_path"]: item for item in baseline_data.get("run_inventory", [])}

    current_inv = {item["relative_path"]: item for item in build_dir_inventory(run_root)}

    all_matched = True
    missing_keys = set(recorded_inv.keys()) - set(current_inv.keys())
    added_keys = set(current_inv.keys()) - set(recorded_inv.keys())

    if missing_keys:
        all_matched = False
        print(f"❌ Missing files ({len(missing_keys)}): {sorted(missing_keys)[:5]}")

    if added_keys:
        all_matched = False
        print(f"❌ Unexpected added files ({len(added_keys)}): {sorted(added_keys)[:5]}")

    for k in recorded_inv.keys() & current_inv.keys():
        rec_item = recorded_inv[k]
        cur_item = current_inv[k]
        if rec_item["sha256"] != cur_item["sha256"] or rec_item["bytes"] != cur_item["bytes"]:
            all_matched = False
            print(f"❌ Modified file: {k} (Recorded SHA: {rec_item['sha256'][:8]}, Current SHA: {cur_item['sha256'][:8]})")

    return all_matched


def main():
    parser = argparse.ArgumentParser(description="Capture or verify baseline of run directories")
    parser.add_argument("--run-root", required=True, type=Path, help="Path to run root directory")
    parser.add_argument("--code-root", action="append", type=Path, default=[], help="Paths to code/config roots")
    parser.add_argument("--config-root", type=Path, help="Optional config root")
    parser.add_argument("--template-root", type=Path, help="Optional template root")
    parser.add_argument("--output", type=Path, help="Output path for baseline JSON")
    parser.add_argument("--verify-against", type=Path, help="Baseline JSON to verify against")
    args = parser.parse_args()

    code_roots: list[Path] = list(args.code_root)
    if args.config_root:
        code_roots.append(args.config_root)
    if args.template_root:
        code_roots.append(args.template_root)

    if args.verify_against:
        ok = verify_baseline(args.run_root, code_roots, args.verify_against)
        sys.exit(0 if ok else 1)

    if not args.output:
        parser.error("--output is required when capturing baseline")

    data = capture_baseline(args.run_root, code_roots, args.output)
    print(f"✅ Baseline successfully captured to {args.output}")
    print(f"   Total run files: {data['run_root_summary']['total_files']}")
    print(f"   Total run bytes: {data['run_root_summary']['total_bytes']:,}")
    if data["final_media_info"]:
        print(f"   Final Media SHA-256: {data['final_media_info']['sha256']}")


if __name__ == "__main__":
    main()
