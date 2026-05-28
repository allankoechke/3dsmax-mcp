# Changelog

All notable changes to this project are documented here.

## [1.0.0] — 2026-05-28

First stable release. Production-ready MCP bridge for 3ds Max 2023–2027 with prebuilt native plugins shipped in the repo.

> **Patched in place (2026-05-28)** — binaries rebuilt, no version bump: fixed a native main-thread deadlock in the **MCP Smoke** macro, a `palette_laydown` crash on flat texture folders, invalid spatial JSON from `create_object` on TCP transport, Forest Pack dropping zero-footprint items, unescaped names in `query_scene` MAXScript fallbacks, and `query_scene(delta)` mis-tracking duplicate-named nodes.

### Highlights

- **114 MCP tools** (77 in `core` profile) — scene reads, objects, modifiers, materials, controllers, viewport capture, plugin introspection, and specialty modules (tyFlow, Forest Pack, RailClone, Data Channel, and more).
- **Native bridge** — named-pipe transport by default; prebuilt `mcp_bridge_20XX.gup` for Max 2023–2027 in `native/bin/`.
- **`query_scene`** — unified scene reads (`overview`, `filter`, `class`, `property`, `selection`, `delta`) replacing scattered snapshot tools.
- **`smart_import`** — folder-aware mesh + PBR import (Megascans plants, shared atlases, multi-variant bundles).
- **`create_shell_material`** — dual render/export pipeline wrapper for any two materials or texture-built PBR pair (OpenPBR, Physical, Arnold, Octane, etc.).
- **`scatter_forest_pack`** — per-geometry footprint sizing for multi-variant Forest Pack scatters.
- **Spatial placement** — `create_object` / `clone_objects` ground-contact placement with rich tripback (`bbox`, `placement`, `groundContact`).
- **Tool Inspector** — `Tool Playground.bat` GUI for manual one-tool-at-a-time testing with full tripback.
- **Live smoke harness** — `run_tool_smoke`, `run_live_tool_smoke.py`, in-Max **MCP Smoke** macro.
- **Multi-Max** — **MCP Claim This Max** routes clients to the correct instance.
- **Agent skill** — bundled Max usage guide + MAXScript reference files; installer deploys automatically.
- **Docs** — user-facing README + [Advanced configuration](docs/ADVANCED.md).

### Breaking changes (from 0.8.x)

- **`create_shell_material`** — new API: wrap existing materials by name or build from `texture_folder` + `render_material_class` / `export_material_class`. Old UberBitmap-only parameters removed.
- **Scene reads** — prefer `query_scene(action=…)` over removed `get_scene_snapshot` / legacy snapshot modules.
- **Standalone in-Max chat** — still experimental (WIP); external MCP recommended for production.

### Install / upgrade

```powershell
git pull
uv sync
uv run python install.py
```

Restart 3ds Max after install.

---

## [0.8.5] and earlier

Pre-1.0 development releases. See git history for details.
