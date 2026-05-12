import json
import unittest

from mcp.server.fastmcp.utilities.types import Image

from src.tool_response import envelope_result, make_structured_tool


class ToolResponseTests(unittest.TestCase):
    def test_envelope_parses_json_result_and_extracts_warnings(self) -> None:
        payload = json.loads(envelope_result('{"value": 3, "warnings": ["low"]}', elapsed_ms=1.234))

        self.assertEqual(payload["ok"], True)
        self.assertEqual(payload["result"]["value"], 3)
        self.assertEqual(payload["warnings"], ["low"])
        self.assertEqual(payload["error"], None)
        self.assertEqual(payload["elapsed_ms"], 1.234)

    def test_envelope_marks_plain_error_strings_as_failures(self) -> None:
        payload = json.loads(envelope_result("Error: boom", elapsed_ms=2.0))

        self.assertEqual(payload["ok"], False)
        self.assertEqual(payload["result"], None)
        self.assertEqual(payload["error"]["message"], "Error: boom")

    def test_envelope_surfaces_hint_from_error_result(self) -> None:
        raw = json.dumps({
            "status": "error",
            "error_type": "MAXScriptError",
            "error": "-- Unknown property: foo",
            "hint": {"message": "fallback", "suggested_tools": ["introspect_osl"]},
        })
        payload = json.loads(envelope_result(raw, elapsed_ms=0.1))

        self.assertEqual(payload["ok"], False)
        self.assertEqual(payload["error"]["type"], "MAXScriptError")
        self.assertEqual(payload["hint"]["suggested_tools"], ["introspect_osl"])

    def test_envelope_catches_not_found_and_failed_messages(self) -> None:
        for raw in (
            "Object not found: __missing__",
            "Material not found: foo",
            "Failed: could not assign controller",
            "Blocked by safe mode: command contains a restricted function.",
        ):
            with self.subTest(raw=raw):
                payload = json.loads(envelope_result(raw, elapsed_ms=0.1))
                self.assertEqual(payload["ok"], False, raw)
                self.assertEqual(payload["error"]["message"], raw)

    def test_envelope_serializes_mcp_images(self) -> None:
        payload = json.loads(envelope_result(Image(data=b"abc", format="png"), elapsed_ms=0.0))

        self.assertEqual(payload["ok"], True)
        self.assertEqual(payload["result"]["type"], "image")
        self.assertEqual(payload["result"]["mime_type"], "image/png")
        self.assertEqual(payload["result"]["encoding"], "base64")
        self.assertEqual(payload["result"]["data"], "YWJj")

    def test_structured_tool_preserves_signature_and_catches_exceptions(self) -> None:
        def raw_tool(name: str, count: int = 1) -> str:
            if count < 0:
                raise ValueError("bad count")
            return name * count

        wrapped = make_structured_tool(raw_tool, transport_provider=lambda: {"transport": "tcp"})

        self.assertEqual(str(wrapped.__signature__), "(name: str, count: int = 1) -> str")
        ok_payload = json.loads(wrapped("x", count=2))
        self.assertEqual(ok_payload["result"], "xx")
        self.assertEqual(ok_payload["transport"]["transport"], "tcp")

        error_payload = json.loads(wrapped("x", count=-1))
        self.assertEqual(error_payload["ok"], False)
        self.assertEqual(error_payload["error"]["type"], "ValueError")


if __name__ == "__main__":
    unittest.main()
