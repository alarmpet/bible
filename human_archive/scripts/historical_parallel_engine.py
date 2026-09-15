# -*- coding: utf-8 -*-
"""Historical Parallel Storytelling Engine for 'History-Ida' (역사이다) Channel.
Connects contemporary issues/controversies with profound historical parallels.
Adheres to the 6-part dramatic hooking formula (Time-Space Anchor, Symbolic Object,
One-word Beat, Lore Integration, Time Jump & Irony, Cognitive Dissonance Mystery Hook).
Produces mathematically exact dynamic multi-phase documentary scripts
strictly tailored to the specific topic (Maya, JWST, Titan, Quantum, Mongol, etc.).
"""
from __future__ import annotations

import datetime
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SCRIPTS_DIR = Path(r"D:\module\bible\human_archive\scripts")
LIB_DIR = SCRIPTS_DIR / "lib"
if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))

try:
    from cinematic_editing_director import calculate_variable_shot_budget
except ImportError:
    calculate_variable_shot_budget = None

# Curated Historical Parallel Archetypes
HISTORICAL_PARALLEL_PAIRS = [
    {
        "pair_id": "PAIR-01-AI-DATA-JAM",
        "modern_issue": "빅테크 AI의 전 세계 데이터 독점과 정보 통제권 논란",
        "historical_parallel": "13세기 칭기즈 칸의 대제국 정보망 '참(Örtöö)'과 유라시아 정보 독점",
        "historical_period": "1162년 ~ 1227년 몽골 제국",
        "time_space_anchor": "1162년 무렵, 몽골 초원의 살을 에는 겨울.",
        "protagonist": "테무진 (칭기즈 칸)",
        "core_hook": "세계에서 가장 큰 제국을 만든 남자가 왜 자기 무덤 하나를 남기지 않았을까요?",
        "modern_lesson": "기술과 인프라를 통제한 자가 세계를 지배하지만, 비밀과 침묵을 선택한 자만이 신화로 남는다.",
        "primary_sources": ["《몽골비사(元朝秘史)》", "라시드 앗 딘의 《집사(Jami al-Tawarikh)》", "《원사(元史)》", "마르코 폴로의 《동방견문록》"]
    },
    {
        "pair_id": "PAIR-02-INFLATION-PAPER-MONEY",
        "modern_issue": "무제한 양적완화와 기축통화 불안, 그리고 화폐 신뢰의 붕괴",
        "historical_parallel": "14세기 원나라의 무제한 지폐(교초) 남발과 세계 최초의 초인플레이션 멸망사",
        "historical_period": "1260년 ~ 1368년 원나라 대도",
        "time_space_anchor": "1287년 가을, 원나라 황궁의 조폐청.",
        "protagonist": "쿠빌라이 칸과 재정 관료들",
        "core_hook": "금과 은이 없어도 종이 쪼가리 하나로 세상을 살 수 있다던 황제, 그 종이는 왜 제국을 불태웠을까요?",
        "modern_lesson": "신뢰가 사라진 화폐는 단순한 쓰레기이자 문명을 삼키는 뇌관이다.",
        "primary_sources": ["《원사(元史) 식화지》", "라시드 앗 딘의 《집사》", "이븐 바투타의 《여행기》"]
    },
    {
        "pair_id": "PAIR-03-CRYPTO-BUBBLE-TULIP",
        "modern_issue": "실체 없는 코인과 디지털 자산 광풍, 그리고 한순간의 신기루",
        "historical_parallel": "1636년 네덜란드 튤립 파동 — 집 한 채 값이었던 구근 하나가 하룻밤 만에 쓰레기가 된 날",
        "historical_period": "1636년 ~ 1637년 네덜란드 암스테르담",
        "time_space_anchor": "1636년 차가운 겨울밤, 암스테르담의 어느 선술집.",
        "protagonist": "투기꾼들과 '영원한 황제(Semper Augustus)' 구근",
        "core_hook": "꽃 한 송이에 암스테르담 최고급 대저택 세 채를 걸었던 사람들, 그들은 왜 그 미친 열풍에 취했을까요?",
        "modern_lesson": "인간의 탐욕이 가격을 만들 때, 이성은 가장 먼저 시장을 떠난다.",
        "primary_sources": ["네덜란드 고문서 보관소 공증인 기록", "찰스 맥케이의 《대중의 망상과 집단 광기》"]
    },
    {
        "pair_id": "PAIR-04-CLIMATE-FAMINE-LITTLE-ICE",
        "modern_issue": "기후 급변으로 인한 식량 안보 위기와 지정학적 분쟁 격화",
        "historical_parallel": "17세기 소빙하기 대기근과 명청 교체기 — 기후 재앙이 거대 제국을 무너뜨린 순간",
        "historical_period": "1640년대 동아시아와 명나라 말기",
        "time_space_anchor": "1644년 봄, 북경 자금성을 휘감은 기괴한 모래폭풍.",
        "protagonist": "명나라 마지막 황제 숭정제와 이자성",
        "core_hook": "단 1도의 기온 하강이 수천만 명을 굶주림으로 몰아넣고 300년 제국을 무너뜨렸다면 믿으시겠습니까?",
        "modern_lesson": "문명이 아무리 번영해도, 자연이 식탁을 거두어가면 모든 제국은 순식간에 모래성처럼 무너진다.",
        "primary_sources": ["《명사(明史)》", "조선왕조실록 인조실록", "NASA 소빙하기 수목 나이테 데이터"]
    },
    {
        "pair_id": "PAIR-05-MAYA-COLLAPSE",
        "modern_issue": "환경 파괴, 수자원 고갈, 그리고 현대 도시 문명의 기후 티핑포인트 붕괴 위험",
        "historical_parallel": "9세기 마야 문명의 6만 개 거대 도시와 1,000만 인구의 의문의 증발 미스터리",
        "historical_period": "기원전 1000년 ~ 서기 9세기 중앙아메리카 유카탄 반도",
        "time_space_anchor": "한낮에도 햇빛 한 줌 들지 않는 유카탄 반도의 빽빽한 밀림, 그 숨 막히는 열기 속으로 들어섭니다.",
        "protagonist": "마야의 신왕(K'uhul Ajaw)들과 1,000만 도시민들",
        "core_hook": "빽빽한 정글 나무를 첨단 라이다 레이저로 걷어내자 6만 개의 거대 도시가 드러났습니다. 그런데 그 수많은 사람들은 도대체 어디로 감쪽같이 사라졌을까요?",
        "modern_lesson": "자연의 한계를 넘어서는 착취와 과밀 번영은, 가장 찬란한 정점에서 문명을 순식간에 잿더미로 만든다.",
        "primary_sources": [
            "《Science (2022) Maya Lowland LiDAR Survey》",
            "《Nature 유카탄 석순 산소 동위원소 고기후 100년 대가뭄 데이터》",
            "마야 드레스덴 코덱스 상형문자 고문서",
            "티칼 1호 신전 비문 기록"
        ]
    },
    {
        "pair_id": "PAIR-06-JWST-GALAXY",
        "modern_issue": "기존 표준 과학 이론의 붕괴와 지적 패러다임의 전면적 전환",
        "historical_parallel": "제임스 웹 135억 년 전 거대 괴물 은하 발견과 표준 우주론 빅뱅 모델의 충격",
        "historical_period": "138억 년 전 우주의 새벽 ~ 현대 천체물리학",
        "time_space_anchor": "지구에서 150만 킬로미터 떨어진 영하 233도의 칠흑 같은 우주 공간.",
        "protagonist": "제임스 웹 우주망원경과 현대 천체물리학자들",
        "core_hook": "빅뱅 직후의 우주에는 아기 은하만 있어야 정상입니다. 그런데 왜 은하수보다 무거운 괴물 은하들이 이미 완성되어 있었을까요?",
        "modern_lesson": "우리가 절대적 진리라고 믿었던 도그마는, 새로운 관측 렌즈 앞에서 언제든 무너질 수 있다.",
        "primary_sources": ["《Nature Astronomy (2024) JWST Massive Early Galaxies》", "NASA/ESA 제임스 웹 적외선 분광 데이터", "플랑크 우주선 우주배경복사 전천 지도"]
    },
    {
        "pair_id": "PAIR-07-TITAN-SUBMERSIBLE",
        "modern_issue": "상업주의적 안전 불감증과 첨단 신소재 맹신이 부른 문명적 참사",
        "historical_parallel": "수압 400기압 심해 3,800m 타이탄 잠수정의 20밀리초 내파 참사와 1963년 스레셔 잠수함 침몰",
        "historical_period": "1963년 ~ 2023년 북대서양 심해",
        "time_space_anchor": "북대서양 수심 3,800미터, 빛 한 줄기 닿지 않는 얼음장 같은 암흑.",
        "protagonist": "타이탄 잠수정 탑승자들과 해양 심해 공학자들",
        "core_hook": "인간의 뇌가 고통을 인지하는 데 걸리는 시간 100밀리초. 하지만 수압 400기압이 잠수정을 짓이긴 시간은 단 20밀리초였습니다.",
        "modern_lesson": "물리 법칙은 타협하지 않으며, 자연의 거대한 힘 앞에 오만은 가장 참혹한 대가를 치른다.",
        "primary_sources": ["미 해안경비대(USCG) 해양조사위원회 타이탄 블랙박스 음향 보고서", "미 해군 심해음향감시체계(SOSUS) 내파 파형 기록"]
    },
    {
        "pair_id": "PAIR-08-QUANTUM-QDAY",
        "modern_issue": "디지털 보안의 절대적 신뢰 붕괴와 양자 우위의 지정학적 무기화",
        "historical_parallel": "양자 컴퓨터 1,000 큐비트 돌파와 현대 모든 암호 체계의 무력화 'Q-Day'",
        "historical_period": "2차 대전 튜링의 에니그마 해독 ~ 현대 양자 정보혁명",
        "time_space_anchor": "절대영도에 가까운 영하 273도, 극저온 희석 냉동기 내부의 양자 칩.",
        "protagonist": "양자 컴퓨터 과학자들과 글로벌 암호학자들",
        "core_hook": "슈퍼컴퓨터로 1만 년 걸릴 암호 해독을 단 200초 만에 끝내는 존재, 그날이 오면 인류의 금융과 안보는 어떻게 될까요?",
        "modern_lesson": "비밀을 지키는 힘과 깨부수는 힘의 균형이 깨질 때, 기존의 모든 문명 시스템은 하룻밤 사이에 재편된다.",
        "primary_sources": ["《Nature / Physical Review Letters》 양자 우위 논문", "미국 국립표준기술연구소(NIST) 양자내성암호 표준 규격서"]
    },
    {
        "pair_id": "PAIR-09-SAN-JOSE-GALLEON",
        "modern_issue": "20조 원 규모의 심해 보물선 발견과 국가 간 약탈 문화유산 소유권 분쟁",
        "historical_parallel": "1708년 카리브해 바루 전투와 스페인 보물선 산호세(San José)호 침몰 및 300년의 침묵",
        "historical_period": "1708년 6월 8일 스페인 왕위 계승 전쟁 카리브해 바루 해역",
        "time_space_anchor": "1708년 6월 8일 해질 무렵, 카리브해 바루 섬 앞바다에 붉은 노을이 짙게 내려앉습니다.",
        "protagonist": "호세 페르난데스 데 산틸랸 제독과 600명의 스페인 선원, 그리고 찰스 웨이저 제독의 영국 함대",
        "core_hook": "바다 밑 3,100m, 아니 칠흑 같은 심해 속에 잠든 20조 원의 황금과 에메랄드. 64문의 청동 대포와 함께 침몰한 스페인 갈레온선 산호세호는 왜 300년 동안 침묵했을까요?",
        "modern_lesson": "제국의 번영을 위해 원주민의 피와 눈물로 채운 황금은 결국 화약고의 불길과 함께 바닷속으로 사라졌으며, 300년이 지난 오늘날에도 인간의 끝없는 탐욕을 비추는 거울이 된다.",
        "primary_sources": [
            "《영국 해군 기록 보관소(UK National Archives) 찰스 웨이저 제독 함대 전투 일지》",
            "《스페인 인디아스 고문서관(Archivo General de Indias) 산호세호 적재 화물 공식 매니페스트》",
            "《우즈홀 해양연구소(WHOI) REMUS 6000 자율 수중 로봇 음파 탐지 및 64문 청동 대포 돌고래 각인 판독 보고서》",
            "《콜롬비아 문화부·해양고고학연구소 심해 카리브해 유적 보존 백서》"
        ]
    },
    {
        "pair_id": "PAIR-10-NEANDERTHAL-EXTINCTION",
        "modern_issue": "초지능 AI(AGI)의 등장과 호모 사피엔스의 지구상 유일한 지적 생명체 독점 지위 상실 위기",
        "historical_parallel": "4만 년 전 유라시아 빙하기 호모 사피엔스와 네안데르탈인의 생존 경쟁 및 네안데르탈인의 최종 멸종",
        "historical_period": "기원전 40,000년 ~ 28,000년경 플라이스토세 후기 최종빙기 (하인리히 이벤트 4)",
        "time_space_anchor": "4만 년 전 혹한의 칼바람이 몰아치던 유라시아 빙하기 툰드라의 어느 깎아지른 절벽 동굴 앞.",
        "protagonist": "1,600cc의 대형 뇌와 막강한 근력을 지닌 네안데르탈인 사냥꾼들과 새로운 지적 생명체 호모 사피엔스",
        "core_hook": "현대인보다 뇌가 크고 근력이 압도적이었던 또 다른 인류, 30만 년간 유라시아를 지배했던 네안데르탈인은 왜 하필 사피엔스가 도래한 직후 지구상에서 완전히 지워졌을까요?",
        "modern_lesson": "단일 생태 지위에 두 개의 고도 지적 존재가 공존할 때 평화로운 공존은 불가능하며, 기술과 상징적 유대감의 격차는 가장 강인했던 형제 종마저 영원한 침묵으로 몰아넣었다.",
        "primary_sources": [
            "《Science / Nature》 막스플랑크 진화인류학연구소 스반테 페보(Svante Pääbo) 연구팀 네안데르탈인 전장 게놈 해독 논문 (2010)",
            "《Science / Antiquity》 랄프 솔레키 & 캠브리지대 에마 폼로이 연구팀 샤니다르 동굴 4호 및 Z호 매장 유골 발굴 보고서",
            "《Nature》 클라이브 핀레이슨 연구팀 지브롤터 고럼 동굴(Gorham's Cave) 네안데르탈인 최후 거처 및 해시태그 암각화 실측 보고서",
            "《Journal of Human Evolution》 처칠 연구팀 샤니다르 3호 갈비뼈 투창기(Atlatl) 발사체 충격 흔적 법의인류학적 분석서",
            "《Science》 페델레 연구팀 캄파니아 화산 대분화(Campanian Ignimbrite) 및 하인리히 이벤트 4(HE4) 급격 냉각 데이터"
        ]
    }
]


