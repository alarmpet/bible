from human_archive.scripts.build_nollam_audio import resolve_nollam_tts_lock


def test_nollam_audio_lock_is_m2_warm():
    lock = resolve_nollam_tts_lock()
    assert lock == {"voice_lock_id": "M2_WARM", "voice": "M2", "speed": 0.95, "total_step": 10}

