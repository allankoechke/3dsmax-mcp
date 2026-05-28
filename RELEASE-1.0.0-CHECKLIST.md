# 3dsmax-mcp — 1.0.0 Release Checklist

**Current version:** `0.8.5` (see `pyproject.toml`)  
**Target:** `1.0.0` — first stable, production-trustworthy release  
**Last updated:** 2026-05-28

Use this document only for release gating. Do not fold it into README.

---

## How to use

- Check boxes when done on **at least one real Max install** (not mocks).
- Prefer **live Max testing** over Python unit tests for release sign-off.
- Record pass/fail notes inline or in a release issue.
- All three live test paths below exercise the **same bridge** an AI agent uses.

---

## 1. Live test ground (required — primary gate)

These are the human-friendly ways to call tools like an AI would.

### 1.1 Tool Inspector (GUI — manual, one tool at a time)

- [ ] Open 3ds Max with MCP bridge loaded
- [ ] Launch `Tool Playground.bat` (opens **Tool Inspector** — nothing auto-runs)
- [ ] Optional: **Check Max connection** (single `get_bridge_status` tripback)
- [ ] For each tool you care about:
  - [ ] Click tool name → **Load** (fills example JSON only)
  - [ ] Edit args if needed
  - [ ] Click **Run ▶** on that row OR **Run this tool** in the detail panel
  - [ ] Read **tripback** pane: status, `result`, full envelope (what the AI sees)
- [ ] Regenerate catalog after tool changes: `uv run python scripts/gen_tool_catalog.py`

### 1.2 In-Max smoke (native, no Python test harness)

- [ ] Regenerate smoke cases: `uv run python scripts/gen_tool_smoke.py`
- [ ] Rebuild + deploy native plugin for target Max year(s)
- [ ] Run **MCP → MCP Smoke** macro inside Max (read tier)
- [ ] Or call MCP tool `run_tool_smoke` with `{ "tier": "read" }`
- [ ] Optional deeper tiers:
  - [ ] `{ "tier": "fixture" }` — needs scene objects; creates `MCP_SmokeTarget`
  - [ ] `{ "tier": "mutate" }` — scene changes; use Hold/Fetch or empty test scene
- [ ] Single-tool debug via `invoke_tool` MCP tool works

### 1.3 CLI live smoke (full surface)

Not pytest — every call hits the real bridge. **Default is one tool per call** (safe). Use `--batch` only if you know what you're doing.

```powershell
uv run python scripts/run_live_tool_smoke.py --tier read
uv run python scripts/run_live_tool_smoke.py --tier fixture
uv run python scripts/run_live_tool_smoke.py --tier native --batch   # optional fast path
uv run python scripts/run_live_tool_smoke.py --tier full
```

- [ ] `--tier read` — zero failures (or only documented `expect_error` cases)
- [ ] `--tier native` — fixture + mutate pass on empty or disposable test scene
- [ ] `--tier full` — Python-routed tools pass (tyFlow, plugins, data channel, etc.)
- [ ] Document any **expected skips** (missing plugins, no sample `.max` file, etc.)

### 1.4 Multi-Max / transport

- [ ] Single Max instance: auto-connect works
- [ ] Two Max instances: **MCP Claim This Max** routes client to correct instance
- [ ] Named pipe is default; TCP fallback works when native bridge unavailable
- [ ] `get_bridge_status` reports correct `protocolVersion`, `safeMode`, transport

---

## 2. Native bridge build matrix

Prebuilt GUPs live in `native/bin/mcp_bridge_20XX.gup`.

| Max year | Build | Install | Smoke read | Notes |
|----------|-------|---------|------------|-------|
| 2023     | [ ]   | [ ]     | [ ]        |       |
| 2024     | [ ]   | [ ]     | [ ]        |       |
| 2025     | [ ]   | [ ]     | [ ]        |       |
| 2026     | [ ]   | [ ]     | [ ]        |       |
| 2027     | [ ]   | [ ]     | [ ]        | C++20 |

- [ ] `gen_tool_registry.py` runs at build time; chat registry matches Python tools
- [ ] `gen_tool_smoke.py` output committed or regenerated in CI before native build
- [ ] No crash on Max shutdown with chat window open
- [ ] No crash on plugin reload / scene reset

---

## 3. Install & upgrade path

