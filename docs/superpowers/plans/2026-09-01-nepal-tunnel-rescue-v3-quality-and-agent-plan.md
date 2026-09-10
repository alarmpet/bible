# Nepal Tunnel Rescue V3 Quality And Agent Plan

Date: 2026-09-01
Scope: `nepal-tunnel-rescue` V2 output review and V3 production plan
Goal: raise subtitle readability, sentence-to-visual semantic alignment, factual clarity, and multi-agent verification quality while enforcing a runtime target of 20 minutes ±30%.

## 1. Current Defects With Evidence

### 1.1 Subtitle readability

Confirmed from sampled rendered frames:

- Subtitle text is visually too small for mobile-first viewing.
- The current output appears to prioritize single-line subtitles even when the sentence length pushes readability down.
- Bottom placement is mostly within a safe area, but safe placement alone does not solve legibility.
- White-on-dark contrast is acceptable, but the outline and weight are not strong enough when thin line art is behind the subtitle.

Observed symptoms from the sampled 2640x1080 frames:

- Estimated visible subtitle height is roughly `45px to 55px`.
- That is about `4% to 5%` of frame height, which is below a comfortable mobile documentary target.
- Long Korean sentences with dates, place names, and proper nouns are compressed into one line too often.

Implication:

- V2 likely passes a basic safe-area check but fails a strict readability check.

### 1.2 Sentence-image mismatch

Confirmed from sampled frames:

- A sentence about where the event began in the Bhotekoshi and Trishuli river basin was paired with a chart-like rising line on a grid.
- A sentence about the 60MW Upper Trishuli 3A project was paired with abstract geometric shapes instead of infrastructure, river, tunnel, or plant logic.
- A sentence stressing the danger of "hundreds of people" was paired with three colored cards and dots, which weakens the scale and human meaning.
- The tunnel blockage sentence was the best match in the sample, but still rendered as an abstract water-and-blocks motif rather than a clearly readable tunnel cross-section.

Implication:

- V2 frequently maps surface keywords to generic visual roles instead of expressing the sentence's concrete subject, action, place, and risk.
- Style consistency is currently stronger than semantic accuracy.

### 1.3 Visual style and composition repetition

Confirmed from sampled frames:

- Repeated use of a dark navy background with cyan and orange accents.
- Repeated use of thin abstract line work, wide negative space, and centered compositions.
- Low object density across multiple shots.

Implication:

- The package has aesthetic consistency, but too many distinct facts collapse into the same visual vocabulary.
- Shot-to-shot distinction is weak, reducing both information density and audience trust.

### 1.4 Factual misunderstanding risk

Confirmed risk types:

- Location and basin sentences can be misread as charts or trends.
- Facility-specific sentences can look like decorative geometry rather than physical infrastructure.
- Human-scale danger can be reduced to symbolic counting rather than real stakes.

Implication:

- V2 contains medium-risk frames where viewers may not learn the intended fact even if the narration is correct.

## 2. Runtime Constraint

The project must target an actual delivered runtime of 20 minutes within ±30%.

- Minimum allowed runtime: `14 minutes`
- Target runtime: `20 minutes`
- Maximum allowed runtime: `26 minutes`

Rules:

- A script draft cannot progress to full image generation if its estimated runtime falls outside `14 to 26 minutes`.
- The estimate must be computed from the actual TTS-ready narration text, not from bullet summaries.
- Final rendered runtime must remain inside the same range after pacing, pauses, and transitions are added.

## 3. Subtitle Specification For V3

V3 subtitle standards:

- Base canvas assumption: 1080p landscape master
- Minimum subtitle font size: `64px`
- Recommended subtitle font size: `72px to 84px`
- Maximum lines: `2`
- Preferred lines: `1 to 2`, never force `1` if readability drops
- Bottom safe margin: at least `6%` of frame height
- Left and right safe margin: at least `8%` of frame width
- Stroke or shadow: mandatory, strong enough to survive thin-line backgrounds
- Subtitle width rule: no line should exceed a comfortable read width for mobile playback
- Proper noun rule: dates, place names, person counts, and project names get priority for line breaks

