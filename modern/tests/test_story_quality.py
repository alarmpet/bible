from __future__ import annotations

from pathlib import Path
import unittest

from modern.story_quality import (
    InsufficientStoryMaterial,
    audit_portfolio,
    validate_clue_ledger,
    validate_topic_cards,
    check_filler_repetition,
    duration_bounds,
    load_yaml,
    require_story_material,
    validate_project_contract,
)


class FillerRepetitionTests(unittest.TestCase):
    def test_blocks_exact_sentence_repeated_three_times(self) -> None:
        report = check_filler_repetition("복도가 조용했다. " * 3)

        self.assertFalse(report["ok"])
        self.assertTrue(
            any("FILLER_REPEAT_BLOCK" in item for item in report["blocks"])
        )

    def test_allows_declared_refrain(self) -> None:
        report = check_filler_repetition(
            "우리는 다시 만난다. " * 3,
            allowlist=("우리는 다시 만난다.",),
        )

        self.assertTrue(report["ok"])
        self.assertEqual([], report["blocks"])

    def test_repeated_short_dialogue_is_not_filler_by_itself(self) -> None:
        report = check_filler_repetition(
            '"네."\n"네."\n"네."\n문이 닫혔다.'
        )

        self.assertTrue(report["ok"], report["blocks"])

    def test_blocks_repeated_three_sentence_window(self) -> None:
        block = "문이 열렸다. 불이 꺼졌다. 전화가 울렸다. "
        report = check_filler_repetition(
            block + block + "주인공은 밖으로 달렸다. 결정을 되돌릴 수 없었다."
        )

        self.assertFalse(report["ok"])
        self.assertTrue(any("REPEATED_BLOCK" in item for item in report["blocks"]))

    def test_clean_distinct_sentences_pass(self) -> None:
        report = check_filler_repetition(
            "문이 열렸다. 그는 복도로 나갔다. 전화가 울렸다. "
            "수빈은 받지 않았다. 대신 계단을 내려갔다. "
            "비가 창문을 두드렸다. 경비원은 우산을 건넸다. "
            "두 사람은 정문을 나섰다. 버스가 막 출발했다. "
            "수빈은 처음으로 도움을 청했다."
        )

        self.assertTrue(report["ok"])
        self.assertEqual([], report["blocks"])


class StoryMaterialTests(unittest.TestCase):
    def test_rejects_material_shorter_than_required(self) -> None:
        with self.assertRaisesRegex(
            InsufficientStoryMaterial, "INSUFFICIENT_STORY_MATERIAL"
        ):
            require_story_material("짧은 원고", 100)

    def test_accepts_material_at_minimum(self) -> None:
        require_story_material("가" * 100, 100)


class ProjectContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.valid_fiction_contract = {
            "episode_id": "E0001",
            "lane": "L3_TWIST",
            "truth_mode": "FICTION_REALISTIC",
            "duration_tier": "standard",
            "target_duration_min": 35,
            "content_disclosure": "등장인물과 사건은 허구입니다.",
        }

    def test_missing_truth_mode_blocks(self) -> None:
        contract = dict(self.valid_fiction_contract)
        del contract["truth_mode"]

        report = validate_project_contract(contract)

        self.assertFalse(report["ok"])
        self.assertTrue(any("TRUTH_MODE_REQUIRED" in item for item in report["blocks"]))

    def test_fiction_without_disclosure_blocks(self) -> None:
        contract = dict(self.valid_fiction_contract, content_disclosure="")

        report = validate_project_contract(contract)

        self.assertFalse(report["ok"])
        self.assertTrue(any("DISCLOSURE_REQUIRED" in item for item in report["blocks"]))

    def test_unsupported_duration_tier_blocks(self) -> None:
        contract = dict(self.valid_fiction_contract, duration_tier="endless")

        report = validate_project_contract(contract)

        self.assertFalse(report["ok"])
        self.assertTrue(any("DURATION_TIER_INVALID" in item for item in report["blocks"]))

    def test_verified_true_story_without_source_packet_blocks(self) -> None:
        contract = dict(
            self.valid_fiction_contract,
            lane="L1_TRUE",
            truth_mode="TRUE_VERIFIED",
            content_disclosure="확인된 자료를 바탕으로 재구성했습니다.",
        )

        report = validate_project_contract(contract)

        self.assertFalse(report["ok"])
        self.assertTrue(any("SOURCE_PACKET_REQUIRED" in item for item in report["blocks"]))

    def test_complete_verified_true_story_contract_passes(self) -> None:
        contract = dict(
            self.valid_fiction_contract,
            lane="L1_TRUE",
            truth_mode="TRUE_VERIFIED",
            content_disclosure="확인된 자료를 바탕으로 재구성했습니다.",
        )
        source_packet = {
            "core_claims": [
                {
                    "claim_id": "C01",
                    "statement": "검증할 핵심 주장",
                    "source_urls": ["https://example.com/source-a"],
                }
            ],
            "people": {"consent_status": "not_required"},
            "review_status": "approved",
            "reviewer": "editor-1",
        }

        report = validate_project_contract(contract, source_packet)

        self.assertTrue(report["ok"], report["blocks"])

    def test_duration_matrix_exposes_standard_bounds(self) -> None:
        config = load_yaml(
            Path(__file__).parents[1] / "config" / "duration_matrix.yaml"
        )

        self.assertEqual((25, 45), duration_bounds(config, "standard"))



    def test_lane_and_truth_mode_must_be_compatible(self) -> None:
        contract = dict(
            self.valid_fiction_contract,
            lane="L1_TRUE",
            truth_mode="FICTION_REALISTIC",
        )
        report = validate_project_contract(contract)
        self.assertFalse(report["ok"])
        self.assertTrue(any("LANE_TRUTH_MISMATCH" in item for item in report["blocks"]))

    def test_makjang_intensity_five_blocks(self) -> None:
        contract = dict(
            self.valid_fiction_contract,
            lane="L4_MAKJANG",
            truth_mode="FICTION_HEIGHTENED",
            makjang_intensity=5,
        )
        report = validate_project_contract(contract)
        self.assertFalse(report["ok"])
        self.assertTrue(any("MAKJANG_INTENSITY_BLOCK" in item for item in report["blocks"]))

    def test_special_without_story_scale_approval_blocks(self) -> None:
        contract = dict(
            self.valid_fiction_contract,
            duration_tier="special",
            target_duration_min=100,
        )
        report = validate_project_contract(contract)
        self.assertFalse(report["ok"])
        self.assertTrue(any("SPECIAL_APPROVAL" in item for item in report["blocks"]))

    def test_special_with_story_scale_approval_passes(self) -> None:
        contract = dict(
            self.valid_fiction_contract,
            duration_tier="special",
            target_duration_min=100,
            active_subplots=2,
            goal_state_changes=3,
            independent_act_goals=3,
            pilot_approved=True,
        )
        report = validate_project_contract(contract)
        self.assertTrue(report["ok"], report["blocks"])

