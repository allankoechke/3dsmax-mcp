import json
import os
import unittest
from unittest.mock import patch

from mcp.server.fastmcp.utilities.types import Image

from src.tool_response import envelope_result, envelope_exception, make_structured_tool


class ToolResponseTests(unittest.TestCase):
    def test_minimal_success_omits_transport_and_elapsed(self) -> None:
        with patch.dict(os.environ, {"MCP_TRIPBACK_MODE": "minimal"}, clear=False):
            payload = json.loads(
                envelope_result('{"value": 3, "warnings": ["low"]}', elapsed_ms=1.234, transport={"transport": "namedpipe"})
            )

        self.assertEqual(payload["ok"], True)
        self.assertEqual(payload["result"]["value"], 3)
        self.assertEqual(payload["warnings"], ["low"])
        self.assertNotIn("error", payload)
        self.assertNotIn("transport", payload)
        self.assertNotIn("elapsed_ms", payload)

    def test_full_success_includes_transport_and_elapsed(self) -> None:
        with patch.dict(os.environ, {"MCP_TRIPBACK_MODE": "full"}, clear=False):
            payload = json.loads(
                envelope_result('{"value": 3}', elapsed_ms=1.234, transport={"transport": "namedpipe"})
            )

        self.assertEqual(payload["ok"], True)
        self.assertEqual(payload["elapsed_ms"], 1.234)
        self.assertEqual(payload["transport"]["transport"], "namedpipe")

    def test_minimal_error_includes_slim_transport(self) -> None:
        with patch.dict(os.environ, {"MCP_TRIPBACK_MODE": "minimal"}, clear=False):
            payload = json.loads(
                envelope_result(
                    "Error: boom",
                    elapsed_ms=2.0,
                    transport={
                        "transport": "namedpipe",
                        "request_id": "abc",
                        "client_round_trip_ms": 1.2,
                    },
                )
            )

        self.assertEqual(payload["ok"], False)
        self.assertEqual(payload["error"]["message"], "Error: boom")
        self.assertEqual(payload["transport"], {"transport": "namedpipe"})
        self.assertNotIn("elapsed_ms", payload)
        self.assertNotIn("result", payload)

    def test_envelope_surfaces_hint_from_error_result(self) -> None:
        raw = json.dumps({
            "status": "error",
            "error_type": "MAXScriptError",
            "error": "-- Unknown property: foo",
            "hint": {"message": "fallback", "suggested_tools": ["introspect_osl"]},
        })
        with patch.dict(os.environ, {"MCP_TRIPBACK_MODE": "minimal"}, clear=False):
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

    def test_minimal_exception_omits_elapsed(self) -> None:
        with patch.dict(os.environ, {"MCP_TRIPBACK_MODE": "minimal"}, clear=False):
            payload = json.loads(
                envelope_exception(RuntimeError("down"), elapsed_ms=9.0, transport={"transport": "tcp"})
            )

        self.assertEqual(payload["ok"], False)
        self.assertEqual(payload["error"]["message"], "down")
        self.assertEqual(payload["transport"]["transport"], "tcp")
        self.assertNotIn("elapsed_ms", payload)

    def test_structured_tool_preserves_signature_and_catches_exceptions(self) -> None:
        def raw_tool(name: str, count: int = 1) -> str:
            if count < 0:
                raise ValueError("bad count")
            return name * count

        with patch.dict(os.environ, {"MCP_TRIPBACK_MODE": "full"}, clear=False):
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
