import json
import unittest
from unittest.mock import MagicMock, patch

from src.tools.data_channel import (
    _format_add_result,
    _operator_lines,
    add_data_channel,
)


class DataChannelTests(unittest.TestCase):
    def test_empty_operators_returns_error(self) -> None:
        result = json.loads(add_data_channel(name="Box001", operators=[]))
        self.assertIn("error", result)

    def test_format_add_result(self) -> None:
        payload = json.loads(_format_add_result("OK|1|1|2|2|#(0, 1)|Box001"))
        self.assertTrue(payload["createdModifier"])
        self.assertEqual(payload["operatorsAdded"], 2)
        self.assertEqual(payload["operatorsTotal"], 2)

    def test_operator_lines_use_stack_count(self) -> None:
        lines = _operator_lines([{"type": "vertex_input"}])
        self.assertEqual(len(lines), 1)
        self.assertIn("dcIF.StackCount()", lines[0])
        lines_with_params = _operator_lines([
            {"type": "vertex_output", "params": {"output": 4, "channelNum": 1}},
        ])
        self.assertIn("beforeCount + 1", lines_with_params[1])

    def test_reuses_existing_modifier_in_maxscript(self) -> None:
        mock_client = MagicMock()
        sent: list[str] = []

        def capture(script: str, **_kwargs: object) -> dict:
            sent.append(script)
            return {"result": "OK|0|1|1|3|#(0,1,2)|Box001"}

        mock_client.send_command = capture
        with patch("src.tools.data_channel.client", mock_client):
            add_data_channel(
                name="Box001",
                operators=[{"type": "smooth"}],
            )
        self.assertEqual(len(sent), 1)
        script = sent[0]
        self.assertIn("for i = 1 to obj.modifiers.count do", script)
        self.assertIn("if dcMod == undefined then (", script)
        self.assertIn("beforeCount = dcMod.operators.count", script)


if __name__ == "__main__":
    unittest.main()
