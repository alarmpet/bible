# movie-sample 1분 핑퐁 루프 실행 로그

## 적용 대상

`C:/Users/amd/module/bible_healing/assets/movie-sample/*.mp4`에 있던 12개 영상.

## 생성 방식

각 원본을 다음 구조로 변환했다.

```text
정방향 → 역방향 → 정방향 → 역방향
```

각 사이클을 반복해 최종 길이를 정확히 60초로 맞췄다. 음성은 제거해 순수 백그라운드 영상 자산으로 만들었다. 본편에서는 별도의 목회자 음성·자막 트랙을 얹는다.

## 출력 위치

`C:/Users/amd/module/bible_healing/assets/movie-sample/pingpong-1min/`

파일명은 원본명 뒤에 `_pingpong_1min.mp4`를 붙였다.

## 검증

- 출력 개수: 12개
- 각 출력 길이: 60.000초
- 코덱: H.264
- 원본 순서: 정방향·역방향을 한 사이클로 구성
- 검증 스크립트: `bible_healing/scripts/build_movie_sample_pingpong_1min_resume.py`
