from pathlib import Path


EPISODE_DIR = Path(
    r"D:\module\bible\human_archive\runs\nollam_file\2026-09-02\himalaya-glof-water-crisis"
)


def main() -> None:
    source = EPISODE_DIR / "generation" / "pilot_prompt_pack_zapi_flow.txt"
    output = EPISODE_DIR / "generation" / "pilot_prompt_pack_zapi_flow_clean.txt"
    lines = source.read_text(encoding="utf-8").splitlines()
    clean = [line.split(" | ", 1)[1] if " | " in line else line for line in lines]
    if len(clean) != 20 or any(not line.strip() for line in clean):
        raise ValueError(f"Expected 20 non-empty prompts, got {len(clean)}")
    output.write_text("\n".join(clean) + "\n", encoding="utf-8")
    print(f"wrote {output}")
    print(f"physical_lines={len(clean)}")


if __name__ == "__main__":
    main()
