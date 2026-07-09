# 3ds Max MCP crash report — ATTO 2 CGTrader Physical import

**Date:** 2026-07-02 (~17:43 local)  
**Scene:** BYD ATTO 2 — CGTrader FBX import (`PhysicalMaterial` on car meshes)  
**Outcome:** 3ds Max crashed during agent **discovery** calls. **No conversion MaxScript was executed.**

---

## What the agent did (single parallel batch)

The agent fired **4 tools at once** before any material conversion:

| # | Tool | Server | Arguments | Reached Max? |
|---|------|--------|-----------|--------------|
| 1 | `get_materials` | `user-3dsmax-mcp` | `{}` | **Yes** — `native:get_materials` |
| 2 | `query_scene` | `user-3dsmax-mcp` | `{"action":"class","class_name":"PhysicalMaterial","limit":200}` | **Yes** — native then MaxScript fallback |
| 3 | `execute_maxscript` | `user-3dsmax-mcp` | `{"code":"maxFilePath + maxFileName"}` | **Likely queued** — never returned |
| 4 | `Shell` (PowerShell) | host | `Get-ChildItem -Recurse` on texture folder | **No** — does not touch Max |

Cursor MCP log (`mcp-server-user-3dsmax-mcp.log`):

```
2026-07-02 17:43:08.833 [error] Processing request of type CallToolRequest
2026-07-02 17:43:08.976 [error] Processing request of type CallToolRequest
2026-07-02 17:43:47.516 [error] Processing request of type CallToolRequest
```

All three MCP calls were **interrupted after ~69s** (Cursor tool timeout). Max crashed during or shortly after this window.

**Important:** The agent never ran conversion logic. This was purely scene introspection on a heavy newly-imported FBX.

---

## Call 1 — `get_materials`

### MCP surface

```json
{
  "server": "user-3dsmax-mcp",
  "toolName": "get_materials",
  "arguments": {}
}
```

### Python path

`src/tools/materials.py` → `client.send_command("{}", cmd_type="native:get_materials")`

### Native handler

`native/src/handlers/inspect_handlers.cpp` — `NativeHandlers::GetMaterials`

```cpp
CollectNodes(root, allNodes);           // full scene tree walk
for (INode* node : allNodes) {
    Mtl* mtl = node->GetMtl();
    // dedupe by pointer
    for (INode* n2 : allNodes) {        // nested full-tree scan per unique material
        if (n2->GetMtl() == mtl) users.push_back(...);
    }
}
```

**Complexity:** O(N × M) where N = all nodes, M = unique top-level materials.

**CGTrader risk:** FBX imports often explode into **thousands of mesh nodes** with **many unique Physical materials**. This handler does not traverse Multi/Sub slots — only `node->GetMtl()` — but the nested `usedBy` loop still scales badly.

---

## Call 2 — `query_scene` (class = PhysicalMaterial)

### MCP surface

```json
{
  "server": "user-3dsmax-mcp",
  "toolName": "query_scene",
  "arguments": {
    "action": "class",
    "class_name": "PhysicalMaterial",
    "limit": 200
  }
}
```

### Python path

`src/tools/_query_scene_core.py` → `run_class_instances(..., scope="auto")`

1. **First:** `native:find_class_instances` with `class_name=PhysicalMaterial`  
   - `native/src/handlers/scene_handlers.cpp`  
   - Matches **`NodeClassName(n) == "PhysicalMaterial"`** on scene **nodes only**  
   - Materials are **not** nodes → returns `totalFound: 0` quickly

2. **Then (scope=auto fallback):** MaxScript via `_class_instances_refs_maxscript`  
   - `src/tools/_query_scene_core.py` lines ~649–676

```maxscript
local cls = execute "PhysicalMaterial"
local insts = getclassinstances cls          -- ALL PhysicalMaterial instances in scene
for i = 1 to amin #(insts.count, 50) do (
    local depNodes = refs.dependentnodes inst  -- dependency graph walk PER material
    ...
)
```

**Note:** `limit: 200` only caps **serialized instances** (`max_show = min(limit, 50)` → **50**).  
`getclassinstances` still enumerates **every** PhysicalMaterial before truncation.

**CGTrader risk:** Dozens–hundreds of Physical materials × `refs.dependentnodes` on a dense mesh graph is a known heavy path in Max and may AV/hang.

---

## Call 3 — `execute_maxscript` (benign, likely never ran)

### MCP surface

```json
{
  "server": "user-3dsmax-mcp",
  "toolName": "execute_maxscript",
  "arguments": {
    "code": "maxFilePath + maxFileName"
  }
}
```

Trivial read. Probably **queued behind** the two heavy handlers and never completed before crash/timeout.

---

## Call 4 — Shell texture listing (not an MCP Max call)

```powershell
Get-ChildItem -Path "C:\Users\ogulc\Projects\BYD\ATTO 2\uploads-files-5949696-BYD+Atto+2+2025_fbx" -Recurse -File
```

External filesystem only. **Cannot crash Max.**

---

