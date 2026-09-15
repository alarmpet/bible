# -*- coding: utf-8 -*-
"""Generate AI video clips for the first 7 hook shots via Google Flow Video (Veo).

Falls back to enhanced 2.5D motion if video generation is not available.
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

from playwright.async_api import async_playwright

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


# Video prompts (cinematic, dynamic, no watermarks)
VIDEO_PROMPTS = {
    "ch1_01": "Cinematic drone shot, Mount Vesuvius erupting violently, massive black ash column rising 30km into clear blue sky over the Bay of Naples, smoke and pyroclastic debris billowing dynamically upward, ancient Roman landscape below, dramatic natural disaster footage, 4K cinematic, photorealistic",
    "ch1_02": "Cinematic wide tracking shot, bustling ancient Pompeii city streets, Roman citizens in togas walking on cobblestone roads, merchant carts moving, fabric awnings fluttering in Mediterranean breeze, terracotta rooftops gleaming in warm golden sunlight, 4K cinematic, photorealistic",
    "ch1_03": "Cinematic close-up portrait, young Roman scholar Pliny standing on a villa balcony writing on papyrus with a reed pen, wind gently blowing his toga, a massive pine-tree shaped volcanic cloud visible rising across the bay behind him, dramatic golden hour lighting, 4K cinematic",
    "ch1_04": "Cinematic aerial view, colossal volcanic ash umbrella cloud expanding horizontally across the stratosphere above ancient Italy, wind-driven ash particles swirling, sunlight filtering through dark clouds creating dramatic crepuscular rays, 4K cinematic, photorealistic",
    "ch1_05": "Cinematic medium shot, Roman citizens on Pompeii cobblestone streets looking up at distant volcanic cloud with calm curiosity, a father pointing upward explaining to his child, other pedestrians walking normally, warm afternoon light, 4K cinematic, photorealistic",
    "ch1_06": "Cinematic tracking shot through a lively Roman marketplace in the Pompeii Forum, merchants actively selling round bread loaves and clay amphorae of olive oil, animated crowd bargaining and exchanging coins, fabric canopy fluttering in breeze, warm sunlight, 4K cinematic",
    "ch1_07": "Cinematic scene outside the Pompeii stone amphitheatre, Roman gladiators in bronze armor gesturing and discussing with animated citizens, painted event posters on stone walls, crowd gathering with energy, afternoon Mediterranean light, 4K cinematic, photorealistic",
}


async def try_generate_video_clips():
    """Attempt to generate AI video clips via Google Flow Video tab."""
    run_dir = Path("human_archive/runs/ep01_pompeii_18hours")
    manifest_path = run_dir / "scene_audio_manifest.json"
    clips_dir = run_dir / "video_clips"
    clips_dir.mkdir(parents=True, exist_ok=True)

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    shot_durations = {s["shot_id"]: s["duration"] for s in manifest["shots"]}

    print("=== Phase 1: Generating AI Video Clips for Hook Shots (ch1_01~ch1_07) ===\n")

    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        contexts = browser.contexts
        if not contexts:
            print("ERROR: No browser contexts found. Is Chrome running with --remote-debugging-port=9222?")
            return False

        # Find the Flow page
        flow_page = None
        for page in contexts[0].pages:
            if "flow" in page.url or "labs.google" in page.url:
                flow_page = page
                break

        if not flow_page:
            print("ERROR: Google Flow page not found. Please open https://labs.google/fx/ko/tools/flow")
            return False

        print(f"  Connected to: {flow_page.url}\n")

        # Check if Video tab/mode exists on the page
        video_tab = await flow_page.query_selector("button:has-text('Video'), [data-tab='video'], button:has-text('동영상')")
        
        if not video_tab:
            # Try looking for video mode selector in different possible locations
            video_tab = await flow_page.query_selector("[aria-label*='video' i], [aria-label*='동영상']")

        if not video_tab:
            print("  ⚠️ Google Flow Video(Veo) tab not found on current page.")
            print("  → Falling back to enhanced cinematic motion mode.\n")
            return False

        # Click video tab to switch to video generation mode
        print("  ✅ Found Video generation tab! Switching to video mode...\n")
        await video_tab.click()
        await flow_page.wait_for_timeout(2000)

        generated_count = 0

        for shot_id, video_prompt in VIDEO_PROMPTS.items():
            dur = shot_durations.get(shot_id, 10.0)
            out_clip = clips_dir / f"{shot_id}_ai_video.mp4"

            print(f"  [{generated_count + 1}/7] Generating video for {shot_id} ({dur:.1f}s)...")
            print(f"    Prompt: {video_prompt[:70]}...\n")

            # Record pre-existing video URLs
            pre_urls = await flow_page.evaluate("""() => {
                const s = new Set();
                document.querySelectorAll('video source, video').forEach(el => {
                    const src = el.src || el.querySelector('source')?.src || '';
                    if (src) s.add(src);
                });
                // Also check for download links
                document.querySelectorAll('a[download], a[href*="video"]').forEach(el => {
                    if (el.href) s.add(el.href);
                });
                return Array.from(s);
            }""")

            # Clear and type prompt
            textbox = await flow_page.query_selector("div[role='textbox'], [contenteditable='true'], textarea")
            if textbox:
                await textbox.click()
                await flow_page.wait_for_timeout(200)
                await flow_page.keyboard.press("Control+A")
                await flow_page.keyboard.press("Backspace")
                await flow_page.wait_for_timeout(100)
                await flow_page.keyboard.type(video_prompt, delay=3)
                await flow_page.wait_for_timeout(300)

            # Submit
            submit_btn = await flow_page.query_selector("button:has-text('arrow_forward'), button[type='submit']")
            if submit_btn:
                await submit_btn.click()
            else:
                await flow_page.keyboard.press("Enter")

            # Video generation takes longer (~60-90s vs ~18s for images)
            print(f"    Submitted. Waiting for video generation (~60s)...")
            await flow_page.wait_for_timeout(60000)

            # Try to find new video content
            post_urls = await flow_page.evaluate("""() => {
                const list = [];
                document.querySelectorAll('video source, video').forEach(el => {
                    const src = el.src || el.querySelector('source')?.src || '';
                    if (src) list.push(src);
                });
                document.querySelectorAll('a[download], a[href*="video"]').forEach(el => {
                    if (el.href) list.push(el.href);
                });
                return list;
            }""")

            new_urls = [u for u in post_urls if u not in pre_urls]

            if new_urls:
                target_url = new_urls[-1]
                try:
                    resp = await flow_page.request.get(target_url)
                    video_bytes = await resp.body()
                    out_clip.write_bytes(video_bytes)
                    print(f"    ✅ Saved AI video clip: {out_clip.name} ({len(video_bytes)} bytes)\n")
                    generated_count += 1
                except Exception as e:
                    print(f"    ❌ Failed to download video: {e}\n")
            else:
                # Try to find video via blob URLs or canvas
                blob_url = await flow_page.evaluate("""() => {
                    const v = document.querySelector('video');
                    return v ? v.src : null;
                }""")
                if blob_url and blob_url.startswith("blob:"):
                    print(f"    ⚠️ Video found as blob URL (cannot download directly). Skipping.\n")
                else:
                    print(f"    ⚠️ No new video content detected for {shot_id}. May need manual download.\n")

        if generated_count > 0:
            print(f"\n=== Successfully generated {generated_count}/7 AI video clips ===\n")
            return True
        else:
            print("\n=== No AI video clips were generated. Falling back to enhanced motion. ===\n")
            return False


async def main():
    success = await try_generate_video_clips()
    if not success:
        print("Fallback: Will use enhanced cinematic motion for hook shots.")
        print("Run build_all_motion_clips.py instead.")


if __name__ == "__main__":
    asyncio.run(main())