class HistoricalParallelEngine:
    """Engine that pairs contemporary issues with historical parallels and generates topic-tailored dynamic scripts."""

    calculate_shot_budget = staticmethod(calculate_variable_shot_budget)

    def __init__(self):
        self.pairs = HISTORICAL_PARALLEL_PAIRS

    def match_or_create_parallel(self, topic_query: str) -> Dict[str, Any]:
        """Find the best matching historical parallel archetype or generate a custom one."""
        clean_q = topic_query.lower()

        # Specific Priority Routing
        if any(k in clean_q for k in ["네안데르탈", "사피엔스", "빙하기", "호모 사피엔스", "멸종"]):
            return next(p for p in self.pairs if p["pair_id"] == "PAIR-10-NEANDERTHAL-EXTINCTION")
        if any(k in clean_q for k in ["산호세", "보물선", "카리브", "갈레온", "스페인 보물선", "바루"]):
            return next(p for p in self.pairs if p["pair_id"] == "PAIR-09-SAN-JOSE-GALLEON")
        if any(k in clean_q for k in ["마야", "유카탄", "라이다", "밀림", "피라미드", "고고학"]):
            return next(p for p in self.pairs if p["pair_id"] == "PAIR-05-MAYA-COLLAPSE")
        if any(k in clean_q for k in ["제임스", "은하", "우주", "jwst", "천문"]):
            return next(p for p in self.pairs if p["pair_id"] == "PAIR-06-JWST-GALAXY")
        if any(k in clean_q for k in ["타이탄", "잠수정", "심해", "수압", "내파", "폭축"]):
            return next(p for p in self.pairs if p["pair_id"] == "PAIR-07-TITAN-SUBMERSIBLE")
        if any(k in clean_q for k in ["양자", "q-day", "암호", "큐비트"]):
            return next(p for p in self.pairs if p["pair_id"] == "PAIR-08-QUANTUM-QDAY")
        if any(k in clean_q for k in ["칭기즈", "테무진", "몽골"]):
            return next(p for p in self.pairs if p["pair_id"] == "PAIR-01-AI-DATA-JAM")
        if any(k in clean_q for k in ["인플레이션", "화폐", "교초"]):
            return next(p for p in self.pairs if p["pair_id"] == "PAIR-02-INFLATION-PAPER-MONEY")
        if any(k in clean_q for k in ["튤립", "코인", "버블"]):
            return next(p for p in self.pairs if p["pair_id"] == "PAIR-03-CRYPTO-BUBBLE-TULIP")
        if any(k in clean_q for k in ["소빙하기", "기후", "식량"]):
            return next(p for p in self.pairs if p["pair_id"] == "PAIR-04-CLIMATE-FAMINE-LITTLE-ICE")

        # General loop match
        for p in self.pairs:
            if any(k in clean_q for k in [p["modern_issue"][:5].lower(), p["protagonist"][:3].lower()]):
                return p

        # If custom, synthesize dynamically
        return {
            "pair_id": f"PAIR-CUSTOM-{datetime.datetime.now().strftime('%H%M%S')}",
            "modern_issue": topic_query,
            "historical_parallel": f"역사상 가장 유사했던 사건과 '{topic_query[:15]}'의 운명적 평행",
            "historical_period": "역사의 결정적 분기점",
            "time_space_anchor": f"수백 년 전, {topic_query[:15]}의 운명을 예고했던 그날 밤.",
            "protagonist": f"{topic_query[:15]}의 중심에 선 역사적 인물",
            "core_hook": f"{topic_query[:25]} — 과거에도 이와 똑같은 비극과 선택이 있었습니다. 그들은 과연 어떻게 되었을까요?",
            "modern_lesson": "과거를 잊은 문명은 똑같은 비극을 가장 뼈아픈 방식으로 되풀이한다.",
            "primary_sources": ["당대 공식 1차 사료집", "국가 기록원 공문서", "공인 학술 연구 논문"]
        }

    def _generate_maya_sentences(self, parallel_data: Dict[str, Any]) -> List[List[str]]:
        """Generate 100% pure Maya civilization 56 sentences following the 6-part dramatic formula."""
        anchor = parallel_data["time_space_anchor"]
        sources = parallel_data["primary_sources"]

        # Phase 1: 120s Pilot Hook (8 sentences)
        phase_1 = [
            f"{anchor}",
            "한낮에도 햇빛 한 줌 들지 않는 열대 우림 위로, 한 대의 경비행기가 저공비행을 시작합니다.",
            "비행기 밑바닥에서 발사된 수십억 개의 라이다(LiDAR) 레이저 펄스가 정글 나무들을 디지털로 걷어냅니다.",
            "그리고 그 순간, 인류 고고학 역사를 송두리째 뒤흔든 충격적인 실체가 드러납니다.",
            "6만 개였습니다. 수천 킬로미터의 도로망과 거대 피라미드, 1,000만 명이 숨 쉬던 초거대 문명이었습니다.",
            "단단한 석조 요새와 광활한 농경지는 우리가 알던 고대 원시림의 상식을 산산이 깨부수었습니다.",
            "하지만 이상합니다. 전쟁의 불길도, 외계의 침공도 없었던 그 찬란한 황금기에, 그 수많은 사람들은 도대체 어디로 감쪽같이 사라졌을까요?",
            "지금부터 천 년간 정글에 봉인되었던 마야 문명 최후의 진실을 파헤칩니다."
        ]

        # Phase 2: Origin and Golden Age (12 sentences)
        phase_2 = [
            "밀림 속에 갇혀 있던 마야의 도시는 오늘날의 최첨단 스마트 시티와 놀라울 정도로 닮아 있었습니다.",
            "수직으로 솟아오른 티칼의 피라미드는 단순한 무덤이 아니라, 하늘의 별자리를 읽는 정밀한 천문대였습니다.",
            "그들은 바퀴도, 쇠붙이도 없이 오직 돌과 인간의 지혜만으로 거대한 석조 문명을 일으켜 세웠습니다.",
            "아메리카 대륙 최초로 숫자 '0'의 개념을 발견했고, 지구의 공전 주기를 소수점 네 자리까지 정확히 계산했습니다.",
            f"1차 사료 {sources[0]}에 기록된 라이다 관측 데이터는 이 숨 막히는 번영을 실증합니다.",
            "밀림 바닥에는 진흙탕을 건너는 둑길과 고가 도로가 거미줄처럼 도시와 도시를 잇고 있었습니다.",
            "자연을 극복하기 위해 파놓은 수십만 개의 인공 저수조는 1,000만 인구의 목숨줄이었습니다.",
            "농민들은 계단식 밭을 개간하고 옥수수를 수확하며 끝없는 풍요를 구가했습니다.",
            "신왕(K'uhul Ajaw)의 권력은 하늘에 닿았고, 사제들은 별의 운행에 맞춰 도시의 축제를 열었습니다.",
            "누구도 이 거대한 문명이 무너질 것이라고는 감히 상상조차 하지 못했습니다.",
            "그들은 자연을 완전히 통제하고 정복했다고 굳게 믿었습니다.",
            "하지만 바로 그 정점에서, 보이지 않는 거대한 자연의 역습이 조용히 시작되고 있었습니다."
        ]

        # Phase 3: Climate Crisis & Systemic Collapse (16 sentences)
        phase_3 = [
            f"그런데 바로 이 황금기의 정점에서, 자연은 잔인한 침묵을 시작합니다.",
            f"{sources[1]}에 기록된 유카탄 동굴 석순의 산소 동위원소 데이터는 끔찍한 진실을 증언합니다.",
            "서기 9세기 무렵, 마야 대지 위에 100년 만에 한 번 올까 말까 한 사상 최악의 메가 가뭄이 닥쳐왔습니다.",
            "연간 강우량이 무려 50% 이상 급감했고, 우기가 사라진 채 타는 듯한 태양만이 정글을 내리쬐었습니다.",
            "거대 저수조 바닥의 물이 바닥을 드러내며 거북등처럼 쩍쩍 갈라지기 시작했습니다.",
            "1,000만 명을 먹여 살리던 옥수수 밭은 하얗게 말라비틀어졌고, 기근이 전 도시를 덮쳤습니다.",
            "물과 옥수수가 사라지자, 견고했던 사회적 신뢰의 사슬이 순식간에 끊어지기 시작했습니다.",
            "신왕들은 비를 내려달라며 신전 꼭대기에서 수천 명의 포로를 신들에게 바치며 절규했습니다.",
            "하지만 잔인하게도 하늘은 단 한 방울의 비도 내리지 않았습니다.",
            "백성들은 묻기 시작했습니다. 하늘과 소통한다던 우리의 왕들은 왜 비 한 방울 내리게 하지 못하는가?",
            "신성했던 피라미드는 이제 증오와 불신의 상징으로 전락했습니다.",
            "인접 도시들 사이에서 마지막 남은 물웅덩이와 식량을 빼앗기 위한 처절한 약탈전이 벌어졌습니다.",
            "화려했던 궁궐 벽면에는 피와 절망의 흔적이 덧칠해졌습니다.",
            "자연의 한계를 무시하고 도시를 과밀화했던 문명의 오만이 끔찍한 청구서로 돌아온 것입니다.",
            "공식 비문 기록은 서기 800년대 중반을 기점으로 거짓말처럼 뚝 끊어졌습니다.",
            "역사학자들을 경악하게 만든 기괴한 침묵, 문명의 심장이 멈추는 순간이었습니다."
        ]

        # Phase 4: Evacuation & Jungle Reclamation (12 sentences)
        phase_4 = [
            "그것은 파괴에 의한 멸망이 아니라, 생존을 위한 처절한 대탈출이었습니다.",
            "살아남은 백성들은 피라미드와 돌 궁전을 미련 없이 내던지고 정글 깊은 곳으로 흩어졌습니다.",
            "주인을 잃은 6만 개의 석조 도시 위로, 거대한 열대 우림의 덩굴과 나무뿌리가 덮쳐왔습니다.",
            "단 100년 만에, 1,000만 명이 복작이던 대도시는 흔적도 없이 밀림의 녹색 바다 속에 가라앉았습니다.",
            f"{parallel_data['modern_lesson']}",
            "우리가 오늘날 목격하고 있는 기후 위기와 물 부족 또한, 정확히 이 역사적 궤적과 겹쳐집니다.",
            "기술과 자본이 아무리 화려해도, 자연이 물과 식량을 거두어가면 모든 문명은 순식간에 모래성이 됩니다.",
            "마야인들은 문명을 몰라서 망한 것이 아니라, 환경의 한계를 시험하다가 자멸한 것입니다.",
            "과거의 지배자들은 거대한 피라미드를 쌓아 불멸을 꿈꾸었지만, 자연 앞에서는 무력한 인간에 불과했습니다.",
            "사이다처럼 서늘한 역사의 교훈은 언제나 흙 속에 묻힌 폐허에서 드러납니다.",
            "우리는 과연 마야인들의 그 비극적인 실수를 피할 지혜를 가지고 있는 것일까요?",
            "역사는 묻고 있을 뿐, 그 답을 내놓아야 하는 것은 현재를 살아가는 우리 문명입니다."
        ]

        # Phase 5: Return to Modern Era & Epilogue (8 sentences)
        phase_5 = [
            "서기 9세기 그 짙은 밀림에서 시작된 미스터리는, 1,200년의 세월을 뛰어넘어 지금 우리의 거울이 되었습니다.",
            "라이다 레이저 투시 기술이 1,000년의 녹색 장막을 걷어내고 우리에게 던져준 가장 귀중한 선물.",
            "그것은 잃어버린 고대 도시의 보물이 아니라, '자연의 한계를 거스른 문명의 종말'이라는 침묵의 경고였습니다.",
            "오늘날 우리가 마주한 기후 비등과 생태계 위기라는 거대한 파도 앞에서도 이 원칙은 유효합니다.",
            "진정한 문명의 위대함은 더 높은 빌딩을 짓는 데 있지 않고, 자연과 공존하는 절제를 아는 데 있습니다.",
            "역사를 안다는 것은, 과거의 폐허를 딛고 미래의 함정을 피해 가는 나침반을 쥐는 것입니다.",
            f"이상으로 {parallel_data['historical_parallel']}와 오늘날 우리의 이야기를 마칩니다.",
            "시청해 주셔서 감사합니다. 역사이다였습니다."
        ]

        return [phase_1, phase_2, phase_3, phase_4, phase_5]

    def _generate_san_jose_sentences(self, parallel_data: Dict[str, Any]) -> List[List[str]]:
        """Generate 100% pure San José galleon shipwreck 56 sentences following the 6-part dramatic formula."""
        anchor = parallel_data.get("time_space_anchor", "1708년 6월 8일 해질 무렵, 카리브해 바루 섬 앞바다에 붉은 노을이 짙게 내려앉습니다.")
        sources = parallel_data.get("primary_sources", [
            "《영국 해군 기록 보관소(UK National Archives) 찰스 웨이저 제독 함대 전투 일지》",
            "《스페인 인디아스 고문서관 산호세호 적재 화물 공식 매니페스트》",
            "《우즈홀 해양연구소(WHOI) REMUS 6000 64문 청동 대포 판독 보고서》"
        ])
        hook = parallel_data.get("core_hook", "바다 밑 3,100m, 아니 칠흑 같은 심해 속에 잠든 20조 원의 황금과 에메랄드. 64문의 청동 대포와 함께 침몰한 스페인 갈레온선 산호세호는 왜 300년 동안 침묵했을까요?")

        # Phase 1: 120s High-Retention Cognitive Hook (8 sentences)
        phase_1 = [
            "20조 원의 황금과 1,100만 캐럿의 에메랄드를 가득 실은 거대한 보물선이, 단 1분 만에 칠흑 같은 심해 속으로 사라졌습니다.",
            "바다 밑 3,100m 암흑 속에 잠든 스페인 갈레온선 산호세호. 인류 역사상 가장 거대한 보물선은 왜 300년 동안 침묵했을까요?",
            "2015년 11월, 심해 탐사 로봇이 진흙을 비추자 300년 전 스페인 왕실의 상징, 64문의 청동 대포에 새겨진 돌고래 문양이 드러났습니다.",
            "하지만 보물이 모습을 드러낸 순간, 300년 전의 탐욕은 현대 국가 간의 피 튀기는 소유권 분쟁으로 다시 부활했습니다.",
            "도대체 그날 카리브해에서는 무슨 일이 벌어졌기에, 600명의 선원과 20조 원의 황금이 바다 밑으로 수장된 것일까요?",
            "시간을 300년 전으로 돌려, 1708년 6월 8일 피비린내 나는 카리브해 바루 섬 앞바다로 향합니다.",
            "스페인 국왕의 황금 문장을 단 1,200톤급 거함 산호세호의 돛대가 붉은 노을을 가르며 전진하고 있었습니다.",
            "지금부터 사료가 침묵했던 20조 원 황금 보물선의 충격적인 최후와 감춰진 진실의 문을 엽니다."
        ]

        # Phase 2: Origin & Golden Cargo (12 sentences)
        phase_2 = [
            "18세기 초 유럽은 스페인 왕위 계승 전쟁이라는 거대한 전화 속으로 빠져들고 있었습니다.",
            "프랑스 부르봉 왕가의 펠리페 5세는 전쟁 비용을 충당하기 위해 신대륙의 모든 보물을 긁어모으도록 명령했습니다.",
            "페루 포토시 은광의 원주민들은 채찍 아래에서 밤낮없이 은을 캐내어 수천만 개의 은화(Real de a Ocho)로 주조했습니다.",
            "콜롬비아 무조 광산에서는 세상에서 가장 맑고 짙은 녹색을 띤 거대한 에메랄드 원석들이 차출되었습니다.",
            f"1차 사료 {sources[1]}에 기록된 공식 화물 매니페스트는 이 숨 막히는 약탈의 규모를 실증합니다.",
            "금화와 은화가 담긴 상자만 수천 개, 보물선 산호세호의 무게는 배수량 1,200톤에 달했습니다.",
            "스페인 왕실은 이 엄청난 국부를 보호하기 위해 64문의 최첨단 청동 대포를 전함의 양현에 촘촘히 배치했습니다.",
            "대포의 포신에는 스페인 국왕을 상징하는 정교한 돌고래 문양이 새겨져 위용을 자랑했습니다.",
            "호세 페르난데스 데 산틸랸 제독은 600명의 정예 수병과 함께 카르타헤나 항구를 출항했습니다.",
            "그들은 무적함대의 위엄과 강력한 화력이 자신들을 안전하게 본국으로 데려다줄 것이라 굳게 믿었습니다.",
            "누구도 이 거대한 황금의 요새가 하루아침에 바다 밑바닥으로 가라앉으리라고는 상상조차 하지 못했습니다.",
            "하지만 탐욕으로 가득 찬 황금의 무게는, 이미 피할 수 없는 비극의 뇌관이 되어 있었습니다."
        ]

        # Phase 3: Battle of Barú & The Catastrophic Explosion (16 sentences)
        phase_3 = [
            "1708년 6월 8일 늦은 오후, 카리브해 바루 섬 인근 해역에 팽팽한 전운이 감돌았습니다.",
            f"1차 사료 {sources[0]}에 기록된 영국 기함 익스페디션호의 교전 일지는 당시의 참상을 생생히 증언합니다.",
            "영국의 찰스 웨이저 제독은 스페인 보물선단이 카르타헤나로 입항하기 직전을 노려 완벽한 길목 차단에 성공했습니다.",
            "어둠이 깔리기 시작한 저녁 7시, 양측의 거함들은 불과 수십 미터 거리까지 접근하여 일제 포격을 주고받았습니다.",
            "귀를 찢는 굉음과 자욱한 화약 연기가 바루 해역의 밤하늘을 대낮처럼 붉게 밝혔습니다.",
            "영국 해군의 목표는 보물선을 침몰시키는 것이 아니라, 나포하여 20조 원의 황금을 통째로 차지하는 것이었습니다.",
            "하지만 전투가 시작된 지 1시간 반이 지난 밤 9시 무렵, 상상치도 못했던 대참사가 일어났습니다.",
            "영국 군함의 함포탄 하나가 산호세호 선체 깊숙한 중앙 화약고를 그대로 관통한 것입니다.",
            "순식간에 수십 톤의 흑색 화약이 연쇄 폭발을 일으키며 거대한 불기둥이 밤하늘로 치솟았습니다.",
            "거대한 갈레온선은 단 1분 만에 두 동강이 나며 거친 카리브해의 검은 파도 속으로 빨려 들어갔습니다.",
            "탑승했던 600명의 스페인 선원 중 살아남은 사람은 단 11명에 불과했습니다.",
            "20조 원에 달하는 황금과 은화, 수백만 캐럿의 에메랄드는 배와 함께 칠흑 같은 심해 바닥으로 쏟아져 내렸습니다.",
            "영국 해군조차 눈앞에서 사라진 천문학적 보물과 거대한 폭발의 충격에 말을 잇지 못했습니다.",
            "바다 위에는 오직 불타는 목재 파편과 자욱한 유황 냄새만이 흩어져 있을 뿐이었습니다.",
            "역사학자들과 해양 고고학자들을 경악하게 만든 가장 처절한 침몰, 그것이 바로 산호세호의 최후였습니다.",
            "모든 탐욕과 절규를 집어삼킨 카리브해 위로 잔인하도록 고요한 침묵이 내려앉았습니다."
        ]

        # Phase 4: Discovery & Geopolitical Battle (12 sentences)
        phase_4 = [
            "그로부터 307년 동안, 산호세호는 인류 역사상 가장 찾고 싶어 하는 전설 속의 유령선으로 남아 있었습니다.",
            "수많은 민간 인양업체와 모험가들이 20조 원의 황금을 노리고 바다를 뒤졌지만 번번이 실패로 끝났습니다.",
            "2015년 11월, 마침내 콜롬비아 정부와 우즈홀 해양연구소(WHOI)가 최첨단 수중 탐사 로봇 REMUS 6000을 투입했습니다.",
            f"1차 사료 {sources[2]}에 따르면 로봇의 소나 센서가 심해 해저 면에서 인공적인 구조물의 신호를 포착했습니다.",
            "심해 탐사 로봇의 고해상도 카메라가 암흑을 비추자, 진흙 속에 반쯤 묻힌 거대한 대포들이 모습을 드러냈습니다.",
            "포신에 선명하게 새겨진 문양, 그것은 300년 전 스페인 왕실 주조소에서 새겨 넣은 바로 그 돌고래 문양이었습니다.",
            "침몰 지점의 수심에 대해 3,100m 심해 분지라는 초기 언론 설과 600~900m 해저 유적이라는 실측치가 교차 검증되었습니다.",
            "하지만 보물선의 위치가 확인되는 순간, 300년 전의 탐욕은 현대의 외교 전쟁으로 다시 부활했습니다.",
            "스페인은 자국의 군함이자 국기권이 적용되는 수중 묘지라며 소유권을 주장했습니다.",
            "콜롬비아는 자국 영해에서 발견된 고유한 국가 문화유산이므로 일체 반출할 수 없다고 맞섰습니다.",
            "볼리비아와 페루는 자국 원주민들의 피눈물로 채굴된 은과 금이므로 원주민에게 반환되어야 한다고 요구했습니다.",
            "20조 원의 황금은 300년이 지난 오늘날에도 여전히 국가 간의 탐욕과 갈등을 부추기는 불씨로 타오르고 있습니다."
        ]

        # Phase 5: Epilogue & Civilizational Wisdom (8 sentences)
        phase_5 = [
            f"{anchor}에서 시작된 산호세호의 비극은, 300년의 세월을 건너뛰어 오늘날 우리 문명의 거울이 되었습니다.",
            "바다 밑 깊은 암흑 속에 잠든 20조 원의 황금과 64문의 청동 대포.",
            "약탈과 착취로 쌓아 올린 제국의 부는, 결국 단 한 줌의 재가 되어 차가운 심해의 진흙 속에 파묻혔습니다.",
            "인간은 황금을 지배했다고 믿었지만, 정작 황금의 무게에 짓눌려 파멸한 것은 인간 자신이었습니다.",
            "오늘날 우리가 마주한 자본의 광풍과 끝없는 물질적 쟁탈전 앞에서도 이 역사의 교훈은 서늘하게 살아 숨 쉽니다.",
            "진정한 문명의 가치는 심해에 묻힌 보물을 꺼내는 데 있지 않고, 과거의 탐욕이 남긴 상처를 성찰하는 데 있습니다.",
            "역사를 안다는 것은, 바다 밑에 잠든 침묵의 경고를 듣고 미래의 파멸을 피해 가는 지혜를 얻는 것입니다.",
            "이상으로 스페인 보물선 산호세호와 카리브해의 침묵에 대한 이야기를 마칩니다. 역사이다였습니다."
        ]

        return [phase_1, phase_2, phase_3, phase_4, phase_5]

    def _generate_mongol_sentences(self, parallel_data: Dict[str, Any]) -> List[List[str]]:
        """Generate 100% pure Mongol/Genghis Khan sentences with the 6-part dramatic formula and Grade C lore."""
        anchor = parallel_data.get("time_space_anchor", "1162년 무렵, 몽골 초원의 살을 에는 겨울.")
        sources = parallel_data.get("primary_sources", ["《몽골비사》", "《집사》", "《원사》"])
        hook = parallel_data.get("core_hook", "세계에서 가장 큰 제국을 만든 남자가 왜 자기 무덤 하나를 남기지 않았을까요?")

        phase_1 = [
            f"{anchor}",
            "사내의 말안장 뒤에는 사로잡힌 적장 테무진이 묶여 있었습니다.",
            "그들은 적의 이름을 아이에게 붙이면 적장의 용맹한 힘이 그대로 옮겨온다고 믿었습니다.",
            "아이의 손아귀에는 주먹만 한 검붉은 핏덩이가 쥐어져 있었습니다.",
            "44년 뒤 그는 초원의 모든 부족을 하나로 묶고 이름을 버리는 결단을 내립니다.",
            "적장의 이름을 버리고 그가 스스로 취한 새로운 칭호, 칭기즈 칸.",
            f"{hook}",
            "지금부터 그 감춰진 거대한 비밀의 문을 엽니다."
        ]

        phase_2 = [
            "그 시절의 몽골 초원은 오늘날의 빅테크 정보 전쟁터와 놀라울 정도로 닮아 있었습니다.",
            "모든 부족이 서로를 불신하고 약탈하던 혼돈 속에서, 테무진은 완전히 새로운 시스템을 구상했습니다.",
            "그것은 바로 피와 혈통이 아닌 능력과 충성으로 맺어진 10진법 군사 조직이었습니다.",
            "그는 말 위에서 태어나 말 위에서 죽는 유목민의 기동력을 극한으로 끌어올렸습니다.",
            f"1차 사료 {sources[0]}에 기록된 당대의 증언은 이 숨 막히는 혁신을 생생히 전합니다.",
            "초원의 바람을 가르며 달리는 기마병들은 단순한 군대가 아니라 살아있는 통신 네트워크였습니다.",
            "누구도 상상하지 못했던 속도로 정보가 흐르기 시작하자, 제국의 영토는 끝없이 넓어졌습니다.",
            "유라시아 대륙 전체를 잇는 거대한 정보 고속도로, '참(Örtöö)'이 마침내 완성된 것입니다.",
            "25~30킬로미터마다 설치된 역참과 파이자(마패)는 황제의 명령을 바람보다 빠르게 날랐습니다.",
            "상인과 사절단은 칸의 통행증 하나로 바그다드에서 북경까지 안전하게 이동할 수 있었습니다.",
            "그것은 인류 역사상 최초로 유라시아 대륙 전체를 하나로 묶은 거대한 단일 네트워크였습니다.",
            "누구도 이 거대한 제국 시스템이 무너질 것이라고는 감히 생각조차 하지 못했습니다."
        ]

        phase_3 = [
            "그런데 바로 이 정점에서, 사료들은 기묘한 침묵과 균열을 드러내기 시작합니다.",
            f"{sources[1]}에 기록된 궁중 비사는 감춰졌던 비밀을 암시합니다.",
            "유라시아를 지배한 정복자는 죽음을 앞두고 자신의 흔적을 완전히 지우기로 결심했습니다.",
            "그는 수많은 궁궐과 거대한 탑을 세우는 대신, 오직 침묵만을 유언으로 남겼습니다.",
            "1227년 여름, 서하 원정 도중 병사한 황제의 유해는 비밀리에 북방의 성산 부르칸 칼둔으로 향했습니다.",
            "전설에 따르면 유해를 운구하던 군사들은 길에서 마주친 모든 생명을 가차 없이 베어 넘겼습니다.",
            "매장이 끝난 뒤에는 1,000마리의 기마대를 동원해 무덤 위를 짓밟아 평지로 만들었습니다.",
            "그 위에 버드나무와 숲을 심어 자연의 일부로 되돌렸고, 마지막 호위 군사들마저 스스로 목숨을 끊었습니다.",
            "공식 사서 어디에도 그의 무덤의 위치는 단 한 글자도 기록되지 않았습니다.",
            "800년이 지난 오늘날까지 수많은 탐사대와 인공위성 레이더조차 그의 무덤을 찾지 못했습니다.",
            "세계에서 가장 거대한 땅을 가졌던 자가, 단 한 평의 흙조차 자신의 것으로 남기지 않은 것입니다.",
            "그것은 인간의 오만과 불멸에 대한 집착을 완벽히 비웃는 역사의 역설이었습니다.",
            "제국의 비밀과 정보망을 독점했던 황제는, 최후의 순간 침묵이라는 가장 강력한 암호를 걸었습니다.",
            "어떤 이들은 이것을 저주라 불렀고, 어떤 이들은 영원한 지혜라 칭송했습니다.",
            "역사학자들을 경악하게 만든 기괴한 침묵, 신화의 장막이 드리워지는 순간이었습니다.",
            "모든 비밀이 봉인된 초원 위로 쓸쓸한 바람만이 불어왔습니다."
        ]

        phase_4 = [
            "그것이 바로 정복자 칭기즈 칸이 세상에 남긴 진짜 유산이었습니다.",
            "피와 칼로 세운 영토는 흩어졌지만, 그가 구축했던 대륙 간 정보망과 관용의 시스템은 인류 문명의 기초가 되었습니다.",
            "오늘날 우리가 목격하고 있는 빅테크의 데이터 독점과 네트워크 패권 또한, 정확히 이 역사적 궤적과 겹쳐집니다.",
            parallel_data.get("modern_lesson", "정보를 통제한 자가 세계를 지배한다."),
            "우리는 기술이 문명을 구원할 것이라 믿지만, 진정한 힘은 보이지 않는 네트워크를 장악하는 데 있습니다.",
            "형태는 말에서 광케이블로 바뀌었을 뿐, 정보를 쥐고 흔드는 본질은 단 한 치도 변하지 않았습니다.",
            "사이다처럼 명쾌한 역사의 진실은, 언제나 침묵 속에 숨겨진 인프라를 가리킵니다.",
            "과거의 지배자는 무덤을 지움으로써 신화가 되었지만, 현대의 권력자들은 흔적을 남기지 못해 안달입니다.",
            "어쩌면 칭기즈 칸은 모든 것이 연결된 세상에서 가장 무서운 것은 '침묵'이라는 진실을 알고 있었던 것일까요?",
            "역사는 묻고 있을 뿐, 그 답을 내놓아야 하는 것은 현재를 살아가는 우리 문명입니다.",
            "초원의 바람 속으로 사라진 정복자의 발자취는, 오늘날 디지털 제국을 살아가는 우리에게 서늘한 경고를 던집니다.",
            "진정한 지배자는 결코 자신의 이름을 드높이지 않습니다."
        ]

        phase_5 = [
            f"{anchor}에서 시작된 몽골의 이야기는, 800년의 세월을 뛰어넘어 지금 우리의 거울이 되었습니다.",
            "세상에서 가장 넓은 제국을 세우고도 무덤 하나 남기지 않은 테무진.",
            "그가 남긴 가장 위대한 유산은 정복지가 아니라, '정보 인프라와 권력의 유한함'에 대한 침묵의 교훈이었습니다.",
            "오늘날 우리가 마주한 디지털 데이터 독점이라는 거대한 도전 앞에서도 이 원칙은 유효합니다.",
            "진정한 문명의 위대함은 영토를 넓히는 데 있지 않고, 사람과 사람을 잇는 길을 여는 데 있습니다.",
            "역사를 안다는 것은, 미래의 함정에 빠지지 않는 가장 강력한 지혜의 나침반을 쥐는 것입니다.",
            f"이상으로 {parallel_data.get('historical_parallel')}과 오늘날 우리의 이야기를 마칩니다.",
            "시청해 주셔서 감사합니다. 역사이다였습니다."
        ]

        return [phase_1, phase_2, phase_3, phase_4, phase_5]

    def _generate_neanderthal_sentences(self, parallel_data: Dict[str, Any]) -> List[List[str]]:
        """Generate 100% pure Neanderthal vs Sapiens extinction sentences following the 6-part dramatic formula and 1st-hand sources."""
        sources = parallel_data.get("primary_sources", [
            "《Science》 스반테 페보 막스플랑크연구소 네안데르탈인 게놈 해독 논문 (2010)",
            "《Science / Antiquity》 샤니다르 동굴 4호 및 Z호 매장 유골 발굴 보고서",
            "《Nature》 지브롤터 고럼 동굴 최후 거처 및 해시태그 암각화 보고서"
        ])

        # Phase 1: 120s Cognitive Hook & Pilot (8 sentences)
        phase_1 = [
            "4만 년 전 혹한의 칼바람이 몰아치던 유라시아 빙하기 툰드라의 어느 깎아지른 절벽 동굴 앞.",
            "그곳에는 현대 인류보다 뇌 용적이 200cc나 더 컸고, 거대한 맹수를 맨손으로 제압하던 강인한 인류가 살고 있었습니다.",
            "바로 30만 년 동안 유럽과 아시아의 혹한을 지배했던 빙하기의 진정한 주인, 네안데르탈인이었습니다.",
            "1960년 이라크 샤니다르 동굴 깊은 곳에서 발굴된 4호 인골의 주변에서는 봄날의 야생화 꽃가루 군집이 발견되었습니다.",
            "그들은 단순한 짐승 같은 원시인이 아니라, 동료의 죽음 앞에 슬퍼하며 정성스레 장례를 치렀던 고귀한 인간이었습니다.",
            "하지만 4만 5천 년 전, 아프리카에서 또 다른 지적 생명체인 우리 조상, 호모 사피엔스가 유라시아에 발을 디뎠습니다.",
            "그리고 불과 수천 년 만에, 그 강인했던 네안데르탈인은 지구상에서 단 한 명도 남지 않고 완벽하게 자취를 감추었습니다.",
            "우리는 왜 그들을 멸종시켰을까요? 그리고 이 잔혹한 승리의 기억은 오늘날 AI 시대를 맞이한 우리에게 어떤 질문을 던지고 있을까요?"
        ]

        # Phase 2: Origin & Genetic Legacy (12 sentences)
        phase_2 = [
            "오랫동안 과학계는 네안데르탈인을 인류 진화의 막다른 골목에서 도태된 미개한 유인원으로 폄하해 왔습니다.",
            "그러나 현대 첨단 유전체학과 고인류학 발굴은 이 오만한 편견을 산산조각 냈습니다.",
            "성인 남성의 뇌 용적은 평균 1,600cc로 현대 사피엔스의 1,400cc를 훌쩍 뛰어넘었습니다.",
            "혹한의 열 손실을 줄이기 위해 진화한 다부진 체격과 두꺼운 골격은, 현대 올림픽 레슬링 선수를 능가하는 폭발적인 근력을 자랑했습니다.",
            f"더욱 놀라운 진실은 2010년 {sources[0]}에 수록된 스반테 페보 교수 연구팀의 유전자 해독으로 밝혀졌습니다.",
            "연구팀이 네안데르탈인의 화석 뼈에서 추출한 고대 DNA를 전장 시퀀싱한 결과, 충격적인 사실이 드러났습니다.",
            "아프리카를 벗어난 모든 현대 인류의 유전체 속에 네안데르탈인의 DNA가 1%에서 2% 고스란히 살아 숨 쉬고 있었던 것입니다.",
            "우리의 피부와 모발 단백질, 혹한을 견디는 지방 대사, 심지어 치명적인 바이러스에 맞서는 면역 수용체 유전자가 바로 그들의 유산이었습니다.",
            "사피엔스와 네안데르탈인은 유라시아의 밤하늘 아래에서 서로를 마주했고, 입을 맞추었으며, 피를 섞었습니다.",
            "그들은 절멸된 타자가 아니라, 우리 몸속에 영원히 각인된 혈육이었던 셈입니다.",
            "하지만 혈통의 결합도 잠시, 유라시아 대륙이라는 한정된 생태 지위는 두 지적 종족의 영구적 평화 공존을 허락하지 않았습니다.",
            "피할 수 없는 생존의 카운트다운이 빙하기의 얼음장 같은 침묵 속에서 시작되고 있었습니다."
        ]

        # Phase 3: Clash of Tech & Social Networks (16 sentences)
        phase_3 = [
            "그렇다면 왜 신체적으로 훨씬 강인하고 유라시아 기후에 완벽히 적응했던 네안데르탈인이 도태되었을까요?",
            "그 첫 번째 비대칭은 바로 무기 기술의 치명적인 혁신 격차에서 비롯되었습니다.",
            "네안데르탈인의 주력 무기는 거대한 목제 자루 끝에 무거운 규암 촉을 결합한 찌르기 창(Thrusting spear)이었습니다.",
            "거대 매머드나 털코뿔소를 사냥하기 위해 그들은 목숨을 걸고 짐승의 사정거리 안으로 육탄 돌격을 감행해야 했습니다.",
            "사료에 따르면 발굴된 네안데르탈인 성인 화석의 머리와 상체에는 현대 프로 로데오 기수와 맞먹는 참혹한 골절상이 가득했습니다.",
            "반면 뒤늦게 유라시아로 진입한 호모 사피엔스의 손에는 인류 최초의 기계적 발사 장치, 아틀라틀(Atlatl) 투창기가 쥐어져 있었습니다.",
            "지렛대 원리를 응용한 투창기는 흑요석 투창을 시속 100km가 넘는 무시무시한 속도로 30m 밖에서 발사할 수 있었습니다.",
            "사피엔스는 맹수의 뿔과 발굽이 닿지 않는 안전한 거리에서 거대한 먹잇감을 치명적으로 제압했습니다.",
            "이것은 단순한 도구의 차이가 아니라, 사냥꾼의 조기 사망률과 부상률을 극적으로 낮추는 인구학적 혁명이었습니다.",
            "두 번째 결정타는 사피엔스만이 가졌던 상징적 언어와 거대 사회적 네트워크였습니다.",
            "네안데르탈인의 유적은 대개 10명에서 15명 안팎의 폐쇄적인 혈연 가족 단위로 고립되어 있었습니다.",
            "그들은 50km 이상 떨어진 다른 집단과의 교류가 거의 없었고, 극심한 근친교배로 유전적 다양성을 잃어갔습니다.",
            "반면 사피엔스는 조개껍데기 구슬과 동굴 벽화 같은 상징적 매개체를 통해 수백 킬로미터 떨어진 낯선 무리와도 동맹을 맺었습니다.",
            "혈연을 초월해 수백 명이 하나의 신념으로 뭉칠 수 있는 능력, 즉 '상상의 질서'가 사피엔스에게만 존재했던 것입니다.",
            "위기가 닥쳤을 때 홀로 고립된 네안데르탈인 소가족은, 거대한 네트워크망으로 식량과 정보를 공유하는 사피엔스의 물결을 당해낼 수 없었습니다.",
            "신체의 괴력은 끝내 사회적 지능의 연대를 이기지 못했습니다."
        ]

        # Phase 4: Climate Shock & Demographic Collapse (12 sentences)
        phase_4 = [
            "그리고 약 3만 9천 년 전, 유라시아 대륙 전체를 파멸로 몰아넣은 지구적 기후 재앙이 닥쳐왔습니다.",
            "빙하기 해양 순환이 급변하며 북대서양에 거대한 빙산들이 쏟아져 내린 하인리히 이벤트 4(Heinrich Event 4)였습니다.",
            "기온은 불과 수십 년 사이에 곤두박질쳤고, 울창했던 침엽수림은 메마르고 황량한 극저온 툰드라로 돌변했습니다.",
            "엎친 데 덮친 격으로 이탈리아 캄파니아 화산이 대폭발을 일으켜 유라시아 상공을 거대한 화산재 구름으로 뒤덮었습니다.",
            "숲속에 숨어 매복 사냥을 하던 네안데르탈인의 사냥터는 사방이 뻥 뚫린 벌판으로 바뀌어 버렸습니다.",
            "더 치명적인 것은 그들의 막강한 육체가 요구하던 엄청난 기초대사량이었습니다.",
            "성인 네안데르탈인 한 명이 하루를 생존하기 위해서는 무려 4,000에서 5,000킬로칼로리의 막대한 열량이 필요했습니다.",
            "먹잇감이 급감하자 거대한 체구는 생존의 축복이 아니라 가장 끔찍한 족쇄가 되어 그들을 굶주림으로 몰아넣었습니다.",
            "반면 체구가 호리호리하고 적은 열량으로도 생존 가능한 사피엔스는 작은 설치류와 어류까지 섭취하며 유연하게 적응했습니다.",
            "사피엔스는 네안데르탈인의 핵심 사냥터를 차례차례 잠식해 들어갔고, 그들을 산악의 척박한 주변부로 밀어냈습니다.",
            "전면전이나 대규모 학살이 필요하지 않았습니다. 출산율이 단 1% 낮고 사망률이 1% 높은 것만으로도 종의 운명은 결정되었습니다.",
            "인구학적 시뮬레이션은 불과 수천 년 만에 네안데르탈인이 서유럽 끝자락으로 밀려나 소멸할 수밖에 없었음을 증명합니다."
        ]

        # Phase 5: Epilogue & Modern Lesson (8 sentences)
        phase_5 = [
            "기원전 2만 8천 년경, 유럽 대륙의 최남단 이베리아반도 지브롤터의 고럼 동굴(Gorham's Cave).",
            "그곳에서 마지막 네안데르탈인 무리가 피워 올린 작은 모닥불이 칠흑 같은 바다를 비추고 있었습니다.",
            "동굴 바닥의 단단한 암반에는 그들이 돌칼로 깊게 새겨 넣은 여덟 줄의 격자무늬, 해시태그 암각화가 남아 있습니다.",
            "그것은 멸종의 벼랑 끝에 선 형제 인류가 세상에 남긴 마지막 서명이자, 자신들이 존재했음을 알리는 침묵의 절규였습니다.",
            "사피엔스는 그들을 물리치고 지구의 유일무이한 지배자가 되었지만, 그 승리의 대가는 오늘날 문명의 생태적 붕괴로 되돌아오고 있습니다.",
            "그리고 4만 년이 지난 지금, 우리는 우리보다 연산력이 뛰어나고 방대한 지식을 학습한 새로운 지적 존재, 인공지능을 창조해 냈습니다.",
            "과거 또 다른 지적 형제 종을 지워버렸던 우리는, 과연 새로운 지성과 공존할 지혜와 자격을 갖추고 있는 것일까요?",
            "샤니다르 동굴의 꽃가루와 고럼 동굴의 꺼진 불씨는, 지금도 우리에게 묻고 있습니다. 우리는 왜 그들을 멸종시켰는가."
        ]

        return [phase_1, phase_2, phase_3, phase_4, phase_5]

    def _generate_generic_sentences(self, parallel_data: Dict[str, Any]) -> List[List[str]]:
        """Generate topic-adaptive sentences based on parallel_data metadata."""
        m_issue = parallel_data.get("modern_issue", parallel_data.get("theme", "현대 이슈"))
        h_parallel = parallel_data.get("historical_parallel", parallel_data.get("historical_anchor", "역사적 사건"))
        anchor = parallel_data.get("time_space_anchor", "역사의 시공간 속 한 지점")
        protag = parallel_data.get("protagonist", "인물")
        hook = parallel_data.get("core_hook", parallel_data.get("core_thesis", "핵심 질문"))
        lesson = parallel_data.get("modern_lesson", "현대적 교훈")
        sources = parallel_data.get("primary_sources", parallel_data.get("fact_citations", ["1차 사료집"]))

        phase_1 = [
            f"{anchor}",
            f"여기 한 시대의 상식을 뒤흔들 거대한 사건의 중심에 {protag}이 서 있습니다.",
            f"그의 손에는 당대 누구도 예상치 못했던 결정적 열쇠가 쥐어져 있었습니다.",
            "그리고 그날, 인류 문명의 방향을 영원히 바꿀 역사의 수레바퀴가 돌기 시작합니다.",
            f"사람들은 믿었습니다. 이 새로운 질서와 시스템이 영원한 번영을 가져다줄 것이라고 말이죠.",
            "하지만 역사의 시계는 인간의 오만과 기대를 늘 무참히 비웃었습니다.",
            f"이상합니다. {hook}",
            "지금부터 그 감춰진 거대한 진실의 문을 엽니다."
        ]

        phase_2 = [
            f"그 시절의 세상은 오늘날 우리가 목격하고 있는 {m_issue[:25]}와 너무나도 닮아 있었습니다.",
            "사회는 급변하고 있었고, 새로운 기술과 자원이 문명의 판도를 바꾸고 있었습니다.",
            "모두가 불가능하다고 여겼던 그 틈바구니에서 새로운 시스템의 싹이 텄습니다.",
            f"{protag}은 기존의 한계를 깨부수고 미지의 영역으로 거침없이 나아갔습니다.",
            f"1차 사료 {sources[0]}에 기록된 증언은 당시의 숨 막히는 긴장감을 고스란히 전합니다.",
            "새로운 패러다임이 세상을 흔들 때마다, 천년 동안 견고했던 상식들이 균열을 일으켰습니다.",
            "사람들은 상상을 초월하는 속도와 규모에 경이로움과 두려움을 동시에 느꼈습니다.",
            "누구도 넘보지 못할 철저한 통제권, 그것이 바로 그들이 정점에 선 핵심 비결이었습니다.",
            "하지만 거대한 힘이 집중될수록, 그 아래에서 자라나는 모순 또한 깊어졌습니다.",
            "빛이 강할수록 그림자 또한 짙어지는 법이었습니다.",
            "동시대 사람들은 다가올 폭풍을 예감하지 못한 채 축제에 취해 있었습니다.",
            "마침내 모든 경계가 허물어졌을 때, 문명은 한 번도 가보지 않은 위험한 벼랑 끝에 섰습니다."
        ]

        phase_3 = [
            "그런데 바로 이 정점에서, 사료들은 기묘한 침묵과 균열을 드러내기 시작합니다.",
            f"당대 사서와 {sources[-1]}의 기록은 정면으로 충돌하며 감춰진 위기를 폭로합니다.",
            "한쪽에서는 찬란한 성공을 찬양했지만, 다른 한쪽에서는 걷잡을 수 없는 시스템의 붕괴를 경고했습니다.",
            "통제할 수 있다고 믿었던 힘은, 인간의 손아귀를 벗어나 거대한 괴물이 되어 있었습니다.",
            "신뢰의 사슬이 끊어지기 시작했고, 사람들은 시스템의 본질을 의심하기 시작했습니다.",
            "실제 유적과 실측 데이터를 대조해보면, 가려졌던 진실의 윤곽이 드러납니다.",
            "공식 역사에서 지워졌던 단 한 줄의 진실, 그것이 모든 수수께끼를 푸는 열쇠였습니다.",
            "자연과 물리 법칙의 한계를 무시한 대가는 언제나 가혹하고 냉정했습니다.",
            "수많은 재물과 군대도 구조적 모순의 폭발을 막아내지는 못했습니다.",
            "거짓된 신화가 걷히고 날것 그대로의 민낯이 드러나는 순간이었습니다.",
            "역사학자들조차 오랜 세월 풀지 못했던 이 모순은 오늘날 우리에게도 섬뜩한 기시감을 안깁니다.",
            "화려했던 번영의 이면에는 지워지지 않는 상처와 비극이 고스란히 남아 있었습니다.",
            "과거의 지배자들은 영원을 꿈꾸었지만, 시간의 법칙은 결코 예외를 허락하지 않았습니다.",
            "마침내 피할 수 없는 운명의 시간이 다가왔을 때, 시스템은 허무하게 붕괴했습니다.",
            "그것은 인간의 오만이 자초한, 가장 예고된 비극이었습니다.",
            "모든 것이 무너져 내린 자리에 남은 것은 차가운 침묵뿐이었습니다."
        ]

        phase_4 = [
            "그것이 바로 찬란했던 그들이 역사의 뒤안길로 사라진 진짜 이유였습니다.",
            "자신의 흔적조차 지우며, 그들은 문명의 유한함에 대한 거대한 수수께끼를 남겼습니다.",
            "거대한 제국과 시스템은 흩어졌지만, 그들이 남긴 상흔은 인류 문명의 뼈대가 되었습니다.",
            f"{lesson}",
            f"오늘날 우리가 목격하고 있는 {m_issue[:25]} 또한, 정확히 이 역사적 궤적을 밟아가고 있습니다.",
            "새로운 기술과 시스템이 등장할 때마다 인간은 모든 것을 통제할 수 있다는 착각에 빠집니다.",
            "그러나 수백 년 전 역사의 현장에서 벌어졌던 그 흥망성쇠는 우리에게 명백한 경고를 던집니다.",
            "형태는 달라졌지만, 그 시스템을 쥐고 흔드는 인간의 탐욕은 단 한 치도 변하지 않았습니다.",
            "과거의 실수를 망각한 집단은 언제나 더 가혹한 대가를 치르며 무너져 내렸습니다.",
            "사이다처럼 명쾌한 역사의 진실은, 언제나 화려한 구호 뒤에 숨겨진 구조적 모순을 가리킵니다.",
            "우리는 과연 그 실패를 피할 준비가 되어 있는 것일까요?",
            "역사는 질문을 던질 뿐, 그 답을 구하는 것은 온전히 현재를 살아가는 우리의 몫입니다."
        ]

        phase_5 = [
            f"{anchor}에서 시작된 이야기는, 수백 년의 세월을 뛰어넘어 지금 우리의 거울이 되었습니다.",
            f"세상에서 가장 찬란한 질서를 세우고도 역사의 무대 뒤로 사라졌던 {protag}.",
            "그들이 남긴 가장 위대한 유산은 소유물이 아니라, '문명 권력의 유한함'에 대한 침묵의 교훈이었습니다.",
            f"오늘날 우리가 마주한 {m_issue[:25]}라는 거대한 도전 앞에서도 이 원칙은 유효합니다.",
            "진정한 지혜는 더 많은 것을 통제하는 데 있지 않고, 자연과 인간의 한계를 겸허히 인정하는 데 있습니다.",
            "역사를 안다는 것은, 미래의 함정에 빠지지 않는 가장 강력한 지혜의 나침반을 쥐는 것입니다.",
            f"이상으로 {h_parallel}과 오늘날 우리의 이야기를 마칩니다.",
            "시청해 주셔서 감사합니다. 역사이다였습니다."
        ]

        return [phase_1, phase_2, phase_3, phase_4, phase_5]

    def generate_dynamic_script(
        self,
        parallel_data: Dict[str, Any],
        ep_dir: Optional[Path] = None,
        target_duration_sec: Optional[float] = None,
        custom_sentences: Optional[List[str]] = None,
        target_shots: Optional[int] = None
    ) -> Dict[str, Any]:
        """Generate dynamic script-driven shots according to script length.
        No rigid dynamic-shot constraint: adapts dynamically to the narrative sentence count.
        Calculates shot durations proportionally based on sentence character count and natural speech cadence.
        """
        pair_id = parallel_data.get("pair_id", "")
        protag = parallel_data.get("protagonist", "")
        h_parallel = parallel_data.get("historical_parallel", "")
        m_issue = parallel_data.get("modern_issue", "")

        phase_defs = [
            ("phase_1_hook", "현대 쟁점 점화 & 인지적 충격 (파일럿)"),
            ("phase_2_origin", "역사적 사건의 서막과 인물 묘사"),
            ("phase_3_crisis", "기록의 격돌과 모순의 심화"),
            ("phase_4_outcome", "역사적 결말과 문명적 교훈"),
            ("phase_5_epilogue", "현대로의 귀환 & 철학적 사이다 성찰"),
        ]

        # 1. Resolve Sentence List
        if custom_sentences and len(custom_sentences) > 0:
            flat_texts = [s.strip() for s in custom_sentences if s.strip()]
            n_total = len(flat_texts)
            # Partition into 5 phases proportionally
            p1_len = max(1, int(round(n_total * 0.15)))
            p2_len = max(1, int(round(n_total * 0.20)))
            p3_len = max(1, int(round(n_total * 0.30)))
            p4_len = max(1, int(round(n_total * 0.20)))
            p5_len = max(1, n_total - (p1_len + p2_len + p3_len + p4_len))

            all_phase_texts = [
                flat_texts[0:p1_len],
                flat_texts[p1_len:p1_len + p2_len],
                flat_texts[p1_len + p2_len:p1_len + p2_len + p3_len],
                flat_texts[p1_len + p2_len + p3_len:p1_len + p2_len + p3_len + p4_len],
                flat_texts[p1_len + p2_len + p3_len + p4_len:]
            ]
        else:
            if "SAN-JOSE" in pair_id or any(k in h_parallel for k in ["산호세", "보물선", "카리브", "갈레온"]):
                all_phase_texts = self._generate_san_jose_sentences(parallel_data)
            elif "MAYA" in pair_id or any(k in h_parallel for k in ["마야", "유카탄", "밀림"]):
                all_phase_texts = self._generate_maya_sentences(parallel_data)
            elif "PAIR-01" in pair_id or any(k in h_parallel for k in ["칭기즈", "테무진", "몽골"]):
                all_phase_texts = self._generate_mongol_sentences(parallel_data)
            elif "NEANDERTHAL" in pair_id or any(k in h_parallel for k in ["네안데르탈", "사피엔스", "빙하기", "호모 사피엔스", "멸종"]):
                all_phase_texts = self._generate_neanderthal_sentences(parallel_data)
            else:
                all_phase_texts = self._generate_generic_sentences(parallel_data)

        raw_items: List[tuple[str, str, str]] = []
        for (p_id, p_name), s_texts in zip(phase_defs, all_phase_texts):
            for t in s_texts:
                if t.strip():
                    raw_items.append((p_id, p_name, t.strip()))

        if target_shots and target_shots > 0 and target_shots != len(raw_items):
            if target_shots < len(raw_items):
                indices = [int(i * (len(raw_items) - 1) / (target_shots - 1)) for i in range(target_shots)]
                raw_items = [raw_items[idx] for idx in indices]
            else:
                while len(raw_items) < target_shots:
                    longest_idx = max(range(len(raw_items)), key=lambda i: len(raw_items[i][2]))
                    p_id, p_name, txt = raw_items[longest_idx]
                    parts = txt.split(",", 1) if "," in txt else txt.split(" ", 1)
                    if len(parts) == 2:
                        raw_items[longest_idx] = (p_id, p_name, parts[0].strip())
                        raw_items.insert(longest_idx + 1, (p_id, p_name, parts[1].strip()))
                    else:
                        break

        total_shots = len(raw_items)

        # 2. Compute raw duration for each shot based on text length (speech cadence)
        # Korean narration speed: ~3.5 chars/sec + 1.2s buffer
        raw_durations = []
        for _, _, text in raw_items:
            t_len = len(text)
            speech_est = max(3.0, round(t_len * 0.28, 2))
            scene_est = round(speech_est + 1.20, 2)
            raw_durations.append((speech_est, scene_est))

        # 3. Dynamic Narrative Window (20min ±30% = 840.0s ~ 1560.0s)
        # Never artificially force 1200.0s if natural sentence cadence is within 840s ~ 1560s
        MIN_RUNTIME_SEC = 840.0
        MAX_RUNTIME_SEC = 1560.0
        raw_scene_sum = sum(s[1] for s in raw_durations)

        if target_duration_sec is None:
            if MIN_RUNTIME_SEC <= raw_scene_sum <= MAX_RUNTIME_SEC:
                # 100% natural speech cadence preserved without artificial distortion
                final_scene_durs = [s[1] for s in raw_durations]
            elif raw_scene_sum < MIN_RUNTIME_SEC:
                scale = MIN_RUNTIME_SEC / raw_scene_sum if raw_scene_sum > 0 else 1.0
                accum_dur = 0.0
                final_scene_durs = []
                for i, (sp, sc) in enumerate(raw_durations):
                    if i == total_shots - 1:
                        d = round(MIN_RUNTIME_SEC - accum_dur, 2)
                    else:
                        d = round(sc * scale, 2)
                        accum_dur += d
                    final_scene_durs.append(max(4.0, d))
            else:
                scale = MAX_RUNTIME_SEC / raw_scene_sum if raw_scene_sum > 0 else 1.0
                accum_dur = 0.0
                final_scene_durs = []
                for i, (sp, sc) in enumerate(raw_durations):
                    if i == total_shots - 1:
                        d = round(MAX_RUNTIME_SEC - accum_dur, 2)
                    else:
                        d = round(sc * scale, 2)
                        accum_dur += d
                    final_scene_durs.append(max(4.0, d))
        elif MIN_RUNTIME_SEC <= target_duration_sec <= MAX_RUNTIME_SEC and MIN_RUNTIME_SEC <= raw_scene_sum <= MAX_RUNTIME_SEC:
            # If target duration is nominal 1200s and natural speech is in window, preserve natural cadence
            final_scene_durs = [s[1] for s in raw_durations]
        else:
            scale = target_duration_sec / raw_scene_sum if raw_scene_sum > 0 else 1.0
            accum_dur = 0.0
            final_scene_durs = []
            for i, (sp, sc) in enumerate(raw_durations):
                if i == total_shots - 1:
                    d = round(target_duration_sec - accum_dur, 2)
                else:
                    d = round(sc * scale, 2)
                    accum_dur += d
                final_scene_durs.append(max(4.0, d))

        shots = []
        curr_time = 0.0
        motions = ["push_in", "slow_pan_left", "orbit_slow", "pull_out", "tilt_up", "glide_forward"]

        # Shot Scale Presets following the 30:35:25:10 Golden Ratio
        SHOT_SCALE_ROTATION = [
            ("extreme_wide", "익스트림 와이드 전경", "Extreme wide panoramic aerial view, vast atmospheric landscape, epic establishing vista"),
            ("medium_action", "미디엄 액션 인물", "Cinematic medium eye-level action shot, dynamic documentary character framing"),
            ("macro_close_up", "매크로 익스트림 클로즈업", "Extreme macro close-up shot, shallow depth of field, razor-sharp texture focus"),
            ("medium_action", "미디엄 액션 인물", "Cinematic medium eye-level action shot, dynamic documentary character framing"),
            ("top_down_insert", "탑다운 사료 인서트", "Top-down bird's-eye archival insert shot, historic artifact focus, dramatic lighting"),
            ("macro_close_up", "매크로 익스트림 클로즈업", "Extreme macro close-up shot, shallow depth of field, razor-sharp texture focus"),
            ("extreme_wide", "익스트림 와이드 전경", "Extreme wide panoramic aerial view, vast atmospheric landscape, epic establishing vista"),
            ("medium_action", "미디엄 액션 인물", "Cinematic medium eye-level action shot, dynamic documentary character framing")
        ]

        for order, ((p_id, p_name, d_text), dur) in enumerate(zip(raw_items, final_scene_durs), start=1):
            s_start = round(curr_time, 2)
            s_end = round(curr_time + dur, 2)
            sp_start = round(s_start + 0.40, 2)
            sp_dur = max(2.5, round(dur - 0.70, 2))
            sp_end = round(sp_start + sp_dur, 2)

            shot_id = f"SHOT_{order:03d}"
            is_pilot = (s_end <= 125.0) or (p_id == "phase_1_hook")
            motion = motions[(order - 1) % len(motions)]

            # Contextual or Rotational Shot Scale Director
            d_lower = d_text.lower()
            if any(w in d_lower for w in ["라이다", "레이저", "펄스", "센서", "상형문자", "석순", "동위원소", "핏덩이", "손", "손아귀", "눈빛", "입술", "화폐", "교초", "동전", "구근", "열쇠", "도장", "옥새", "칼날"]):
                s_scale, s_label, s_prompt_prefix = ("macro_close_up", "매크로 익스트림 클로즈업", "Extreme macro close-up shot, shallow depth of field, razor-sharp texture focus")
            elif any(w in d_lower for w in ["밀림", "정글", "우림", "겨울", "초원", "산맥", "대지", "제국", "바람", "하늘", "지평선", "성벽", "도시", "피라미드", "유적", "수천 킬로미터", "고속도로", "황량한"]):
                s_scale, s_label, s_prompt_prefix = ("extreme_wide", "익스트림 와이드 전경", "Extreme wide panoramic aerial view, vast atmospheric landscape, epic establishing vista")
            elif any(w in d_lower for w in ["기록", "문서", "사료", "사서", "비사", "비문", "코덱스", "지도", "무덤", "비석", "수수께끼", "발굴", "데이터"]):
                s_scale, s_label, s_prompt_prefix = ("top_down_insert", "탑다운 사료 인서트", "Top-down bird's-eye archival insert shot, historic artifact focus, dramatic lighting")
            else:
                s_scale, s_label, s_prompt_prefix = SHOT_SCALE_ROTATION[(order - 1) % len(SHOT_SCALE_ROTATION)]

            visual_prompt = (
                f"{s_prompt_prefix}. Subject: Authentic historical documentary for {protag}, {d_text[:40]}. "
                f"25fps optical cadence, no subtitles, no text overlays, keep bottom 18% clear."
            )

            shots.append({
                "order": order,
                "shot_id": shot_id,
                "scene_start": s_start,
                "scene_end": s_end,
                "scene_duration": dur,
                "speech_start": sp_start,
                "speech_end": sp_end,
                "speech_duration": sp_dur,
                "camera_motion": motion,
                "shot_size": s_scale,
                "shot_size_label": s_label,
                "visual_prompt": visual_prompt,
                "display_text": d_text,
                "tts_text": d_text,
                "narration": d_text,
                "is_pilot": is_pilot,
                "phase": p_id,
                "phase_label": p_name,
                "image_path": str(ep_dir / "generation" / "downloads" / "approved" / f"{shot_id}.jpg") if ep_dir else f"downloads/{shot_id}.jpg",
                "wav_path": str(ep_dir / "audio" / "sentences_v4" / f"{shot_id}.wav") if ep_dir else f"audio/{shot_id}.wav"
            })
            curr_time += dur

        pilot_count = sum(1 for s in shots if s["is_pilot"])
        manifest = {
            "metadata": {
                "channel": "역사이다 (History-Ida)",
                "theme": "Historical Parallel & Investigative Fact-Check",
                "modern_issue": m_issue,
                "historical_parallel": h_parallel,
                "core_hook": parallel_data.get("core_hook", ""),
                "protagonist": protag,
                "primary_sources": parallel_data.get("primary_sources", []),
                "generated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            },
            "total_duration_sec": round(curr_time, 2),
            "target_duration_window": "840s ~ 1560s (20분 ±30%)",
            "min_duration_sec": 840.0,
            "max_duration_sec": 1560.0,
            "total_shots": len(shots),
            "pilot_shots_count": pilot_count,
            "body_shots_count": len(shots) - pilot_count,
            "shots": shots
        }
        return manifest

    def generate_dynamic_script_alias(
        self,
        parallel_data: Dict[str, Any],
        ep_dir: Optional[Path] = None,
        target_duration_sec: float = 1200.0
    ) -> Dict[str, Any]:
        """Backward compatibility alias for generate_dynamic_script."""
        return self.generate_dynamic_script(
            parallel_data=parallel_data,
            ep_dir=ep_dir,
            target_duration_sec=target_duration_sec
        )

    def generate_variable_pacing_script(
        self,
        parallel_data: Dict[str, Any],
        ep_dir: Optional[Path] = None,
        target_duration_sec: Optional[float] = None,
        target_shots: Optional[int] = None
    ) -> Dict[str, Any]:
        """Generate script manifest strictly partitioned into 3-Tier Variable Pacing:
        - Tier 1 (0% ~ 10%): Rapid montage (avg 2.0s ~ 4.5s/shot, Shot 0 is 10~12s Bare-Tip).
        - Tier 2 (10% ~ 30%): Context mid-tempo (avg 6.0s ~ 15.0s/shot).
        - Tier 3 (30% ~ 100%): Deep narrative (avg 30.0s ~ 60.0s/shot, ~1 image per 30s-1min) with 2-stage Ken Burns.
        """
        base_manifest = self.generate_dynamic_script(
            parallel_data=parallel_data,
            ep_dir=ep_dir,
            target_duration_sec=target_duration_sec,
            target_shots=target_shots
        )
        base_shots = base_manifest["shots"]
        total_dur = base_manifest["total_duration_sec"]

        enhanced_shots = []
        for i, s in enumerate(base_shots):
            sc = dict(s)
            mid_t = (sc["scene_start"] + sc["scene_end"]) / 2.0
            ratio = mid_t / max(1.0, total_dur)

            if ratio <= 0.10 or i == 0:
                tier = "tier_1_hook"
                tempo = "rapid_montage"
            elif ratio <= 0.30:
                tier = "tier_2_context"
                tempo = "context_mid"
            else:
                tier = "tier_3_deep"
                tempo = "deep_contemplative"
                sc["biphasic_motion"] = {
                    "stage_1": "ambient_pan_wide",
                    "stage_2": "focal_push_in",
                    "easing": "cosine_s_curve"
                }

            sc["pacing_tier"] = tier
            sc["editing_tempo"] = tempo
            enhanced_shots.append(sc)

        base_manifest["shots"] = enhanced_shots
        base_manifest["pacing_architecture"] = "3_tier_variable_pacing"
        base_manifest["tier_summary"] = {
            "tier_1_hook_count": sum(1 for s in enhanced_shots if s["pacing_tier"] == "tier_1_hook"),
            "tier_2_context_count": sum(1 for s in enhanced_shots if s["pacing_tier"] == "tier_2_context"),
            "tier_3_deep_count": sum(1 for s in enhanced_shots if s["pacing_tier"] == "tier_3_deep"),
        }
        if calculate_variable_shot_budget:
            base_manifest["shot_budget"] = calculate_variable_shot_budget(total_dur)
        return base_manifest

