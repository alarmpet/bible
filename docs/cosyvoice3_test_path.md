# CosyVoice3 시험 경로

SuperTonic3가 본편 기본 엔진이다. Fun-CosyVoice3-0.5B는 **opt-in 테스트**만 한다. 본편 full-job, `media_rules_lock.json`, 배포 MP4를 바꾸지 않는다.

## 설치

```powershell
powershell -ExecutionPolicy Bypass -File bible_healing/scripts/install_cosyvoice3.ps1
```

- 코드: `D:\Fun-CosyVoice3`
- Python 3.10 venv: `C:\Users\amd\.venvs\cosyvoice3-py310` (C:에 둠. D:는 작은 파일 복사가 느림)
- 모델: `D:\Fun-CosyVoice3\pretrained_models\Fun-CosyVoice3-0.5B`
- 이 PC는 Intel UHD 620이라 **CPU 전용**. 짧은 문장(5~15초)만 먼저 합성한다.

## 참조 음성

전용 성우 wav가 없어서 기존 SuperTonic M4/F5 짧은 클립을 복제 참조로 쓴다.

- `bible_healing/assets/voice_refs/scripture_M4_ref.wav`
- `bible_healing/assets/voice_refs/narrator_F5_ref.wav`
- 매핑: `bible_healing/config/cosyvoice3_voices.json`

## 실행

```powershell
# 1문장 smoke
python modern/scripts/test_cosyvoice3_smoke.py

# SuperTonic vs CosyVoice A/B (같은 3문장)
python modern/scripts/test_cosyvoice3_vs_supertonic3.py

# 기존 job preview만 CosyVoice로 (본편 아님)
python modern/scripts/tts_multi_voice.py --job <job> --engine cosyvoice3 --preview-only
python modern/scripts/tts_multi_voice_cosyvoice.py --job <job> --preview-only
```

`--engine` 기본값은 `supertonic3`이다. 인자를 빼면 예전과 같다.

## 제약

- CosyVoice3는 Python 3.10 전용. SuperTonic venv(3.14)와 섞지 않는다. 어댑터가 서브프로세스로 3.10 worker를 호출한다.
- CPU RTF가 높을 수 있다. 본편 51분 영상에 바로 쓰지 않는다.
- 품질이 더 나아져도 lock/배포 전환은 별도 결정이다.