## Likely root cause (ranked)

### 1. Heavy dual introspection on a fresh massive FBX (most likely)

Two expensive scene walks dispatched **in the same agent turn**:

- `get_materials` — full node collect + nested material→users scan  
- `query_scene class PhysicalMaterial` — `getclassinstances` + `refs.dependentnodes` per material  

Both post to `MainThreadExecutor` (`WM_MCP_EXECUTE`, default timeout 120s). They run **serially on the Max main thread** but back-to-back on an already heavy scene → UI freeze → possible crash/OOM.

### 2. `get_materials` O(N×M) `usedBy` loop

Patch target: `inspect_handlers.cpp::GetMaterials`

Replace nested scan with single-pass `std::map<Mtl*, json>` accumulation.

### 3. `query_scene` auto-fallback for material classes

Patch target: `_query_scene_core.py::run_class_instances`

When `class_name` is a **material/map class** (not a node class), **skip** `native:find_class_instances` and either:

- go straight to `scope=refs` MaxScript, or  
- add `native:find_ref_instances` that reads `sceneMaterials` / medit without `refs.dependentnodes` on every instance

### 4. Parallel MCP tool calls from the client

Three `CallToolRequest` within ~140ms. Even if Max executes serially, multiple pipe clients may be waiting and agents may retry. Consider **serializing** or **rejecting concurrent** native scene walks.

---

## Suggested MCP patches

### A. `get_materials` — single-pass users map

```cpp
// Pseudocode
std::map<Mtl*, json> matMap;
for (INode* node : allNodes) {
    Mtl* mtl = node->GetMtl();
    if (!mtl) continue;
    auto& matJ = matMap[mtl];
    if (matJ.empty()) { /* init name, class, subMtlCount */ }
    matJ["usedBy"].push_back(nodeName);
}
```

Optional: add `include_used_by: false` param for fast material list only.

### B. `query_scene` class — material-aware path

- Detect material classes: `PhysicalMaterial`, `Std_Surface_Mtl`, `glTFMaterial`, etc.
- For materials, iterate `sceneMaterials` / `getClassInstances` with **`limit` applied before dependency walks**
- Add `scope=refs` param to tool schema docs: **required for material classes**
- Avoid calling `refs.dependentnodes` unless `include_dependents=true`

### C. Scene size guardrails

Before full walks, cheap preflight:

```maxscript
objects.count
(getClassInstances PhysicalMaterial).count
```

If over threshold (e.g. nodes > 3000 or materials > 100), return `{ "warning": "scene too large", "hint": "use execute_maxscript with targeted query" }` instead of full scan.

### D. Agent guidance (AGENTS.md / skill)

On **new heavy imports** (CGTrader FBX, CAD):

1. **Never** parallel `get_materials` + `query_scene class`  
2. Start with `query_scene action=overview` or lightweight `objects.count`  
3. Use targeted `execute_maxscript` for conversion batches  
4. Do not use `query_scene class=PhysicalMaterial` on large scenes — use `for m in sceneMaterials where classOf m == PhysicalMaterial collect m.name`

---

## Repro recipe (for local smoke)

1. Import CGTrader BYD ATTO 2 FBX with Physical materials (large node count).
2. Claim Max instance.
3. In parallel (or rapid sequence):
   - `get_materials {}`
   - `query_scene {"action":"class","class_name":"PhysicalMaterial","limit":200}`
4. Observe hang/crash.

**Control:** same calls on small Box scene → should succeed (as with prior glTF car workflow).

---

## Context from prior successful runs (same MCP, lighter scenes)

Same tools worked on **glTF car imports** (~27 materials, ~61 mesh objects):

- `get_materials` returned in <1s  
- `query_scene class=glTFMaterial` used MaxScript `getclassinstances glTFMaterial` — small instance count  

CGTrader Physical FBX is a different scale and material model.

---

## Files to inspect in repo

| File | Relevance |
|------|-----------|
| `native/src/handlers/inspect_handlers.cpp` | `GetMaterials` nested loop |
| `native/src/handlers/scene_handlers.cpp` | `FindClassInstances` (node-only) |
| `src/tools/_query_scene_core.py` | `run_class_instances`, `_class_instances_refs_maxscript` |
| `src/tools/materials.py` | `get_materials` tool wrapper |
| `native/src/main_thread_executor.cpp` | Main-thread queue, 120s timeout |
| `src/max_client.py` | `DEFAULT_TIMEOUT = 120.0` |

---

## Agent follow-up (after patch)

For ATTO 2 Physical → Octane conversion, prefer **one** `execute_maxscript` batch:

- Iterate `sceneMaterials where classOf m == PhysicalMaterial`
- Map PBR params → `Std_Surface_Mtl`
- Wire textures from  
  `C:\Users\ogulc\Projects\BYD\ATTO 2\uploads-files-5949696-BYD+Atto+2+2025_fbx`
- Skip BYD reference sphere materials (user request)

Do **not** run full-scene discovery on the imported FBX until `get_materials` / `query_scene class` are patched or guarded.
