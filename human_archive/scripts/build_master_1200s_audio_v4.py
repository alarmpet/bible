# -*- coding: utf-8 -*-
"""V4 Master Audio Pipeline:
Eradicates all dead air by expanding ALL 36 body shots (incorporating the remaining 18 shots:
SHOT_021~027 and SHOT_045~055), synthesizes 4~5 sentence dense scientific narration via SuperTonic3 M2,
hardens Korean phonetic normalization, and mixes a continuous -24dB ambient soundscape for an exact 1,200.000s master audio track."""
from __future__ import annotations
import json
import re
import subprocess
import sys
import time
from pathlib import Path

SUPERTONIC_ROOT = Path(r"C:\Users\shs\supertonic3-local-tts-20260517-r4\supertonic3-local-tts")
sys.path.insert(0, str(SUPERTONIC_ROOT / "src"))
sys.path.insert(0, r"D:\module\bible\human_archive\scripts")

from supertonic3_engine import Supertonic3Engine
from lib.korean_phonetic_normalizer import robust_normalize_korean_tts

EP_DIR = Path(r"D:\module\bible\human_archive\runs\nollam_file\2026-09-02\himalaya-glof-water-crisis")
MANIFEST_PATH = EP_DIR / "generation" / "master_1200s_manifest.json"
AUDIO_DIR = EP_DIR / "audio" / "sentences_v4"
AUDIO_DIR.mkdir(parents=True, exist_ok=True)
CANDIDATE_DIR = EP_DIR / "candidate"
CANDIDATE_DIR.mkdir(parents=True, exist_ok=True)

