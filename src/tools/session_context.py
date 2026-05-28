"""Compact session context tool for natural AI + 3ds Max interaction."""

from __future__ import annotations

import json

from ..server import mcp, client
from ._query_scene_core import run_overview, run_selection


@mcp.tool()
def get_session_context(
    max_roots: int = 20,
    max_selection: int = 20,
) -> str:
    """Bundle bridge, capabilities, scene, and selection when broad live context is needed—not before every task."""
    from .bridge import get_bridge_status
    from .capabilities import get_plugin_capabilities

    return json.dumps({
        "bridge": json.loads(get_bridge_status()),
        "capabilities": json.loads(get_plugin_capabilities()),
        "scene": json.loads(run_overview(client, max_roots=max_roots)),
        "selection": json.loads(run_selection(client, detail="full", max_items=max_selection)),
    })
