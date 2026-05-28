import json
import unittest
from unittest.mock import MagicMock, patch

import src.tools._query_scene_core as core
from src.tools._query_scene_core import run_delta


class SceneDeltaTests(unittest.TestCase):
    def setUp(self) -> None:
        core._previous_snapshot = None

    def test_first_call_captures_baseline(self) -> None:
        state = {
            "Box001": {"c": "Box", "p": [0.0, 0.0, 0.0], "m": "", "n": 0, "h": False},
        }
        client = MagicMock()
        client.native_available = False
        with patch("src.tools._query_scene_core._capture_scene_state", return_value=state):
            result = json.loads(run_delta(client))

        self.assertEqual(result, {"baseline": True, "objectCount": 1})

    def test_diff_reports_added_removed_and_modified_objects(self) -> None:
        previous = {
            "Box001": {"c": "Box", "p": [0.0, 0.0, 0.0], "m": "", "n": 0, "h": False},
            "Box002": {"c": "Box", "p": [5.0, 0.0, 0.0], "m": "MatA", "n": 1, "h": False},
        }
        current = {
            "Box002": {"c": "Box", "p": [6.2, 0.0, 0.0], "m": "MatB", "n": 2, "h": True},
            "Sphere001": {"c": "Sphere", "p": [1.0, 1.0, 1.0], "m": "", "n": 0, "h": False},
        }
        client = MagicMock()
        client.native_available = False
        core._previous_snapshot = previous
        with patch("src.tools._query_scene_core._capture_scene_state", return_value=current):
            result = json.loads(run_delta(client))

        self.assertEqual(result["added"], [{"name": "Sphere001", "class": "Sphere"}])
        self.assertEqual(result["removed"], [{"name": "Box001", "class": "Box"}])
        self.assertEqual(result["counts"]["modified"], 1)


if __name__ == "__main__":
    unittest.main()
