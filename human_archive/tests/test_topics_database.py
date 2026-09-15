# -*- coding: utf-8 -*-
"""Test historical topics database and strict deduplication governance."""
from __future__ import annotations

import json
import sys
from pathlib import Path
import pytest

_TEST_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _TEST_DIR.parents[1]
_SCRIPTS_DIR = _PROJECT_ROOT / "human_archive" / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from lib.topics_inventory import (
    init_topics_db,
    import_topics_from_catalog,
    get_available_topics,
    reserve_topic,
    commit_topic_as_used,
    release_topic_reservation,
    get_topic_detail,
)


@pytest.fixture
def temp_db(tmp_path: Path) -> Path:
    db_path = tmp_path / "test_topics.sqlite3"
    init_topics_db(db_path)
    return db_path


@pytest.fixture
def seed_catalog(tmp_path: Path) -> Path:
    catalog_path = tmp_path / "test_catalog.json"
    data = {
        "schema_version": 1,
        "topics": [
            {
                "topic_id": "TOPIC-COBRA-001",
                "title": "영국 총독부의 코브라 효과",
                "theme": "paradox",
                "historical_period": "19세기 영국령 인도 제국",
                "core_hook": "코브라 잡으라고 포상금 줬더니 뱀 양식장을 차렸다?",
                "primary_sources": ["영국령 델리 행정관 보고서"],
                "modern_analogy": "쥐 잡으라고 지원금 줬더니 안방에 쥐 양식장 차린 꼴이지요.",
                "humanistic_insight": "선한 의도가 낳은 최악의 정책 실패와 인간의 탐욕.",
                "target_duration_sec": 1200,
                "status": "AVAILABLE",
            },
            {
                "topic_id": "TOPIC-PIGWAR-001",
                "title": "돼지 한 마리 때문에 터진 영-미 전쟁",
                "theme": "paradox",
                "historical_period": "1859년 산후안 섬",
                "core_hook": "감자 먹은 돼지 한 마리 때문에 양국 함대가 대포를 겨눴다?",
                "primary_sources": ["산후안 분쟁 공식 군사 기록"],
                "modern_analogy": "마당 감자 먹은 돼지 때문에 동네 싸움이 대형 소송전으로 번진 격이지요.",
                "humanistic_insight": "국가적 자존심과 관료주의가 만든 희극적 비극.",
                "target_duration_sec": 1200,
                "status": "AVAILABLE",
            },
        ],
    }
    catalog_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return catalog_path


def test_import_and_query_available_topics(temp_db, seed_catalog):
    import_topics_from_catalog(seed_catalog, temp_db)
    available = get_available_topics(temp_db)
    assert len(available) == 2
    assert available[0]["topic_id"] == "TOPIC-COBRA-001"


def test_reserve_and_reject_duplicate_usage(temp_db, seed_catalog):
    import_topics_from_catalog(seed_catalog, temp_db)

    # 1. First reservation succeeds
    reserve_topic(temp_db, "TOPIC-COBRA-001", "HA002")
    detail = get_topic_detail(temp_db, "TOPIC-COBRA-001")
    assert detail["status"] == "RESERVED"
    assert detail["used_in_episode_id"] == "HA002"

    # 2. Reserving already RESERVED topic raises ValueError
    with pytest.raises(ValueError, match="already in progress"):
        reserve_topic(temp_db, "TOPIC-COBRA-001", "HA003")

    # 3. Available list no longer contains the reserved topic
    available = get_available_topics(temp_db)
    assert len(available) == 1
    assert available[0]["topic_id"] == "TOPIC-PIGWAR-001"

    # 4. Release reservation allows it back to AVAILABLE
    release_topic_reservation(temp_db, "TOPIC-COBRA-001")
    assert len(get_available_topics(temp_db)) == 2


def test_commit_as_used_permanently_blocks_reusage(temp_db, seed_catalog):
    import_topics_from_catalog(seed_catalog, temp_db)

    # 1. Commit as used for episode HA002
    reserve_topic(temp_db, "TOPIC-COBRA-001", "HA002")
    commit_topic_as_used(temp_db, "TOPIC-COBRA-001", "HA002")

    detail = get_topic_detail(temp_db, "TOPIC-COBRA-001")
    assert detail["status"] == "USED"
    assert detail["used_in_episode_id"] == "HA002"
    assert detail["used_at_utc"] is not None

    # 2. Attempting to reserve or commit again raises ValueError
    with pytest.raises(ValueError, match="has already been used"):
        reserve_topic(temp_db, "TOPIC-COBRA-001", "HA003")

    # 3. Release attempt on USED topic is forbidden
    with pytest.raises(ValueError, match="Cannot release completed USED topic"):
        release_topic_reservation(temp_db, "TOPIC-COBRA-001")