Acceptance gate:

- Every shot must pass a mobile-size legibility review at a reduced preview scale before final export.

## 4. Sentence-To-Visual Redesign

Each narration sentence must be transformed into a structured visual brief before asset generation.

Required fields per sentence:

- `sentence_id`
- `sentence_text`
- `source_basis`
- `fact_type`
- `visual_role`
- `must_include`
- `must_avoid`
- `factual_risk`
- `emotional_goal`
- `subtitle_length_class`
- `candidate_asset_modes`

### 4.1 Visual role taxonomy

Allowed primary visual roles:

- `map_context`
- `timeline_context`
- `facility_explainer`
- `tunnel_cross_section`
- `people_at_risk`
- `flood_dynamics`
- `rescue_sequence`
- `data_annotation`
- `aftermath_context`

Rules:

- River basin or location sentences default to `map_context`, not chart motifs.
- Infrastructure sentences default to `facility_explainer` or `tunnel_cross_section`.
- Human-scale risk sentences default to `people_at_risk` with count and crowd logic, not generic symbols.
- Physical blockage sentences default to `tunnel_cross_section` or `rescue_sequence`.
- `data_annotation` is allowed only when the line explicitly discusses measured change, counts, comparison, capacity, or chronology.

### 4.2 Example repairs for the sampled failures

Sentence: event began in the Bhotekoshi and Trishuli river basin

- Replace chart-like line graphic with a labeled map or simplified topographic basin view.
- Must include river names, upstream/downstream direction, and rain/flood trigger context.
- Must avoid stock market or trend-chart composition cues.

Sentence: 60MW Upper Trishuli 3A

- Replace abstract ellipse-and-bars composition with a dam or hydropower schematic, tunnel entrance, river alignment, or construction section.
- Must include one concrete physical cue that makes it legible as infrastructure.

Sentence: the dangerous word is "hundreds"

- Replace colored cards with people-scale visualization, evacuation density, rescue count framing, or worker grouping.
- Must include a sense of risk magnitude rather than symbolic counting alone.

Sentence: water, mud, and boulders blocked the tunnel again

- Keep the water-and-obstruction concept, but convert it to a tunnel cutaway with directionality, blockage depth, and access constraint.

## 5. Competitive And Cross-Validation Agent Structure

V3 should not rely on a single generator plus weak polish. It needs a competitive, scored, and veto-capable workflow.

### 5.1 Agent roles

`GPT-5.5` Lead Editor and Final Arbiter

- Owns story integrity
- Breaks the script into sentence-level briefs
- Defines required facts, forbidden misreadings, and final acceptance logic
- Chooses the final shot only after reading all reviewer scores

Inputs:

- verified source notes
- full narration draft
- previous quality failures

Outputs:

- sentence brief sheet
- final decision sheet
- rejection reasons

`GPT-5.4` Storyboard Architect

- Designs shot logic for each sentence
- Assigns `visual_role`, `shot_type`, `composition`, `camera movement`, and `subtitle policy`
- Produces at least 2 distinct storyboard options for difficult lines

Inputs:

- sentence brief sheet from GPT-5.5

Outputs:

- storyboard plan
- per-sentence visual rationale

`GPT-5.3` Candidate Generator A

- Generates expressive candidate prompts and assets
- Prioritizes visual boldness and variety inside constraints

`GPT-5.3` Candidate Generator B

- Generates a second, independent prompt family
- Prioritizes clarity and literal readability over style novelty

Inputs:

- storyboard plan

Outputs:

- candidate prompts
- candidate image sets
- self-reported uncertainty notes

`GPT-5.4` Critic A

- Scores semantic match
- Flags factual misread risk
- Checks subtitle fit against the proposed frame

`GPT-5.4` Critic B

- Scores composition repetition, palette repetition, abstraction drift, and audience comprehension risk

Inputs:

- all candidate sets
- sentence brief sheet

Outputs:

- numeric scorecard
- veto recommendations
- concrete repair notes

