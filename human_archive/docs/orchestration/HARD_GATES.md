# Hard gates for orchestration rounds

These are not advisory. If a task appears to require violating one, stop and report the
conflict in `## UNCERTAINTY` (review roles) or `## RISKS` (design roles) instead of
proceeding.

1. **Never fabricate a structured answer to look complete.** If you cannot actually check
   something, say so in `## UNCERTAINTY` / `## RISKS`. A confident-sounding placeholder is
   the exact failure this repository already has in `scripts/tri_model_debate_engine.py`
   (hardcoded "합의 점수 98.8" strings with zero model calls behind them)  --  do not
   reproduce it.
2. **Do not silently reuse the same underlying model in two seats of one round.** A round
   where two "independent" reviewers are the same checkpoint under different names is not
   a cross-check (this repository already shipped that bug once: "Gemini 3.7" and
   "Gemini 3.6" both resolved to `gemini-2.5-flash`).
3. **Cite `file:line`, a manifest path, or an exact command.** "The script looks fine" or
   "the prompt covers this" is a claim, not evidence, in this repository's history  --  every
   defect found in the 2026-09-15 diagnosis (`docs/superpowers/plans/2026-09-15-human-archive-nollam-script-visual-motion-multi-llm-overhaul-plan.md`)
   was found by reading actual code, not by trusting a docstring or a YAML comment.
4. **Narration text, sentence content, or a full script must never be copied verbatim from
   another channel's real, specific video.** Structural benchmarking (cut-length
   distribution, phase ratios, cut counts  --  see `research/human_library_top30/`) is fine;
   reproducing another creator's actual words, branding, or frame-matched timing is not.
   See `research/human_library_benchmark_internal_only/DO_NOT_PUBLISH.md` for the incident
   this gate exists because of.
5. **Motion/Ken Burns proposals must not reintroduce the known judder pattern**: full-shot
   cosine easing over the whole clip duration with a small (<10%) zoom delta. This exact
   pattern was found independently in both `scripts/build_motion_clips_v2.py` and
   `scripts/smooth_subpixel_motion_engine.py` and produced a measured 78-84% near-duplicate
   frame rate (`mpdecimate`). Any motion design must specify the trajectory as normalized
   start/end crop coordinates with an explicit short ramp (0.2-0.4s) at each end, not "apply
   easing across the clip."
6. **Image generation prompts must never include text, numerals, years, or watermarks**  -- 
   `overlay_event_manifest` renders all on-screen text. This is a hard channel-visual-policy
   constraint (`channel_profiles.yaml`, `nollam_file_visual_policy.yaml`), not a style
   preference.
7. **A round with fewer than 2 independent-vendor answers is not a completed round.** Do not
   let a synthesis or critique proceed as if a missing participant's absence were silent
   agreement.
8. **Do not invent duration, shot-count, or pacing numbers.** `nollam_decay_20m`
   (`config/visual_pacing_profiles.yaml`) and `script_policy_v3.yaml` are the authorities
   for target duration, cut cadence, and sentence-length ranges. If a proposal needs a
   number from there, read the file; do not estimate.
