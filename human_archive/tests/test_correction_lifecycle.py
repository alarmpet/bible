from human_archive.scripts.create_correction_action import create_correction_action


def test_critical_correction_propagates_all_surfaces_without_auto_post():
    manifest = create_correction_action("video-1", "CRITICAL", ["title", "subtitles", "thumbnail"])
    assert manifest["status"] == "PROPOSED"
    assert manifest["auto_post"] is False
    assert set(manifest["surfaces"]) == {"title", "subtitles", "thumbnail"}