`GPT-5.5` Synthesis Judge

- Merges the best surviving elements
- Rejects any candidate that fails hard constraints even if style is strong
- Resolves disagreement between critics

### 5.2 Score model

Every candidate frame gets a score out of 100:

- Semantic match: `35`
- Factual clarity: `20`
- Readability support for subtitles: `15`
- Style fit with episode: `10`
- Visual distinctiveness from nearby shots: `10`
- Emotional fit: `10`

Automatic rejection conditions:

- Semantic match below `24/35`
- Factual clarity below `12/20`
- Subtitle fit below `9/15`
- Any critic marks the frame as "chart-like misread", "wrong domain cue", or "human-risk minimization" for the sentence type

### 5.3 Veto rules

Any one of the following creates a temporary veto:

- a `GPT-5.4` critic identifies a domain-misaligned visual role
- a `GPT-5.5` lead editor finds a missing must-show fact
- subtitle QA fails the mobile preview

A vetoed frame can re-enter only after a revised candidate is rescored.

## 6. Stage Gates And Regression Tests

### 6.1 Stage gates

Gate 1: source and script gate

- narration estimate must land in `14 to 26 minutes`
- every paragraph must cite or link to a verified `source_basis`
- all sentences must be tagged with `fact_type`

Gate 2: sentence brief gate

- every sentence has `must_include`, `must_avoid`, and `visual_role`
- all high-risk sentences get at least 2 storyboard variants

Gate 3: asset generation gate

- each sentence gets at least 2 independent candidate visual families
- no candidate advances without critic scoring

Gate 4: subtitle gate

- font size and line-break rules pass
- mobile-size preview passes
- subtitle does not collide with essential visual labels

Gate 5: sequence gate

- neighboring shots are checked for palette repetition, composition repetition, and abstraction fatigue
- map, facility, people, and tunnel scenes must remain distinguishable in rhythm and look

Gate 6: final render gate

- runtime remains in `14 to 26 minutes`
- random shot sample review finds no domain-misaligned visuals
- all hard-veto failures are closed

### 6.2 Regression tests

Must-run regression checks for every new package:

- `subtitle_font_min_check`
- `subtitle_two_line_break_check`
- `mobile_legibility_preview_check`
- `visual_role_domain_check`
- `map_sentence_not_chart_check`
- `facility_sentence_not_abstract_geometry_check`
- `people_risk_sentence_not_symbolic_count_only_check`
- `tunnel_blockage_requires_cutaway_or_spatial_direction_check`
- `adjacent_shot_repetition_check`
- `runtime_14_to_26_min_check`

## 7. Confirmed Facts And Unmet Items In The Current Batch

### 7.1 Confirmed from observed V2 outputs

- Subtitle text is too small relative to the frame for comfortable mobile viewing.
- Several lines are visually over-compressed into a one-line subtitle treatment.
- Sentence-to-image matching is inconsistent and often too abstract.
- Multiple frames reuse a narrow dark-blue geometric style with low scene specificity.
- The current package shows weak evidence of a true competitive multi-agent review loop.

### 7.2 Not yet confirmed from the current batch

These items should be treated as unresolved until the package files are opened directly:

- the exact subtitle font size in renderer settings
- actual `visual_role` tags written in metadata
- actual `asset_id` lineage for the sampled shots
- actual `source_basis` coverage for every sentence
- exact runtime and whether it truly lands inside `14 to 26 minutes`
- whether multiple model families were independently generating and critiquing candidates or only serially refining one prompt family

## 8. Required Changes Before V3 Can Be Called Ready

Minimum bar for V3 readiness:

- Subtitle sizing and line-break policy are upgraded and verified
- Every sentence has an explicit visual brief with must-show facts
- High-risk lines are generated through competitive candidate sets
- Critics can veto domain-misaligned images
- Final sequence passes repetition, factuality, and runtime checks

Without these changes, V3 will likely preserve V2's main failure mode:

- visually consistent output that still under-delivers on meaning, trust, and mobile readability