class DiversityContractTests(unittest.TestCase):
    def make_cards(self) -> list[dict[str, object]]:
        lanes = ["L1_TRUE", "L2_HEART", "L3_TWIST", "L4_MAKJANG"] * 2
        return [
            {
                "card_id": f"TC-{index + 1:02d}",
                "lane": lane,
                "protagonist": {"role": f"role-{index + 1}"},
                "execution_dna": {
                    "pov": "교차시점" if index % 2 else "제한적 3인칭",
                    "chronology": "선형" if index % 2 else "두 시간대 교차",
                },
            }
            for index, lane in enumerate(lanes)
        ]

    def test_topic_cards_require_exactly_eight(self) -> None:
        report = validate_topic_cards(self.make_cards()[:7])
        self.assertFalse(report["ok"])
        self.assertTrue(any("TOPIC_CARD_COUNT" in item for item in report["blocks"]))

    def test_topic_cards_require_four_lanes(self) -> None:
        cards = self.make_cards()
        for card in cards:
            card["lane"] = "L2_HEART"
        report = validate_topic_cards(cards)
        self.assertFalse(report["ok"])
        self.assertTrue(any("LANE_DIVERSITY" in item for item in report["blocks"]))

    def test_protagonist_role_may_not_repeat_more_than_twice(self) -> None:
        cards = self.make_cards()
        for card in cards[:3]:
            card["protagonist"] = {"role": "간호사"}
        report = validate_topic_cards(cards)
        self.assertFalse(report["ok"])
        self.assertTrue(any("ROLE_OVERUSE" in item for item in report["blocks"]))

    def test_valid_topic_card_batch_passes(self) -> None:
        report = validate_topic_cards(self.make_cards())
        self.assertTrue(report["ok"], report["blocks"])

    def test_three_consecutive_execution_pairs_block(self) -> None:
        episodes = [
            {
                "episode_id": f"E{index}",
                "lane": "L2_HEART",
                "pov": "전지적",
                "chronology": "선형",
            }
            for index in range(3)
        ]
        report = audit_portfolio(episodes)
        self.assertFalse(report["ok"])
        self.assertTrue(any("EXECUTION_PAIR_STREAK" in item for item in report["blocks"]))

    def test_l3_twist_requires_three_clues(self) -> None:
        contract = {"lane": "L3_TWIST", "core_twists": 1}
        clues = [
            {"twist_id": "TW01", "clue_id": "CL01"},
            {"twist_id": "TW01", "clue_id": "CL02"},
        ]
        report = validate_clue_ledger(contract, clues)
        self.assertFalse(report["ok"])
        self.assertTrue(any("CLUE_COUNT" in item for item in report["blocks"]))

    def test_l3_twist_with_three_clues_passes(self) -> None:
        contract = {"lane": "L3_TWIST", "core_twists": 1}
        clues = [
            {"twist_id": "TW01", "clue_id": f"CL0{index}"}
            for index in range(1, 4)
        ]
        report = validate_clue_ledger(contract, clues)
        self.assertTrue(report["ok"], report["blocks"])

if __name__ == "__main__":
    unittest.main()