# 18 Newly Expanded Shots + Previous 18 Shots = 100% 36 Body Shots Fully Expanded!
EXPANDED_BODY_SCRIPTS_V4 = {
    # Phase 2: Moraine Trap Hook & Mechanics (Shots 21 - 27)
    "SHOT_021": (
        "우리가 흔히 생각하는 댐은 단단한 철근 콘크리트로 지어집니다. "
        "하지만 해발 5,000m의 빙하호수를 가두고 있는 댐은 인간이 만든 것이 아닙니다. "
        "수만 년 동안 빙하가 밀어 올린 모래와 자갈, 그리고 얼음 덩어리가 뒤섞여 쌓인 자연의 흙더미에 불과하죠. "
        "지질학자들은 이 위태로운 구조물을 '빙퇴석 모레인 댐'이라고 부릅니다. "
        "기초 암반도 없이 얼어붙은 흙으로만 버티고 있어 언제 무너져도 이상하지 않은 시한폭탄입니다."
    ),
    "SHOT_022": (
        "빙하 호수를 둘러싸고 있는 이 제방은 겉보기에는 수백 미터 두께의 견고한 산처럼 보입니다. "
        "하지만 그 속을 들여다보면 충격적인 비밀이 숨겨져 있습니다. "
        "제방의 중심부는 단단한 암반이 아니라 과거 빙하가 남기고 간 흙과 진흙 덩어리일 뿐입니다. "
        "기온이 상승하면 이 흙더미를 단단히 굳혀주던 영구동토층이 녹아내리며 내부 지지력을 잃게 되죠. "
        "겉은 멀쩡해 보이지만 속은 이미 부드러운 진흙탕으로 변해가고 있는 것입니다."
    ),
    "SHOT_023": (
        "더욱 치명적인 위험은 제방 흙더미 속에 파묻혀 있는 거대한 만년설 덩어리, 즉 '사빙'입니다. "
        "수천 년 전 빙하의 잔해가 흙 속에 묻혀 있다가 온난화로 인해 서서히 녹아내리는 현상이죠. "
        "사빙이 녹아 빈 공간이 생기면 제방 내부에는 거대한 싱크홀과 지하 동굴이 형성됩니다. "
        "수억 톤의 호수 물을 지탱해야 할 제방의 바닥이 속부터 텅 비어 주저앉는 끔찍한 연쇄 붕괴가 진행되는 것입니다."
    ),
    "SHOT_024": (
        "그렇다면 이 위태로운 호수를 폭발시키는 첫 번째 방아쇠는 무엇일까요? "
        "그것은 바로 호수 윗벽에 매달려 있는 거대한 빙벽 붕괴입니다. "
        "해발 6,000m 고산의 칼날 같은 절벽에서 수십만 톤의 얼음 덩어리가 한순간에 떨어져 내립니다. "
        "마치 거대한 빌딩 수십 채가 산꼭대기에서 호수 한가운데로 자유낙하하는 것과 같은 엄청난 물리적 충격이 발생합니다."
    ),
    "SHOT_025": (
        "낙하한 빙벽이 호수 수면을 강타하는 순간, 수십 미터 높이의 거대한 해일이 솟구쳐 오릅니다. "
        "유체역학에서 '세이시 파도'라 불리는 이 내륙 쓰나미는 시속 수십 킬로미터의 속도로 호수 가장자리를 향해 질주하죠. "
        "평온했던 호수 표면이 순식간에 거대한 괴물의 입처럼 변해 흙더미 제방을 사정없이 후려칩니다. "
        "한번 밀어닥친 파도는 취약한 흙 제방을 단 몇 초 만에 깎아내리기 시작합니다."
    ),
    "SHOT_026": (
        "2021년 인도 차몰리 참사 당시에도 바로 이러한 빙벽 낙하가 재앙의 도화선이었습니다. "
        "충격파로 인해 지진계에는 지진 규모 3.0 이상의 강력한 지진파가 감지되었죠. "
        "지진이 나서 얼음이 무너진 것이 아니라, 얼음이 무너지며 땅을 흔든 것입니다. "
        "수력발전소 건설 현장과 다리들이 단 수 분 만에 흔적도 없이 사라지며 수백 명의 인명 피해가 발생했습니다."
    ),
    "SHOT_027": (
        "두 번째 방아쇠는 흙더미 제방 자체가 안쪽에서부터 터져 나가는 파이핑 현상입니다. "
        "흙 속에 얼어붙어 있던 얼음이 녹아내리며 생긴 물길이 수압을 이기지 못하고 거대한 터널로 확장되죠. "
        "호수의 바닥에서부터 시작된 누수는 걷잡을 수 없는 속도로 둑을 파먹어 들어갑니다. "
        "제방의 가장 취약한 지점이 뚫리는 순간, 둑 전체가 지퍼가 열리듯 단숨에 터져 나가는 것입니다."
    ),

    # Phase 4 & 5: Peak Water, Transboundary Geopolitics, & Outro (Shots 45 - 55)
    "SHOT_045": (
        "히말라야의 빙하는 단순히 위험한 호수를 만드는 것에 그치지 않고, 인류의 생존을 떠받치는 거대한 자연 저수지입니다. "
        "겨울철에 쌓인 눈을 거대한 얼음 덩어리로 저장했다가 건기마다 일정하게 물을 방출해 생명줄을 이어주죠. "
        "하지만 온난화로 인해 이 영구적인 물 공급 시스템에 심각한 교란이 발생하고 있습니다. "
        "과학자들은 얼음이 녹아 일시적으로 유량이 폭증하는 이 위험한 전환점을 주목하고 있습니다."
    ),
    "SHOT_046": (
        "인도의 갠지스강, 파키스탄의 인더스강, 중국의 황하와 양쯔강은 모두 히말라야의 만년설에서 출발합니다. "
        "수천 년 동안 이 강줄기들은 아시아 대륙의 농경 문명을 꽃피우고 도시들을 먹여 살려왔죠. "
        "하지만 빙하가 급격히 녹아내리면서 강 상류의 유량 변동성이 극단적으로 커지고 있습니다. "
        "지금 당장은 물이 넘쳐나 홍수가 빈발하지만, 이것은 곧 닥쳐올 거대한 파국의 전조일 뿐입니다."
    ),
    "SHOT_047": (
        "기후학계에서는 이 현상을 '피크 워터', 즉 유량의 정점이라고 부릅니다. "
        "빙하가 녹아내리는 속도가 극에 달해 수자원 배출량이 최대치를 찍는 순간을 의미하죠. "
        "겉으로 보기에는 수자원이 풍부해진 것처럼 보이지만, 사실은 수천 년 동안 저장된 원금을 탕진하는 과정입니다. "
        "피크 워터를 지나 얼음 저장고가 바닥을 드러내면, 인류 역사상 유례없는 파멸적인 갈증이 시작됩니다."
    ),
    "SHOT_048": (
        "예측 모델에 따르면 2050년경 남아시아의 주요 하천들은 피크 워터를 지나 유량이 급격히 감소할 것으로 보입니다. "
        "빙하에서 흘러나오는 여름철 유입수가 최대 50%까지 줄어들 것으로 관측되죠. "
        "비가 오지 않는 건기에는 강바닥이 완전히 말라붙어 논과 밭에 물을 댈 수 없게 됩니다. "
        "세계 최대 인구 밀집 지역의 곡창지대가 한순간에 메마른 황무지로 변하는 것입니다."
    ),
    "SHOT_049": (
        "파키스탄은 국가 전체 농업용수의 90% 이상을 인더스강 빙하수에 의존하고 있습니다. "
        "2억 4천만 인구의 식량 생산과 국가 경제 전체가 오직 이 강줄기 하나에 목숨을 걸고 있는 셈이죠. "
        "인도 북부의 5억 인구 역시 갠지스강 유역에서 벼농사를 지으며 살아가고 있습니다. "
        "빙하가 마르면 식량 공급망이 마비되며 전 지구적인 대규모 아사 위기가 현실화됩니다."
    ),
    "SHOT_050": (
        "수자원의 고갈은 단순한 환경 문제를 넘어 국가 간의 생존을 건 치열한 지정학적 충돌로 번집니다. "
        "물이 부족해진 상류 국가들은 자국민을 살리기 위해 거대한 댐을 건설하고 물길을 돌리기 시작하죠. "
        "이는 하류 국가의 생명줄을 직접적으로 죄는 행위이며, 외교적 타협의 한계를 시험하게 만듭니다. "
        "아시아의 지붕이라 불리는 히말라야가 가장 위험한 화약고로 변모하는 것입니다."
    ),
    "SHOT_051": (
        "국경을 맞댄 인도와 파키스탄, 그리고 중국은 이미 핵무기를 보유한 군사 대국들입니다. "
        "이 국가들이 하나의 강줄기를 두고 수자원 통제권을 다투는 상황은 상상조차 하기 힘든 재앙을 부를 수 있죠. "
        "물 한 방울이라도 더 확보하기 위한 댐 건설 경쟁은 상호 간의 군사적 긴장감을 최고조로 끌어올립니다. "
        "기후변화가 초래한 물 부족이 결국 21세기 문명의 전쟁 방아쇠가 되는 셈입니다."
    ),
    "SHOT_052": (
        "실제로 인더스강 상류와 브라마푸트라강 유역에서는 이미 보이지 않는 물 전쟁이 진행 중입니다. "
        "상류 국가가 댐의 수문을 닫으면 하류의 수천만 주민들은 당장 마실 물조차 구하지 못하는 지옥을 겪게 됩니다. "
        "식수와 전력이 끊긴 도시들은 폭동과 혼란에 휩싸이고, 국경지대에는 군대가 전진 배치되죠. "
        "빙하가 녹아내리는 속도만큼이나 지정학적 파국의 시계도 빠르게 돌아가고 있습니다."
    ),
    "SHOT_053": (
        "인류 역사는 번성했던 문명들이 기후 붕괴와 수자원 고갈 앞에서 얼마나 무력하게 무너졌는지를 똑똑히 보여줍니다. "
        "과거 메소포타미아와 마야 문명도 강줄기가 마르고 토양이 황폐해지며 역사 속으로 사라졌죠. "
        "지금 히말라야에서 녹아내리는 만년설은 우리 현대 문명 역시 결코 영원하지 않다는 경고의 메시지입니다. "
        "과거의 실패를 되풀이하지 않기 위한 전 지구적 각성이 시급한 순간입니다."
    ),
    "SHOT_054": (
        "해발 5,000m 고산의 얼음이 무너지는 것은 지구가 인류에게 보내는 마지막 경고음입니다. "
        "자연의 가장 거대한 얼음 탑이 녹아내리며, 이제 그 영향은 고산 부족을 넘어 전 인류의 문턱까지 다다랐습니다. "
        "물이 넘쳐흘러 모든 것을 삼키는 순간과, 물이 말라붙어 아무것도 남지 않는 미래 사이에서, 인류는 과연 어떤 대답을 준비하고 있을까요? "
        "시간은 결코 우리를 기다려주지 않습니다."
    ),
    "SHOT_055": (
        "히말라야 만년설이 쪼개지며 내는 굉음은 지구 온난화라는 거대한 폭풍의 전조곡입니다. "
        "지구의 지붕이 무너지면 그 아래 기대어 살아가던 인류 문명의 기둥도 결코 온전할 수 없습니다. "
        "이것은 먼 미래의 공상과학이 아닌, 지금 이 순간 우리 발밑에서 벌어지고 있는 가혹한 현실입니다. "
        "대자연이 던진 엄중한 물음 앞에서, 우리는 지금 당장 행동에 나서야만 합니다."
    ),
}

