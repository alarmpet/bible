from lib.aligned_prompt_compiler import compile_aligned_prompt
def test_aligned_prompt_keeps_anchors_and_blocks_repeated_text():
 p=compile_aligned_prompt({"shot_id":"S1","visual_mode":"historical_reconstruction","semantic_anchors":["궁궐","회의"],"focal_subject":"신하들","action":"기록을 검토한다","place":"궁궐","era":"Joseon","camera":"wide"})
 assert "궁궐" in p["submission_prompt"] and "1701" not in p["submission_prompt"]
 assert any("digits" in x for x in p["negative"]["items"])

def test_host_prompt_generates_empty_background_and_uses_canonical_overlay():
 p=compile_aligned_prompt({"shot_id":"H1","visual_mode":"host_chapter_hinge","semantic_anchors":["취선당","신당"],"focal_subject":"취선당 서쪽 신당","action":"관리들이 현장을 살핀다","place":"취선당 서쪽 뜰","era":"조선","camera":"wide","motion_profile":"host_hinge"})
 assert p["host_overlay"]["asset"] == "human_archive/assets/doodle_seonbi_v1.png"
 assert "no people" in p["submission_prompt"].lower()
 assert "right" in p["submission_prompt"].lower()

def test_non_host_prompt_explicitly_excludes_presenter_and_uses_doodle_style():
 p=compile_aligned_prompt({"shot_id":"N1","visual_mode":"historical_reconstruction","semantic_anchors":["왕","대신"],"focal_subject":"왕과 대신","action":"대신들이 간언한다","place":"편전","era":"조선","camera":"wide"})
 assert "no presenter" in p["submission_prompt"].lower()
 assert "ink-doodle" in p["submission_prompt"].lower()
