# -*- coding: utf-8 -*-
"""Download public-domain Korean Bible OSIS from open-bibles."""
from __future__ import annotations

import hashlib
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from paths_bh import RAW, DATA

DEFAULT_URL = (
    "https://raw.githubusercontent.com/seven1m/open-bibles/master/kor-korean.osis.xml"
)
OUT_NAME = "kor-korean.osis.xml"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    out = RAW / OUT_NAME
    url = DEFAULT_URL
    print(f"Downloading {url}")
    req = urllib.request.Request(url, headers={"User-Agent": "bible-healing-pipeline/1.0"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = resp.read()
    out.write_bytes(data)
    digest = sha256_file(out)
    prov = {
        "downloaded_at": datetime.now(timezone.utc).isoformat(),
        "url": url,
        "filename": OUT_NAME,
        "bytes": len(data),
        "sha256": digest,
        "translation_id": "KRV",
        "repo": "https://github.com/seven1m/open-bibles",
        "license_note": "Public domain Korean Bible text as packaged by open-bibles",
    }
    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / "provenance.json").write_text(
        json.dumps(prov, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"OK {out} ({len(data)} bytes) sha256={digest[:16]}...")


if __name__ == "__main__":
    main()
