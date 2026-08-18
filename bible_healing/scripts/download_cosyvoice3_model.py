# -*- coding: utf-8 -*-
"""Download Fun-CosyVoice3-0.5B-2512 to D:\\Fun-CosyVoice3\\pretrained_models."""
from __future__ import annotations

import time
from pathlib import Path

DEST = Path(r"D:\Fun-CosyVoice3\pretrained_models\Fun-CosyVoice3-0.5B")
REPO = "FunAudioLLM/Fun-CosyVoice3-0.5B-2512"


def main() -> int:
    DEST.parent.mkdir(parents=True, exist_ok=True)
    from huggingface_hub import snapshot_download

    last_error = None
    for attempt in range(1, 6):
        try:
            snapshot_download(
                REPO,
                local_dir=str(DEST),
                max_workers=1,
                resume_download=True,
            )
            print(f"model ok {DEST}")
            return 0
        except Exception as exc:
            last_error = exc
            wait = min(30, 5 * attempt)
            print(f"download attempt {attempt} failed: {type(exc).__name__}: {exc}")
            print(f"retry in {wait}s")
            time.sleep(wait)
    raise SystemExit(f"model download failed after retries: {last_error}")


if __name__ == "__main__":
    raise SystemExit(main())