- [ ] Fresh machine: `uv sync` → `uv run python install.py` → Max restart → bridge connects
- [ ] Upgrade from 0.8.x: `git pull` → `uv sync` → `install.py` → Max restart
- [ ] `--skip-skill` path still deploys bridge + MAXScript
- [ ] Config lands in `%LOCALAPPDATA%\3dsmax-mcp\`:
  - [ ] `mcp_config.ini`
  - [ ] `.env` / API key path documented for chat (not required for MCP-only)
- [ ] Cursor / Claude MCP config snippet in `install.py` output is correct
- [ ] Uninstall story documented (remove GUP, startup MS, MCP client entry)

---

## 4. MCP tool surface (114 tools, full profile)

### 4.1 Core workflows (must work on release)

- [ ] Scene read: `query_scene`, `get_session_context`, `get_hierarchy`, `get_instances`, `get_dependencies`
- [ ] Object CRUD: create, transform, delete, clone, parent
- [ ] Materials: OpenPBR assign, slots read, texture-from-folder
- [ ] Modifiers: add/remove/state/collapse
- [ ] Organization: layers, groups, selection sets
- [ ] Viewport capture (not full render unless explicitly requested)
- [ ] External `.max`: inspect, search, merge
- [ ] `execute_maxscript` respects `safe_mode`

### 4.2 Specialty modules (full profile)

Test only if plugin installed; mark N/A otherwise.

- [ ] tyFlow
- [ ] RailClone
- [ ] Forest Pack / scattering
- [ ] Data Channel
- [ ] State sets / camera sequence
- [ ] Floor plan builder
- [ ] Effects list/toggle

### 4.3 Standalone chat (optional for MCP-only users)

- [ ] MCP Chat window opens
- [ ] `/reload`, `/clear`, `/help`
- [ ] Tool calls from LLM route through `CommandDispatcher` + safe_mode
- [ ] `tool_profile=core` vs `full` behaves as documented

---

## 5. Agent skill & resources

- [ ] `python scripts/build_skill.py` succeeds
- [ ] Skill deploys to expected agent paths (Claude / `.agents`)
- [ ] `resource://3dsmax-mcp/skill` serves current SKILL.md
- [ ] Plugin manifest resources resolve for at least one installed plugin
- [ ] learn-from-mistakes entries reviewed (no duplicates, still accurate)

---

## 6. Security & safety (honest scope for 1.0)

- [ ] `safe_mode=true` (default) blocks obvious destructive MAXScript patterns
- [ ] Documented: safe_mode is **not** a sandbox; native handlers are unfiltered
- [ ] Named pipe ACL understood (same-user local dev OK)
- [ ] No secrets in repo (.env.example only)
- [ ] Chat API key stored under `%LOCALAPPDATA%`, not scene files

---

## 7. Automated tests (secondary gate)

Python unit tests catch regressions in string building and envelopes — **not** a substitute for §1.

```powershell
uv run python -m pytest tests/ -q
```

- [ ] Full pytest suite green
- [ ] `tests/test_install.py` passes on clean layout
- [ ] No new flaky live-only assumptions in unit tests

---

## 8. Release mechanics

- [ ] Version bumped: `pyproject.toml`, native `MCP_BRIDGE_VERSION` (via CMake), any install banners
- [ ] CHANGELOG section for 1.0.0 (highlights + breaking changes if any)
- [ ] Git tag `v1.0.0`
- [ ] GitHub release with:
  - [ ] Prebuilt GUP binaries per supported Max year OR build instructions
  - [ ] MCP client config example
  - [ ] Link to this checklist (archived pass results)
- [ ] README accurate enough for first-time install (separate doc pass OK post-checklist)

---

## 9. Known limitations (accept or fix before 1.0)

Track decisions — ship with docs, or block release.

| Item | Status | Decision |
|------|--------|----------|
| ~40 tools require Python MCP server (MAXScript wrappers) | | |
| In-Max chat registry ⊂ full MCP tool list | | |
| Plugin-specific tools fail without plugin | | |
| Shell/ORM material path needs real texture folders | | |
| `render_scene` not in default smoke (intentional) | | |
| Multi-user / RDP / VM edge cases | | |

---

## 10. Sign-off

| Role | Name | Date | Notes |
|------|------|------|-------|
| Live Max smoke (§1) | | | |
| Native builds (§2) | | | |
| Install path (§3) | | | |
| Release tag (§8) | | | |

**Release approved for 1.0.0:** [ ] Yes  [ ] No — blockers: _______________

---

## Quick reference commands

```powershell
# Regenerate artifacts
uv run python scripts/gen_tool_catalog.py
uv run python scripts/gen_tool_smoke.py
uv run python scripts/gen_tool_registry.py

# Human test ground
Tool Playground.bat

# Live smoke tiers
uv run python scripts/run_live_tool_smoke.py --tier read
uv run python scripts/run_live_tool_smoke.py --tier native
uv run python scripts/run_live_tool_smoke.py --tier full

# Install
uv sync
uv run python install.py

# Unit tests (secondary)
uv run python -m pytest tests/ -q
```
