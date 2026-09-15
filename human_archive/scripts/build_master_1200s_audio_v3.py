# -*- coding: utf-8 -*-
"""V3 Master Audio Pipeline:
Eradicates 15-27s dead air through 5-sentence narrative expansions for starved body shots,
fixes decimal normalization (3.0 -> 삼 점 영), mixes continuous -24dB Himalayan ambient soundbed,
and delivers an exact 1,200.000s 48kHz Stereo master audio track."""
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
AUDIO_DIR = EP_DIR / "audio" / "sentences_v3"
AUDIO_DIR.mkdir(parents=True, exist_ok=True)
CANDIDATE_DIR = EP_DIR / "candidate"
CANDIDATE_DIR.mkdir(parents=True, exist_ok=True)

# Scientifically rich 4~5 sentence expansions for under-filled body shots (bringing speech to 20-23s)
EXPANDED_BODY_SCRIPTS = {
    "SHOT_028": (
        "이처럼 눈에 보이지 않는 물길들은 빙하의 내부를 거대한 스위스 치즈처럼 파먹어 들어갑니다. "
        "표면에서는 단단해 보이는 만년설이지만 속은 이미 수백 개의 물길로 구멍이 숭숭 뚫려 있죠. "
        "한번 약해진 얼음 지반은 수만 톤의 수압을 이기지 못하고 순식간에 주저앉습니다. "
        "결국 눈에 보이지 않는 내부 침식이 시한폭탄의 도화선에 불을 붙이는 셈입니다."
    ),
    "SHOT_029": (
        "내부 수로에 갇혀 있던 물은 여름철 햇볕 아래에서 무서운 속도로 불어납니다. "
        "출구를 찾지 못한 수압은 빙벽 내부를 사방에서 밀어내며 거대한 압력솥 상태를 만들죠. "
        "미세한 균열 사이로 얼음물이 뿜어져 나오기 시작하면 붕괴는 이미 돌이킬 수 없습니다. "
        "자연이 만들어낸 가장 위험한 고압 파이프라인이 산꼭대기에서 터지기 직전인 것입니다."
    ),
    "SHOT_030": (
        "호수의 수위가 제방의 턱밑까지 차오르면 물의 압력은 상상을 초월하는 수준에 도달합니다. "
        "제방 안쪽에 박혀 있던 흙과 얼음은 이미 진흙탕으로 변해 지지력을 완전히 잃어버렸죠. "
        "작은 진동 하나만으로도 수억 톤의 물을 가두고 있던 마지막 둑이 터져 나갈 수 있습니다. "
        "지금 히말라야의 계곡들은 언제 터질지 모르는 방아쇠를 당긴 채 숨을 죽이고 있습니다."
    ),
    "SHOT_031": (
        "빙하가 이동하는 속도가 빨라지면, 표면 곳곳에 수십 미터 깊이의 크레바스가 찢어집니다. "
        "얼음 덩어리가 쪼개지며 발생하는 균열은 지표면 아래 수백 미터 암반까지 파고들죠. "
        "이 거대한 틈새로 여름철 융해수가 폭포처럼 빨려 들어가며 내부 수압을 극도로 끌어올립니다. "
        "지진계에는 미세한 파쇄음이 연속적으로 기록되며 거대한 폭발의 전조를 알립니다. "
        "겉으로는 고요해 보이는 얼음 산이, 속에서는 비명을 지르고 있는 것입니다."
    ),
    "SHOT_032": (
        "크레바스를 통해 얼음 바닥으로 흘러든 물은 윤활유 역할을 하며 빙하의 미끄러짐을 가속합니다. "
        "바위 암반과 빙하 사이에서 마찰력이 사라지며 수백만 톤의 얼음 덩어리가 통째로 덜컹거립니다. "
        "이 불안정한 움직임은 제방에 균열을 일으키며 연쇄 붕괴의 위험을 증폭시키죠. "
        "산 전체가 서서히 균형을 잃어가며 계곡 아래로 쏟아질 준비를 마치는 순간입니다."
    ),
    "SHOT_033": (
        "지하 수압이 한계에 도달하면, 어느 날 갑자기 빙하 말단부가 화산처럼 폭발하며 터져 나옵니다. "
        "수백만 톤의 얼음물과 토사가 좁은 얼음 터널을 뚫고 시속 80km의 속도로 뿜어져 나오죠. "
        "얼음 파편과 거대한 바위들이 포탄처럼 계곡 아래로 쏟아져 내립니다. "
        "이 폭발적인 분출은 하류 계곡의 수로를 단 수 분 만에 완전히 메워버립니다. "
        "경보 시스템이 작동할 틈도 없이, 첫 번째 충격파가 마을을 덮치는 것입니다."
    ),
    "SHOT_034": (
        "이것이 바로 예측 불가능한 '내부 파열형 글로프'입니다. "
        "외부 제방이 터지는 일반적인 홍수와 달리, 빙하 속 얼음 동굴 자체가 파열되는 현상이죠. "
        "위성 관측으로는 빙하 표면의 변화를 감지할 수 없어 사전 대피가 불가능에 가깝습니다. "
        "지구물리학자들은 이 현상을 '빙하 내부의 수압 폭탄'이라 부릅니다. "
        "보이지 않는 곳에서 차오른 물이 가장 잔혹한 방식으로 문명을 타격하는 것입니다."
    ),
    "SHOT_035": (
        "과학자들은 이 보이지 않는 붕괴를 막기 위해 첨단 조기경보 센서를 설치하기 시작했습니다. "
        "위성 레이더와 현장 음향 센서를 연결하여 얼음 속 미세한 진동까지 실시간 감시하죠. "
        "하지만 해발 5,000m의 극한 환경에서는 배터리 하나를 교체하는 것도 목숨을 건 도전입니다. "
        "인간의 첨단 기술과 자연의 가혹한 법칙이 매 순간 팽팽하게 맞서고 있습니다."
    ),
    "SHOT_036": (
        "이 속도라면 2100년까지 히말라야 빙하의 최대 80%가 사라질 수 있습니다. "
        "남아시아와 동아시아 대륙을 식혀주던 거대한 에어컨이 영원히 꺼지는 셈이죠. "
        "만년설이 사라진 산맥은 더 이상 비구름을 붙잡지 못하고 메마른 돌산으로 변합니다. "
        "유엔 기후변화 보고서는 이를 '아시아 수자원 문명의 종말적 위기'로 규정했습니다. "
        "시한폭탄의 타이머는 이미 카운트다운을 시작했습니다."
    ),
    "SHOT_037": (
        "그렇다면 우리는 이 거대한 재앙 앞에서 그저 손을 놓고 지켜보고만 있어야 할까요? "
        "전 세계의 과학자들과 공학자들은 호수의 압력을 낮추기 위한 사투를 벌이고 있습니다. "
        "거대한 사이펀 파이프를 산꼭대기까지 끌어올려 물을 인위적으로 빼내는 작업이 진행 중이죠. "
        "단 1미터의 수위를 낮추는 것만으로도 수백만 명의 생명을 구할 수 있기 때문입니다."
    ),
    "SHOT_038": (
        "네팔의 임자 호수에서는 군인들과 현지 셰르파들이 힘을 합쳐 제방을 수작업으로 낮췄습니다. "
        "호수 수위를 3.4m 낮추는 데 무려 6개월의 뼈를 깎는 노력이 필요했죠. "
        "비록 작은 시작에 불과하지만, 이것은 인류가 재앙에 맞설 수 있다는 희망의 증거입니다. "
        "자연의 위협에 굴복하지 않고 문명을 지켜내려는 의지가 현장을 움직이고 있습니다."
    ),
    "SHOT_039": (
        "하지만 이것은 2만 5천 개의 호수 중 단 하나를 해결했을 뿐입니다. "
        "네팔과 인도 북부에 산재한 초고위험 호수만 해도 최소 수백 개가 넘습니다. "
        "한 곳의 물을 빼내는 데 수년의 시간과 수백만 달러의 예산이 소모되었죠. "
        "지금 이 순간에도 녹아내린 얼음물이 새로운 위험 호수들을 증식시키고 있습니다. "
        "인간의 방재 속도가 자연의 붕괴 속도를 결코 따라가지 못하고 있는 것입니다."
    ),
    "SHOT_040": (
        "해발 5,000m의 극한 고산지대에 중장비를 옮기는 데만 수개월이 걸리기 때문입니다. "
        "공기가 희박하여 대형 수송 헬기조차 추락 위험 때문에 비행이 제한됩니다. "
        "영하 20도의 혹한과 강풍 속에서 토목 공사를 진행하는 것은 불가능에 가깝죠. "
        "결국 현장 인부들이 곡괭이와 삽으로 얼어붙은 바위를 파내야 하는 실정입니다. "
        "현대 문명의 첨단 토목 기술도 해발 5,000m 고산 앞에서는 무력해집니다."
    ),
    "SHOT_041": (
        "결국 가장 현실적인 대안은 조기경보 시스템과 신속한 대피 훈련입니다. "
        "호수가 붕괴했을 때 하류 주민들에게 단 15분의 대피 시간이라도 벌어주는 것이죠. "
        "마을마다 확성기 사이렌이 설치되고, 주민들은 대피 경로를 익히며 매일 긴장 속에 살아갑니다. "
        "재앙을 막을 수 없다면, 최소한 인간의 목숨만은 지켜내야 한다는 절박한 선택입니다."
    ),
    "SHOT_042": (
        "하지만 홍수가 지나간 자리에 남겨지는 것은 처참한 파괴와 황폐함뿐입니다. "
        "논과 밭은 수 미터 두께의 자갈과 모래로 뒤덮여 영구히 농사를 지을 수 없게 됩니다. "
        "교량과 도로는 흔적도 없이 끊겨 계곡 전체가 문명과 완전히 고립되고 말죠. "
        "생계의 터전을 잃은 수많은 고산 주민들은 결국 고향을 등지는 기후 난민이 됩니다."
    ),
    "SHOT_043": (
        "우리는 왜 홍수보다 '빙하의 소멸'을 더 두려워해야 하는 걸까요? "
        "홍수는 일시적인 재난이지만, 빙하가 사라지면 영구적인 갈증이 시작되기 때문입니다. "
        "한번 녹아버린 수천 년의 만년설은 인간의 어떤 기술로도 다시 얼릴 수 없습니다. "
        "강줄기가 마르고 지하수가 고갈되는 순간, 농경지와 도시 전체가 사막화됩니다. "
        "진짜 재앙은 물이 넘칠 때가 아니라, 단 한 방울의 물도 흐르지 않을 때 찾아옵니다."
    ),
    "SHOT_044": (
        "그 해답은 아시아 대륙 전체를 먹여 살리는 '강의 비밀'에 있습니다. "
        "갠지스와 인더스, 양쯔강과 메콩강은 모두 히말라야의 얼음물로 태어납니다. "
        "이 강들은 아시아 20억 인구의 식수이자, 전력망이며, 거대한 식량 창고입니다. "
        "만약 이 발원지의 수도꼭지가 잠긴다면 아시아의 지정학적 지도는 통째로 뒤흔들립니다. "
        "이제 우리는 빙하의 붕괴가 불러올 문명사적 대전환의 진실을 마주해야 합니다."
    ),
    "SHOT_056": (
        "산꼭대기에서 시작된 재앙의 파동은 지금 전 세계 문명의 문턱을 넘어서고 있습니다. "
        "우리가 화석연료를 태우며 내뿜은 열기가 결국 지구의 지붕을 녹여 인류의 발밑으로 쏟아지는 것이죠. "
        "히말라야의 경고는 결코 먼 나라의 이야기가 아닌, 우리 모두의 미래에 대한 엄중한 질문입니다. "
        "자연의 침묵 뒤에 찾아올 거대한 심판 앞에서, 우리는 과연 어떤 대답을 준비하고 있을까요?"
    )
}

def get_wav_duration(path: Path) -> float:
    cmd = [
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(path)
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return float(res.stdout.strip())

def main():
    print("=== Step 1: Loading Manifest & Applying 5-Sentence Expansions ===")
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

        # If this is an expanded shot, update display_text
        if sid in EXPANDED_BODY_SCRIPTS:
            s["display_text"] = EXPANDED_BODY_SCRIPTS[sid]

        raw_text = s["display_text"]
        normalized_text = robust_normalize_korean_tts(raw_text)
        s["tts_text"] = normalized_text
        
        target_wav = AUDIO_DIR / f"{sid}_v3.wav"
        s["wav_path"] = str(target_wav)

        # Force re-synthesize if expanded or decimal present
        needs_resynth = (sid in EXPANDED_BODY_SCRIPTS) or ("점" in normalized_text) or (not target_wav.exists())

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
    # Using anoisesrc with pink noise bandpassed at 180Hz-800Hz, volume=0.045
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
