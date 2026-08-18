from __future__ import annotations

import unittest

from modern.runs.smoke_g4.build_chapters import expand
from modern.story_quality import InsufficientStoryMaterial


class SmokeG4NoPaddingTests(unittest.TestCase):
    def test_short_chapter_raises_instead_of_repeating_scene_beats(self) -> None:
        with self.assertRaises(InsufficientStoryMaterial):
            expand("짧은 초고", 100)

    def test_sufficient_chapter_is_returned_unchanged(self) -> None:
        chapter = "가" * 100

        self.assertEqual(chapter, expand(chapter, 100))


if __name__ == "__main__":
    unittest.main()
