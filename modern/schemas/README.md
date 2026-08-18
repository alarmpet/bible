# JSON 계약 개요 (스키마 문서)

구현 validator: `scripts/validate_job.py`  
정식 필드는 계획서 v1.2 §4 참고.

| 파일 | 원본/파생 | 설명 |
|---|---|---|
| shot_plan.json | **원본** | 시각·이미지 경로·씬 ID |
| scenes.json | **원본** | segments[] 화자·텍스트 |
| voice_map.json | **원본** | 화자→SuperTonic voice/speed |
| draft.json | 파생 | Hermes 렌더 호환 narration join |
| job.json | 원본 | intro_mode, multi_voice, scene_count |
| scene-media-manifest.json | 파생 | sha256, order |
| scene_audio_manifest.json | TTS 후 | ok=전원 성공 시에만 true |

`intro_mode` enum: `PRE_ROLL_VIDEO` (기본 고정)
