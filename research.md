# 구약 힐링 첫 1분 훅·진성 엠비언트 조사 노트

> 조사일: 2026-08-11  
> 용도: `계획서_구약힐링_첫1분훅_진성엠비언트.md` 개정 근거  
> 주의: 커뮤니티 글은 사용자 언어를 이해하기 위한 정성 자료이며 일반화 가능한 효과 근거가 아니다.

## 1. 저장소 실측

`bible_healing/runs/ep01_anxious_night/hermes_jobs/full/scene_audio_manifest.json`과 `scenes.json`을 대조했다.

| 구간 | 실제 시간 |
|---|---:|
| `open_01` | 0.00–21.76초 |
| `open_02` | 21.76–48.20초 |
| `u01_n0` 공감·말씀 안내 | 48.20–90.68초 |
| 첫 성경 낭독 `u01_s0` | **90.68초 시작** |

현재 첫 48.2초는 채널 성격 설명과 호흡 안내가 중심이고, “불을 껐는데 머릿속만 환한 밤”이라는 구체 공감은 48초 이후에 나온다. 첫 말씀까지 1분 30.68초가 걸린다.

## 2. YouTube 공식 근거

- YouTube는 Intro 지표를 **첫 30초 후에도 남아 있는 시청자의 비율**로 정의한다. 높은 Intro 비율은 첫 30초가 제목·썸네일의 기대와 맞고 관심을 유지했을 가능성을 뜻한다. 첫 30초 스타일을 실험하라고 권한다.  
  출처: [Measure key moments for audience retention](https://support.google.com/youtube/answer/9314415)
- 추천 시스템 설명에서도 초기 몇 초에 시청자가 머물지 결정하며, 인트로가 제목·썸네일의 약속을 즉시 전달하고 곧바로 가치를 제공해야 한다고 안내한다.  
  출처: [Understand your content performance for YouTube’s recommendation system](https://support.google.com/youtube/answer/16559650)

설계 해석: 이 영상의 클릭 약속이 “불안한 밤을 위한 말씀·위로”라면 채널 소개보다 먼저 불안한 밤을 구체적으로 비추고, 곧 말씀을 들을 수 있다는 확신을 줘야 한다.

## 3. 불안·수면·공감 언어 근거

- 불면 모델 연구에서는 걱정과 반추 같은 반복적 부정 사고가 수면 문제와 연관된 주요 인지 각성으로 다뤄진다.  
  출처: [Cognitive factors and processes in models of insomnia: a systematic review](https://pmc.ncbi.nlm.nih.gov/articles/PMC10909484/)
- 감정을 말로 붙이는 affect labeling은 부정 정서를 조절하는 전략으로 연구돼 왔다. 이는 “당신은 불안합니다”라고 진단하라는 뜻이 아니라, 시청자가 이미 경험하는 장면과 감정을 짧고 구체적으로 비추는 설계를 지지한다.  
  출처: [Feelings Into Words: Contributions of Language to Exposure Therapy](https://pmc.ncbi.nlm.nih.gov/articles/PMC4721564/), [Putting feelings into words](https://pubmed.ncbi.nlm.nih.gov/17576282/)
- NHS는 밤의 걱정을 무조건 멈추라고 강요하기보다 걱정을 알아차리고 현재로 돌아오는 전략, 호흡·마음챙김 같은 선택지를 소개한다. 수면 자체를 목표로 압박하면 긴장과 불안이 커질 수 있다고 설명한다.  
  출처: [Tackling your worries](https://www.nhs.uk/every-mind-matters/mental-wellbeing-tips/self-help-cbt-techniques/tackling-your-worries/), [Worrying about sleep](https://oxfordhealth.nhs.uk/camhs/self-care/sleep/anxiety-worry/worrying-about-sleep/)
- 느린 호흡 연구는 이완·자율신경 변화 가능성을 지지하지만 개인차가 있고 임상적 치료 효과를 보장하지 않는다. 따라서 오프닝의 호흡은 명령형이 아니라 선택형이어야 한다.  
  출처: [The physiological effects of slow breathing in the healthy human](https://pmc.ncbi.nlm.nih.gov/articles/PMC5709795/), [Breathwork interventions for diagnosed anxiety disorders](https://pmc.ncbi.nlm.nih.gov/articles/PMC9954474/)

## 4. Reddit 정성 자료

다음 표현이 여러 불안·수면 게시물에서 반복됐다.

- 피곤하지만 머리가 멈추지 않음
- 내일 할 일과 과거 실수를 반복해서 생각함
- 심장이 빨리 뛰거나 몸이 긴장함
- 혼자 깨어 있다는 고립감
- 화면을 보기보다 편안한 말이나 소리를 틀어 놓음

참고 스레드:

- [When anxiety prevents you from falling asleep at night](https://www.reddit.com/r/Anxiety/comments/1mhp3pg)
- [Anxious night](https://www.reddit.com/r/Anxiety/comments/114932l)
- [What do you do when you can’t sleep due to anxiety?](https://www.reddit.com/r/Anxiety/comments/17tbmsu/)
- [I hate how my brain never shuts off at night](https://www.reddit.com/r/Anxiety/comments/1nq3ien/)

설계 해석: “불안은 실패가 아니다” 같은 설명보다 “불을 껐는데 머릿속은 아직 환한 밤”처럼 경험을 먼저 비추는 편이 시청자의 자기 인식을 빠르게 만든다. 이는 정성적 가설이며 업로드 후 유지율로 검증해야 한다.

## 5. GitHub·FFmpeg 기술 조사

- FFmpeg는 반복 입력, 복합 필터, `xfade` 등으로 루프 영상과 전환을 구성할 수 있다.  
  출처: [FFmpeg 공식 문서](https://ffmpeg.org/ffmpeg-all.html)
- GitHub 공개 예제에서는 `-stream_loop -1`을 이용한 무한 반복과 정방향·역방향을 붙이는 bounce loop가 사용된다.  
  참고: [Create a bounce loop using ffmpeg](https://gist.github.com/drikusroor/80970258181c548249f2fd34c1b9d4b7), [Infinite looping stream example](https://gist.github.com/shinroo/84a206b4e9e8971db542e2243c7f5a20)

설계 해석: 단순 반복은 가능하지만, 불꽃·빗방울처럼 방향성이 있는 영상에 bounce loop를 쓰면 역재생이 눈에 띌 수 있다. 에셋 자체의 seamless 여부를 먼저 검사하고, 플레이트 경계 전환은 오디오를 건드리지 않는 별도 영상 필터로 처리해야 한다.

## 6. Threads 조사 상태

Threads의 공개 게시물은 검색엔진에서 안정적으로 색인·검증되는 관련 결과를 확보하지 못했다. 출처를 채우기 위해 인용하지 않는다. 추후 사용자가 제공한 Threads URL 또는 접근 가능한 게시물 묶음이 있을 때 별도 정성 분석한다.

## 7. 조사에서 도출한 결정

1. 훅의 중심은 자극·공포가 아니라 **정확한 감정 미러링**이다.
2. 흐름은 **공감받음 → 혼자가 아님 → 지금 해결하지 않아도 됨 → 첫 말씀**으로 한다.
3. 첫 성경 낭독은 현재 90.68초에서 **45–55초**로 앞당긴다.
4. 첫 30초에는 채널 설명·저작권·구독 요청·효과 보장을 넣지 않는다.
5. 호흡 안내는 “가능하다면/편하다면”으로 선택권을 주고 1회만 둔다.
6. “치유된다·잠들게 한다”는 결과 약속 대신 “말씀을 천천히 듣는 자리”를 약속한다.
7. 성과는 30초 유지율, 첫 말씀 진입 유지율, 60초 유지율과 시청자 피드백으로 검증한다.

