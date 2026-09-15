# EP02 v6 fact-bound expansion task

Read these repository files completely before producing the response:

- `human_archive/runs/ep02_jang_huibin/full-v5-001/source/script_candidate.json`
- `human_archive/runs/ep02_jang_huibin/full-v5-001/source/claim_inventory_v2.json`
- `human_archive/runs/ep02_jang_huibin/source/source_snapshot_manifest_v2.json`
- `human_archive/config/seonbi_narration_policy.yaml`
- `human_archive/schemas/script_expansion_v1.schema.json`

Return only a JSON object accepted by `script_expansion_v1.schema.json`.

## Immutable contract

- `episode_id`: `HA002`
- `base_script_sha256`: `962576c781176bd689aa63159b643db12a5e004f76d4103bacd770aa9af77bc7`
- `target_duration_sec`: `1080`
- Produce exactly seven blocks, one for each allowed anchor, in chapter order.
- Produce exactly 13 sentences per block, 91 new sentences total.
- IDs are consecutive `HA002-V6-N001` through `HA002-V6-N091`.
- `order` values are consecutive 127 through 217. The compiler will assign final playback order.
- Every sentence is 10–45 Korean characters and `display_text`, `tts_text`, and the single segment `text` are identical.
- Do not rewrite or repeat any existing sentence. The expansion compiler inserts only these new rows.

## Evidence rules

- Use only the seven claims and evidence spans in the supplied inventory.
- A `fact` or `direct_quote` segment must include its exact `claim_id` and only evidence IDs listed for that claim.
- Every segment must emit both evidence fields. For a non-claim segment use `"claim_id": null` and `"evidence_span_ids": []`; for a claim-bound segment use the exact claim ID and one or more allowed evidence IDs.
- A transition, analogy, source commentary, or insight without a claim must not introduce a new date, person, place, event, quotation, motive, or causal fact.
- Do not upgrade interpretation into fact. Use phrases such as `기록으로 확인되는 범위`, `이 대목에서 읽을 수 있는 점`, or `제가 보기엔` for bounded analysis.
- Do not invent dialogue, physical actions, emotions, scenery, chronology, or biographical detail.
- Do not state that the shamanic incident was wholly fabricated; do not state that all ministers agreed; do not describe forced poison administration.

## Style and diversity rules

- Match the existing Archivist-Seonbi tone, but do not repeat `허허, 천만의 말씀!` or either existing outro.
- Avoid sentence templates repeated with only one noun changed.
- No exact or normalized duplicate sentence.
- Use at most eight analogy sentences across all blocks; mark every analogy as explanatory rather than source wording.
- Keep source literacy, political structure, and human dignity concrete. Avoid generic filler such as `역사는 중요합니다`.
- Each block should move from evidence to limits, then interpretation, then a transition back to the existing chapter.

## Block topics

1. After `HA002-S018`, chapter 1: why official records, administrative diaries, and later narrative have different evidentiary weight; what absence can and cannot prove. Use `CLM-JH-001` where factual.
2. After `HA002-S036`, chapter 2: exactly what the shrine and buried-object record establishes and what it does not establish. Use `CLM-JH-005` and contrast carefully with `CLM-JH-001`.
3. After `HA002-S054`, chapter 3: distinguish accusation, factional support, political justification, and royal decision. Use `CLM-JH-006` and `CLM-JH-003`.
4. After `HA002-S072`, chapter 4: explain why Choe Seok-hang's opposition matters and how it disproves unanimity without inventing debate detail. Use `CLM-JH-007`.
5. After `HA002-S090`, chapter 5: read the wording of self-termination, execution, dignity, and palace solemnity without softening the death sentence. Use `CLM-JH-002` and `CLM-JH-001`.
6. After `HA002-S108`, chapter 6: connect the permanent ban on concubine elevation to the political-structure interpretation without claiming more than the sources. Use `CLM-JH-004` and `CLM-JH-003`.
7. After `HA002-S124`, chapter 7: synthesize source criticism, responsibility, political structure, later storytelling, and human dignity. Reuse claims only when needed; finish by handing naturally to the two existing outro sentences.

Before returning JSON, silently verify all 91 IDs, all seven anchors, chapter consistency, evidence membership, sentence limits, and duplicate absence.
