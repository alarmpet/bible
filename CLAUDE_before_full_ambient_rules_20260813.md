# 구약 힐링 영상 프로젝트 작업 규칙

이 문서는 `C:\Users\amd\module` 프로젝트 전용 지침이다. 상위·외부 프로젝트인 `C:\Users\amd\hermes\CLAUDE.md`의 규칙을 이 프로젝트에 자동으로 상속하지 않는다.

## 작업 전 필수 확인

1. `manual.md`
2. `research.md`
3. `bible_healing/config/final_render_policy.json`
4. `bible_healing/scripts/final_render_preflight.py`
5. `bible_healing/scripts/final_background_preflight.py`

문서 규칙과 실행 정책이 다르면 실행 정책을 기준으로 삼되, 반드시 문서도 함께 수정한다.

## 배경영상 규칙

- 최종영상 배경은 반드시 `bible_healing/assets/movie-sample/pingpong-1min/*.mp4`에서 선택한다.
- 각 배경은 1분 길이의 앰비언트 영상이며 정방향·역방향 핑퐁 루프가 적용된 파일이다.
- `scene_*_flow.jpg`, `bg_*.jpg`, 정지 이미지, 단색 plate를 최종 배경으로 사용하지 않는다.
- 최종 렌더 전에 다음 검사를 실행한다.

```powershell
python bible_healing/scripts/final_background_preflight.py
python bible_healing/scripts/final_render_preflight.py
```

검사 실패 시 렌더를 시작하지 않는다.

## 음성 규칙

- 허용 화자는 `narrator`와 `scripture`뿐이다.
- 남성 성경 낭독은 승인된 M4 설정을 사용한다.
- 속도 0.72, pitch -8%, 낮고 인자하며 안정적인 톤을 유지한다.
- 성경 본문에서 괄호 설명, 곡 제목, 셀라·첼라, 느낌표를 제거한다.
- 종결 표현 뒤에는 실제 음성 쉼을 넣는다.

## 자막 규칙

- 롱폼 균형형 자막을 사용한다.
- 최대 2줄, 한 줄 최대 20자다.
- 자막은 실제 오디오 세그먼트 시작·종료 시각을 따른다.
- 장면 전체 시각을 여러 자막에 재사용하지 않는다.
- 자막 크기와 위치를 영상 전체에서 고정한다.

## 챕터 표시 규칙

- 우측 상단에 현재 주제 확인용으로 표시한다.
- 최대 한 줄, 최대 12자, 1080p 기준 36px 이하로 한다.
- 자막보다 작게 표시한다.
- 영상에서 사라지지 않고 주제가 바뀔 때 문구만 교체한다.

## 결과물 보호

- 기존 영상·원본 에셋·설정·매뉴얼을 덮어쓰지 않는다.
- 새 렌더는 별도 파일명으로 만든다.
- 불완전한 렌더 파일은 검증 전에 배포본으로 보고하지 않는다.
- 최종 보고에는 배경 MP4 경로, 영상 길이, 코덱, 자막 검사 결과를 기록한다.