def get_wav_duration(path: Path) -> float:
    cmd = [
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(path)
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return float(res.stdout.strip())

def main():
    print("=== Step 1: Loading Manifest & Applying Full 18-Shot V4 Expansions ===")
    manifest_data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    shots = manifest_data["shots"]
    print(f"Loaded {len(shots)} shots from manifest.")

    engine = Supertonic3Engine(output_dir=AUDIO_DIR)
    voice = "M2"
    speed = 1.075
    total_step = 10

    synthesized_count = 0
    for s in shots:
        sid = s["shot_id"]
        is_pilot = s.get("is_pilot", False)

        # Apply V4 expansion if present
        if sid in EXPANDED_BODY_SCRIPTS_V4:
            s["display_text"] = EXPANDED_BODY_SCRIPTS_V4[sid]

        raw_text = s["display_text"]
        normalized_text = robust_normalize_korean_tts(raw_text)
        s["tts_text"] = normalized_text
        
        target_wav = AUDIO_DIR / f"{sid}_v4.wav"
        
        # Check if re-synthesis needed
        needs_resynth = (sid in EXPANDED_BODY_SCRIPTS_V4) or (not target_wav.exists())

        if needs_resynth:
            print(f"Synthesizing [{sid}] ({len(normalized_text)} chars): {normalized_text[:40]}...")
            engine.synthesize_to_file(
                text=normalized_text,
                voice=voice,
                speed=speed,
                total_step=total_step,
                output_path=target_wav
            )
            synthesized_count += 1
        else:
            # If not in EXPANDED_BODY_SCRIPTS_V4, use v3 wav if existing, else copy
            v3_wav = EP_DIR / "audio" / "sentences_v3" / f"{sid}_v3.wav"
            if v3_wav.exists() and not target_wav.exists():
                import shutil
                shutil.copy2(v3_wav, target_wav)

        s["wav_path"] = str(target_wav)
        dur = get_wav_duration(target_wav)
        s["speech_duration"] = round(dur, 3)
        if is_pilot:
            s["speech_start"] = round(s.get("speech_start", s["scene_start"] + 0.1), 3)
        else:
            s["speech_start"] = round(s["scene_start"] + 0.5, 3)
        s["speech_end"] = round(s["speech_start"] + dur, 3)
        gap = s["scene_duration"] - dur
        print(f"[{sid}] Audio: dur={dur:.2f}s, silence_tail={gap:.2f}s (ends {s['speech_end']:.2f}s / {s['scene_end']:.2f}s)")

    print(f"Synthesis pass finished: {synthesized_count} files newly synthesized.")
    MANIFEST_PATH.write_text(json.dumps(manifest_data, ensure_ascii=False, indent=2), encoding="utf-8")

    # Step 2: Assemble Master Audio with continuous ambient soundbed (dynamic 840s~1560s)
    total_target_dur = float(manifest_data.get("total_duration_sec", shots[-1]["scene_end"]))
    print(f"\n=== Step 2: Assembling {total_target_dur:.1f}s 48kHz Master Audio Track with Ambient Bed ===")
    master_wav = CANDIDATE_DIR / "pilot_audio_1200s_master.wav"

    inputs = []
    filter_parts = []
    
    # 0 to 55: shot voiceovers
    for i, s in enumerate(shots):
        wav_p = Path(s["wav_path"])
        inputs.extend(["-i", str(wav_p)])
        delay_ms = int(round(s["speech_start"] * 1000))
        filter_parts.append(f"[{i}:a]adelay={delay_ms}|{delay_ms}[a{i}]")

    voice_mix = "".join(f"[a{i}]" for i in range(len(shots)))
    filter_parts.append(f"{voice_mix}amix=inputs={len(shots)}:dropout_transition=0:normalize=0[voice_mixed]")

    # Continuous high-altitude wind & deep glacial presence ambient soundbed (-24dB to -26dB)
    ambient_gen = f"anoisesrc=d={int(total_target_dur + 5)}:c=pink:r=48000:a=0.035,highpass=f=80,lowpass=f=900,volume=0.45[ambient]"
    filter_parts.append(ambient_gen)

    # Mix voiceover with ambient bed, sidechain/gentle compression, then broadcast loudnorm
    final_chain = (
        "[voice_mixed][ambient]amix=inputs=2:dropout_transition=0:normalize=0[full_mixed];"
        "[full_mixed]highpass=f=45,lowpass=f=8500,"
        "equalizer=f=180:t=q:w=1:g=1.5,equalizer=f=3400:t=q:w=1:g=1.2,"
        "loudnorm=I=-16:TP=-1.5:LRA=11,"
        f"apad=whole_dur={total_target_dur:.3f}[outa]"
    )
    filter_parts.append(final_chain)
    filter_complex = ";".join(filter_parts)

    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "warning",
        *inputs,
        "-filter_complex", filter_complex,
        "-map", "[outa]",
        "-t", f"{total_target_dur:.3f}",
        "-ar", "48000",
        "-ac", "2",
        str(master_wav)
    ]
    t0 = time.time()
    print("Muxing master audio track via FFmpeg...")
    subprocess.run(cmd, check=True)
    dt = time.time() - t0
    final_dur = get_wav_duration(master_wav)
    print(f"Master audio generated in {dt:.1f}s: {master_wav} ({final_dur:.3f}s)")

if __name__ == "__main__":
    main()
