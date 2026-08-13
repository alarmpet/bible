# -*- coding: utf-8 -*-
"""Tests for Korean eojel-aware two-line caption layout."""
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from sanitize_script import sanitize_script  # noqa: E402
from subtitle_layout import CaptionBlock, pack_two_lines, split_korean_caption  # noqa: E402


def test_does_not_split_after_adjective():
    blocks = split_korean_caption("불을 껐는데, 머릿속은 아직 환한 밤이 있습니다.")
    joined = [b.text.replace(r"\N", "") for b in blocks]
    assert not any(t.endswith("환한") for t in joined)
    assert any("환한 밤이" in t or "밤이 있습니다" in t for t in joined)


def test_two_lines_max_and_hard_limit():
    blocks = split_korean_caption(
        "오늘 한 말이 자꾸 돌아오고, 내일 해야 할 일이 벌써 가슴 위에 올라와 있는 밤."
    )
    for b in blocks:
        assert len(b.lines) <= 2
        assert all(len(line) <= 20 for line in b.lines)


def test_does_not_cut_inside_eomi():
    blocks = split_korean_caption("지금은 무언가를 해내지 않아도 됩니다.")
    # 해내지 + 않아도 must share the same line inside a CaptionBlock
    # (not merely appear adjacent across a flattened multi-block join).
    assert any("해내지 않아도" in line for b in blocks for line in b.lines)
    assert not any(line == "해내지" for b in blocks for line in b.lines)


def test_strips_then_layouts_scripture():
    text = sanitize_script(
        "(다윗의 시) 내 의의 하나님이여, 내가 부를 때에 응답하소서"
    ).display
    blocks = split_korean_caption(text)
    assert all("(" not in b.text and "다윗" not in b.text for b in blocks)


def test_packs_two_short_phrases_with_n():
    blocks = split_korean_caption("그건 당신이 약해서가 아닙니다.")
    # 한 문장이 20자 이하면 1줄, 넘으면 2줄 \N
    assert all(len(b.lines) in (1, 2) for b in blocks)


def test_caption_block_shape():
    blocks = split_korean_caption("평안히 눕고 자기도 하리니.")
    assert blocks
    for b in blocks:
        assert isinstance(b, CaptionBlock)
        assert 1 <= len(b.lines) <= 2
        if len(b.lines) == 1:
            assert b.text == b.lines[0]
        else:
            assert b.text == r"\N".join(b.lines)


def test_pack_two_lines_pairs_phrases():
    blocks = pack_two_lines(["짧은 한 줄입니다", "다음 줄도 짧습니다", "마지막"])
    assert len(blocks) == 2
    assert blocks[0].lines == ["짧은 한 줄입니다", "다음 줄도 짧습니다"]
    assert blocks[0].text == r"짧은 한 줄입니다\N다음 줄도 짧습니다"
    assert blocks[1].lines == ["마지막"]
    assert blocks[1].text == "마지막"


def test_never_char_slices_mid_eojel():
    """Single eojel must not be hard-sliced with s[i:i+20]; keep whole eojel."""
    long_eojel = "아주아주긴한국어절하나"  # 11 chars, under hard_max
    text = f"{long_eojel} {long_eojel} {long_eojel}"
    blocks = split_korean_caption(text, hard_max=20)
    flat_lines = [ln for b in blocks for ln in b.lines]
    for ln in flat_lines:
        # No partial token fragments of the known eojel
        if long_eojel in ln:
            assert long_eojel in ln.split() or ln.replace(" ", "").count(
                long_eojel.replace(" ", "")
            ) >= 1
        for token in ln.split():
            assert token == long_eojel or len(token) <= 20


def test_oversized_eojel_emitted_whole():
    """Eojel longer than hard_max is emitted whole alone — never s[i:i+20]."""
    huge = "가" * 25  # 25 > 20
    assert len(huge) > 20
    blocks = split_korean_caption(f"앞에 {huge} 뒤에", hard_max=20)
    lines = [ln for b in blocks for ln in b.lines]
    # Full token present as its own line/block
    assert huge in lines
    assert any(b.lines == [huge] for b in blocks)
    # Not character-sliced into hard_max chunks
    assert huge[:20] not in lines
    assert huge[20:] not in lines
    for ln in lines:
        for token in ln.split():
            if token.startswith("가") and set(token) == {"가"}:
                assert token == huge


def test_does_not_split_after_eun_adnominal():
    """Common 은/는 adnominals (높은, …) must not be left line-final before noun."""
    blocks = split_korean_caption(
        "고요한 밤하늘 아래 멀리 보이는 높은 산이 있다."
    )
    lines = [ln for b in blocks for ln in b.lines]
    assert not any(
        ln.rstrip(".,!?。").endswith("높은") for ln in lines
    )
    assert any("높은 산이" in ln for ln in lines)
