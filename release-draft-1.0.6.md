# 3dsmax-mcp 1.0.6

Patch release focused on native keyframing tools and installer polish.

## Highlights

- Added `keyframe_tracks` for native key inspection, setting, endpoint matching, loop closure, tangent styling, and out-of-range behavior edits.
- Added compact, budgeted JSON summaries for baked animation and mocap-heavy controllers.
- Added keyed `value` and `move` writes so animation edits do not need `transform_object` offset moves.
- Clarified keyframe counters so logical track edits are separate from raw sub-controller edits.
- Improved installer discovery for classic and Microsoft Store Claude Desktop config paths.

## Fixes

- Composite Position/Euler/Scale controllers now create and style explicit-frame keys through their child tracks.
- Keyframe styling reports stable candidate counts on first set-and-style calls.
- Track-path matching is exact so narrow edits do not leak into similarly named tracks.

## Validation

- `.venv\Scripts\python.exe -m unittest tests.test_keyframes tests.test_controllers tests.test_install`
- `.venv\Scripts\python.exe scripts/gen_tool_registry.py`
- `.venv\Scripts\python.exe scripts/gen_tool_smoke.py`
- `native\build.bat all`

## Assets

- `mcp_bridge_2023.gup`
- `mcp_bridge_2024.gup`
- `mcp_bridge_2025.gup`
- `mcp_bridge_2026.gup`
- `mcp_bridge_2027.gup`
- `mcp_bridge.gup`
