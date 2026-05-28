"""Tests for path_filter helper."""

import unittest
from pathlib import Path

from src.helpers.path_filter import (
    filter_by_name_pattern,
    matches_name_pattern,
    normalize_name_pattern,
)


class PathFilterTests(unittest.TestCase):
    def test_normalize_treats_empty_and_star_as_disabled(self) -> None:
        self.assertIsNone(normalize_name_pattern(""))
        self.assertIsNone(normalize_name_pattern("*"))
        self.assertEqual(normalize_name_pattern("*wood*"), "*wood*")

    def test_filter_by_stem_glob(self) -> None:
        paths = [Path("OakWood_LOD0.fbx"), Path("StoneWall.fbx"), Path("wood_plank.obj")]
        kept, skipped = filter_by_name_pattern(paths, "*wood*", key=lambda p: p.stem)
        self.assertEqual([p.name for p in kept], ["OakWood_LOD0.fbx", "wood_plank.obj"])
        self.assertEqual(skipped, 1)

    def test_filter_disabled_returns_all(self) -> None:
        paths = [Path("a.fbx"), Path("b.fbx")]
        kept, skipped = filter_by_name_pattern(paths, "", key=lambda p: p.stem)
        self.assertEqual(kept, paths)
        self.assertEqual(skipped, 0)

    def test_matches_is_case_insensitive(self) -> None:
        self.assertTrue(matches_name_pattern("OakWood", "*wood*"))


if __name__ == "__main__":
    unittest.main()
