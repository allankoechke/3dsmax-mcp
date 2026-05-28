import json
import unittest

from src.server import mcp


class ServerToolEnvelopeTests(unittest.IsolatedAsyncioTestCase):
    async def test_registered_tools_return_structured_envelopes(self) -> None:
        _content, meta = await mcp.call_tool("execute_maxscript", {"code": ""})
        payload = json.loads(meta["result"])

        self.assertEqual(payload["ok"], False)
        self.assertIn("error", payload)
        self.assertNotIn("elapsed_ms", payload)
        self.assertNotIn("result", payload)


if __name__ == "__main__":
    unittest.main()
