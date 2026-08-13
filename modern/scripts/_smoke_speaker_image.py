# -*- coding: utf-8 -*-
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from build_shot_plan_json import (
    guess_segments,
    refine_speakers,
    pick_image_for_narration,
    images_by_chapter,
)

tests = [
    '"한 씨, 오늘도 남아요?" 박경호 대리가 물었습니다.',
    '"페이퍼상으로는 이미 정리됐습니다." 시우가 말했습니다.',
    '"서로 좋게 갑시다." 기철이 웃으며 말했습니다.',
    '"일단 숫자부터 볼게요." 유진이 대답했습니다.',
    '"자리는 창가에서 두 칸 안쪽이에요."',
]
for t in tests:
    segs = refine_speakers(1, guess_segments(t), t)
    print(t[:50], "->", [(s["speaker"], s["text"][:28]) for s in segs])

imgs = images_by_chapter()[1]
samples = [
    "소회의실 형광등이 한 번 깜빡였습니다.",
    "테이블 위에는 퇴사 권고 봉투와 볼펜이 놓여 있었습니다.",
    "인천 남동 쪽 공단 길을 지나면 한빛물산이 있었습니다.",
    "한유진은 그해 서른한 살이었습니다.",
    "이시우 과장이 칸막이 너머로 얼굴을 내밀었습니다.",
]
prev = ""
print("--- images ---")
for n in samples:
    rel, title, how = pick_image_for_narration(n, imgs, prev)
    prev = rel
    print(how, Path(rel).name, "|", n[:36])
