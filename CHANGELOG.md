# Changelog

All notable changes to this project are documented here.

## [1.1.0] — 2026-07-06

Render automation (done-signal) and material-library tooling.

### Added

- `render_automations` — arms a render done-signal at 3ds Max's `NOTIFY_POST_RENDER` and reports completion (with the real `frames_rendered` count) through an event-driven file watcher (`scripts/render_signal_wait.ps1`); no polling, never blocks the bridge. Includes `cancel` to abort a render in flight from the pipe thread.
- Native `render_start` / `render_cancel` handlers and an always-on render-completion pinger.
- `get_material_library` — inspects the volatile material scratchpads (`currentMaterialLibrary` and the Compact Material Editor slots) that aren't saved with the scene, and warns when the current library has no backing `.mat` file.
- `backup_material_library` — saves those scratchpads to timestamped `.mat` files without touching the scene.

### Changed

- The bridge is a render *listener*, not a trigger: `render_automations(start)` only arms the done-signal, and the render is fired externally (Render button, or `max quick render` via `execute_maxscript`). Launching the render from inside the bridge caused 3ds Max to auto-start a second render on completion and loop; keeping the trigger outside the bridge avoids it.
- `execute_maxscript` suggests the material-library tools when raw MAXScript touches the material library.
- `SKILL.md` trimmed to Max-usage gotchas only.

## [1.0.6] — 2026-06-24

Keyframing and installer release draft with the package version bumped to `1.0.6`.

### Added

- `keyframe_tracks` for native key inspection, setting, endpoint matching, loop closure, tangent styling, and out-of-range behavior edits.
- Compact, budgeted keyframe summaries for baked animation and mocap-heavy controllers.
- Keyed `value` and `move` writes so animation edits can avoid `transform_object` offset side effects.

### Changed

- Keyframe result counters distinguish logical track edits from raw sub-controller edits.
- Installer discovery covers classic and Microsoft Store Claude Desktop config paths.

### Fixed

- Composite Position/Euler/Scale controllers now create and style explicit-frame keys through their child tracks.
- Keyframe styling reports stable candidate counts on first set-and-style calls.
- Track-path matching is exact so narrow keyframe edits do not leak into similarly named tracks.

## [1.0.5] — 2026-06-01

Material-network release draft with the package version bumped to `1.0.5`.

### Added

- `inspect_material_network` for native semantic material graph reads: wired slots, nested maps, file manifests, health issues, and compact mode.
- `replicate_material` for preview-first graph cloning, texture remapping, verification, and explicit apply.
- Material-network tool catalog, smoke input coverage, in-Max chat registry entries, and user-facing docs/spec.

### Changed

- Viewport capture tools now return saved-file metadata by default, with `return_image=true` preserving inline image behavior.
- Native viewport captures accept max dimensions and report source/final image sizes.
- Tool surface is streamlined around `inspect_properties(target="modifier")`; `inspect_modifier_properties` remains as a compatibility alias but is hidden from the playground and default smoke pass.
- `get_object_properties` and `inspect_object` descriptions now distinguish compact readback from deep exploratory inspection.

### Fixed

- Material replication now blocks missing source textures and non-texture graph dependencies unless explicitly allowed.
- OSL shader source is no longer misclassified as a remappable file path; OSL file paths remain visible in inspection output.
- Wired material slots are deduplicated in graph inspection output.

## [1.0.0] — 2026-05-28

First stable release. Production-ready MCP bridge for 3ds Max 2023–2027 with prebuilt native plugins shipped in the repo.

> **Patched in place (2026-05-28)** — binaries rebuilt, no version bump: fixed a native main-thread deadlock in the **MCP Smoke** macro, a `palette_laydown` crash on flat texture folders, invalid spatial JSON from `create_object` on TCP transport, Forest Pack dropping zero-footprint items, unescaped names in `query_scene` MAXScript fallbacks, and `query_scene(delta)` mis-tracking duplicate-named nodes.

### Highlights

- **114 MCP tools** (77 in `core` profile) — scene reads, objects, modifiers, materials, controllers, viewport capture, plugin introspection, and specialty modules (tyFlow, Forest Pack, RailClone, Data Channel, and more).
- **Native bridge** — named-pipe transport by default; prebuilt `mcp_bridge_20XX.gup` for Max 2023–2027 in `native/bin/`.
- **`query_scene`** — unified scene reads (`overview`, `filter`, `class`, `property`, `selection`, `delta`) replacing scattered snapshot tools.
- **`smart_import`** — folder-aware mesh + PBR import (per-subfolder asset packs, shared atlases, multi-variant bundles).
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
