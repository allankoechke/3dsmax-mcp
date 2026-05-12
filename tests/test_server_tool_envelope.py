import json
import unittest

from src.server import mcp


class ServerToolEnvelopeTests(unittest.IsolatedAsyncioTestCase):
    async def test_registered_tools_return_structured_envelopes(self) -> None:
        _content, meta = await mcp.call_tool("execute_maxscript", {"code": ""})
        payload = json.loads(meta["result"])

        self.assertEqual(payload["ok"], False)
        self.assertEqual(payload["result"], None)
        self.assertIn("error", payload)
        self.assertIn("transport", payload)
        self.assertIn("elapsed_ms", payload)


if __name__ == "__main__":
    unittest.main()
