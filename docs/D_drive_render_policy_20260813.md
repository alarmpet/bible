# D 드라이브 산출물 고정 정책

- 최종 영상: `D:\bible_healing_ep01\final\`
- 인코딩 임시 파일·concat 목록: `D:\bible_healing_ep01\work\`
- C 드라이브는 프로젝트 원본, 대본, 장면 음성, 자막 원천만 보관한다.
- 최종 렌더는 `full-authoritative-audio.wav`를 오디오 기준으로 사용한다.
- 기존 MP4에 포함된 과거 오디오를 재사용하지 않는다.
- 렌더 완료 전 `moov atom`, 영상 길이, 오디오 스트림, 자막 마지막 시각을 검증한다.
