"""Data Channel modifier tools — procedural per-vertex/face data processing.

The Data Channel modifier is 3ds Max's node-based data processing system
(similar to Houdini VOPs) that lives in the modifier stack. It chains
operators that read mesh data, process it, and output to channels like
position, selection, vertex color, UVs, normals, etc.

One object should have at most one Data Channel modifier in normal use.
Operators are appended to that modifier's internal substack — not by adding
another Data Channel modifier on the object stack.
"""

from __future__ import annotations

import json as _json
from typing import Optional

from ..server import mcp, client
from ..coerce import DictList, IntList
from src.helpers.maxscript import safe_string


# Maps operator names to their (idA, idB) class IDs for AddOperator().
_OP_IDS = {
    "vertex_input":       (3658656257, 0),
    "face_input":         (38019502, 0),
    "edge_input":         (590351565, 0),
    "xyz_space":          (236038690, 0),
    "component_space":    (236038707, 0),
    "curvature":          (236108612, 0),
    "velocity":           (237091669, 0),
    "node_influence":     (3416675101, 0),
    "tension_deform":     (1215902043, 0),
    "distort":            (301607866, 0),
    "maxscript":          (2597005274, 0),
    "maxscript_process":  (3180516783, 0),
    "expression_float":   (1185521650, 0),
    "expression_point3":  (1185521649, 0),
    "vector":             (1155607757, 0),
    "scale":              (283192250, 0),
    "clamp":              (551627706, 0),
    "invert":             (1135524769, 0),
    "normalize":          (103725985, 0),
    "curve":              (1944136634, 0),
    "smooth":             (2481007546, 0),
    "decay":              (284830921, 0),
    "point3_to_float":    (1137503061, 0),
    "convert_subobject":  (2888899789, 0),
    "geo_quantize":       (496046533, 0),
    "color_space":        (3257339550, 0),
    "vertex_output":      (2882382387, 0),
    "face_output":        (52689454, 0),
    "edge_output":        (17934909, 0),
    "transform_elements": (655960264, 0),
    "color_elements":     (1270620223, 0),
    "delta_mush":         (3367109027, 0),
}


def _mxs_str(value: str) -> str:
    return safe_string(value)


def _mxs_object_block(name: str, body: str, *, not_found: str = "") -> str:
    safe_name = _mxs_str(name)
    msg = not_found or f"Object not found: {name}"
    safe_msg = msg.replace("\\", "\\\\").replace('"', '\\"')
    indented = "\n        ".join(line for line in body.splitlines() if line.strip())
    return f"""(
    local obj = getNodeByName "{safe_name}"
    if obj == undefined then "{safe_msg}"
    else
    (
        {indented}
    )
)"""


def _escape_script_literal(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("\t", "\\t")
    )


def _format_add_result(raw: str) -> str:
    if raw.startswith("OK|"):
        parts = raw.split("|", 6)
        if len(parts) >= 7:
            _, created, mod_idx, added, total, order, obj_name = parts
            return _json.dumps({
                "modifier": "Data Channel",
                "createdModifier": created == "1",
                "modifierStackIndex": int(mod_idx),
                "operatorsAdded": int(added),
                "operatorsTotal": int(total),
                "order": order,
                "object": obj_name,
            })
        # Legacy fallback
        _, op_count, order, obj_name = raw.split("|", 3)
        return _json.dumps({
            "modifier": "Data Channel",
            "operators": int(op_count),
            "order": order,
            "object": obj_name,
        })
    return raw


def _resolve_dc_modifier_lines(
    *,
    modifier_index: int,
    create_new: bool,
    display: bool,
) -> list[str]:
    """MAXScript to get or create the single Data Channel modifier on the object."""
    display_lit = "true" if display else "false"
    return [
        "local dcMod = undefined",
        "local created = 0",
        "local modStackIndex = 0",
        f"local forceNew = {'true' if create_new else 'false'}",
        f"local targetModIndex = {modifier_index}",
        "if forceNew then () else if targetModIndex > 0 then (",
        "    if targetModIndex <= obj.modifiers.count and classof obj.modifiers[targetModIndex] == DataChannelModifier do (",
        "        dcMod = obj.modifiers[targetModIndex]",
        "        modStackIndex = targetModIndex",
        "    )",
        ") else (",
        "    for i = 1 to obj.modifiers.count do (",
        "        if classof obj.modifiers[i] == DataChannelModifier do (",
        "            dcMod = obj.modifiers[i]",
        "            modStackIndex = i",
        "            exit",
        "        )",
        "    )",
        ")",
        "if dcMod == undefined then (",
        "    dcMod = DataChannelModifier()",
        f"    dcMod.display = {display_lit}",
        "    addModifier obj dcMod",
        "    modStackIndex = 1",
        "    created = 1",
        ")",
        "local dcIF = dcMod.DataChannelModifier",
        "local beforeCount = dcMod.operators.count",
    ]


def _operator_lines(operators: list[dict]) -> list[str]:
    """Generate MAXScript to append operators to the DC internal stack."""
    lines: list[str] = []
    for op in operators:
        op_type = op.get("type", "").lower()
        if op_type not in _OP_IDS:
            raise ValueError(
                f"Unknown operator type: {op_type}. "
                f"Available: {', '.join(sorted(_OP_IDS.keys()))}"
            )
        id_a, id_b = _OP_IDS[op_type]
        lines.append(f"dcIF.AddOperator {id_a}L {id_b}L (dcIF.StackCount())")

    for i, op in enumerate(operators):
        params = op.get("params", {})
        idx = f"beforeCount + {i + 1}"
        for key, val in params.items():
            target = f"dcMod.operators[{idx}]"
            if key == "node" and isinstance(val, str):
                safe_node = _mxs_str(val)
                lines.append(f'{target}.{key} = getNodeByName "{safe_node}"')
            elif key == "script" and isinstance(val, str):
                safe_script = _escape_script_literal(val)
                lines.append(f'{target}.{key} = "{safe_script}"')
            elif isinstance(val, bool):
                lines.append(f'{target}.{key} = {"true" if val else "false"}')
            elif isinstance(val, (int, float)):
                lines.append(f'{target}.{key} = {val}')
            elif isinstance(val, str):
                lines.append(f'{target}.{key} = {val}')

    for i, op in enumerate(operators):
        blend = op.get("blend")
        if blend is not None:
            idx = f"beforeCount + {i + 1}"
            lines.append(f"dcMod.operator_ops[{idx}] = {blend}")

    return lines


def _result_line() -> str:
    return (
        '"OK|" + (created as string) + "|" + (modStackIndex as string) + "|" + '
        "((dcMod.operators.count - beforeCount) as string) + \"|\" + "
        "(dcMod.operators.count as string) + \"|\" + "
        "(dcMod.operator_order as string) + \"|\" + obj.name"
    )


@mcp.tool()
def add_data_channel(
    name: str,
    operators: DictList,
    order: Optional[IntList] = None,
    display: bool = True,
    modifier_index: int = 0,
    create_new: bool = False,
) -> str:
    """Append operators to a Data Channel modifier's internal stack.

    Reuses the first Data Channel modifier on the object by default. Operators
    are added via DataChannelModifier.AddOperator at StackCount() — not by
    stacking another Data Channel modifier on the object.

    modifier_index: 1-based object modifier stack slot (must be Data Channel).
    create_new: force a new Data Channel modifier on the object stack.
    """
    if not operators:
        return _json.dumps({
            "error": "operators must include at least one entry "
            "(typical graph: vertex_input + vertex_output)",
        })

    try:
        op_lines = _operator_lines(list(operators))
    except ValueError as exc:
        return _json.dumps({"error": str(exc)})

    body_lines = [
        *_resolve_dc_modifier_lines(
            modifier_index=modifier_index,
            create_new=create_new,
            display=display,
        ),
        *op_lines,
    ]
    if order is not None:
        order_str = ", ".join(str(o) for o in order)
        body_lines.append(f"dcMod.operator_order = #({order_str})")
    body_lines.append(_result_line())

    maxscript = _mxs_object_block(name, "\n        ".join(body_lines))
    response = client.send_command(maxscript)
    return _format_add_result(response.get("result", str(response)))


@mcp.tool()
def inspect_data_channel(
    name: str,
    modifier_index: int = 1,
) -> str:
    """Inspect a Data Channel modifier's operator graph."""
    safe = _mxs_str(name)
    maxscript = f"""(
    local obj = getNodeByName "{safe}"
    if obj == undefined then "Object not found: {safe}"
    else
    (
        local dcMod = undefined
        local modStackIndex = 0
        if {modifier_index} > 0 and {modifier_index} <= obj.modifiers.count do (
            local m = obj.modifiers[{modifier_index}]
            if classof m == DataChannelModifier do (
                dcMod = m
                modStackIndex = {modifier_index}
            )
        )
        if dcMod == undefined do (
            for i = 1 to obj.modifiers.count do (
                local m = obj.modifiers[i]
                if classof m == DataChannelModifier do (
                    dcMod = m
                    modStackIndex = i
                    exit
                )
            )
        )
        if dcMod == undefined then "No DataChannelModifier found on " + obj.name
        else
        (
            local result = "{{\\n"
            result += "  \\"object\\": \\"" + obj.name + "\\",\\n"
            result += "  \\"modifierStackIndex\\": " + modStackIndex as string + ",\\n"
            result += "  \\"display\\": " + dcMod.display as string + ",\\n"
            result += "  \\"order\\": \\"" + dcMod.operator_order as string + "\\",\\n"
            result += "  \\"blend_modes\\": \\"" + dcMod.operator_ops as string + "\\",\\n"
            result += "  \\"operators\\": [\\n"

            for i = 1 to dcMod.operators.count do (
                local op = dcMod.operators[i]
                local cls = (classof op) as string
                local enabled = dcMod.operator_enabled[i]
                local frozen = dcMod.operator_frozen[i]

                result += "    {{\\"index\\": " + i as string
                result += ", \\"class\\": \\"" + cls + "\\""
                result += ", \\"enabled\\": " + enabled as string
                result += ", \\"frozen\\": " + frozen as string

                local props = getPropNames op
                for p in props where p != #deprecated do (
                    local val = try ((getProperty op p) as string) catch "?"
                    local pname = p as string
                    if pname == "script" and val.count > 200 do (
                        val = (substring val 1 200) + "..."
                    )
                    val = substituteString val "\\"" "'"
                    val = substituteString val "\\n" " "
                    result += ", \\"" + pname + "\\": \\"" + val + "\\""
                )

                result += "}}"
                if i < dcMod.operators.count do result += ","
                result += "\\n"
            )

            result += "  ]\\n}}"
            result
        )
    )
)"""
    response = client.send_command(maxscript)
    return response.get("result", str(response))


@mcp.tool()
def set_data_channel_operator(
    name: str,
    operator_index: int,
    params: dict,
    modifier_index: int = 0,
) -> str:
    """Set properties on a specific operator in a Data Channel modifier."""
    safe = _mxs_str(name)
    param_lines: list[str] = []
    for key, val in params.items():
        if key == "node" and isinstance(val, str):
            safe_node = _mxs_str(val)
            param_lines.append(f'op.{key} = getNodeByName "{safe_node}"')
        elif key == "script" and isinstance(val, str):
            safe_script = _escape_script_literal(val)
            param_lines.append(f'op.{key} = "{safe_script}"')
        elif isinstance(val, bool):
            param_lines.append(f'op.{key} = {"true" if val else "false"}')
        elif isinstance(val, (int, float)):
            param_lines.append(f'op.{key} = {val}')
        elif isinstance(val, str):
            param_lines.append(f'op.{key} = {val}')

    param_block = "\n            ".join(param_lines) if param_lines else ""
    if modifier_index > 0:
        maxscript = f"""(
    local obj = getNodeByName "{safe}"
    if obj == undefined then "Object not found: {safe}"
    else if {modifier_index} > obj.modifiers.count then "Modifier index out of range"
    else if classof obj.modifiers[{modifier_index}] != DataChannelModifier then "Not a DataChannelModifier at index {modifier_index}"
    else if {operator_index} < 1 then "operator_index must be 1-based"
    else if {operator_index} > obj.modifiers[{modifier_index}].operators.count then "Operator index out of range"
    else
    (
        local dcMod = obj.modifiers[{modifier_index}]
        local op = dcMod.operators[{operator_index}]
        {param_block}
        "Updated operator {operator_index} (" + (classof op) as string + ") on " + obj.name + " [DC stack {modifier_index}]"
    )
)"""
    else:
        maxscript = f"""(
    local obj = getNodeByName "{safe}"
    if obj == undefined then "Object not found: {safe}"
    else
    (
        local dcMod = undefined
        local modStackIndex = 0
        for i = 1 to obj.modifiers.count do (
            if classof obj.modifiers[i] == DataChannelModifier do (
                dcMod = obj.modifiers[i]
                modStackIndex = i
                exit
            )
        )
        if dcMod == undefined then "No DataChannelModifier found on " + obj.name
        else if {operator_index} < 1 then "operator_index must be 1-based"
        else if {operator_index} > dcMod.operators.count then "Operator index out of range"
        else
        (
            local op = dcMod.operators[{operator_index}]
            {param_block}
            "Updated operator {operator_index} (" + (classof op) as string + ") on " + obj.name + " [DC stack " + modStackIndex as string + "]"
        )
    )
)"""
    response = client.send_command(maxscript)
    return response.get("result", str(response))


@mcp.tool()
def add_dc_script_operator(
    name: str,
    script: str,
    element_type: int = 0,
    data_type: int = 0,
    output_to: str = "selection",
    modifier_index: int = 0,
    create_new: bool = False,
) -> str:
    """Add a MAXScript operator to a Data Channel modifier's internal stack."""
    safe = _mxs_str(name)

    if "on Process" not in script:
        script = f"""on Process theNode theMesh elementType outputType outputArray do
(
    if theMesh == undefined then return 0
    local nv = polyop.getNumVerts theMesh
    local nf = polyop.getNumFaces theMesh
{script}
)"""

    safe_script = _escape_script_literal(script)

    output_config = {
        "selection":     ("vertex_output", 4, 1),
        "position":      ("vertex_output", 0, 1),
        "vertex_color":  ("vertex_output", 1, 0),
        "map_channel":   ("vertex_output", 2, 1),
        "normals":       ("vertex_output", 3, 1),
        "mat_id":        ("face_output", 1, 0),
    }

    out_type, out_val, out_chan = output_config.get(output_to, ("vertex_output", 4, 1))
    mxs_id_a, mxs_id_b = _OP_IDS["maxscript"]

    if modifier_index > 0 and not create_new:
        maxscript = f"""(
    local obj = getNodeByName "{safe}"
    if obj == undefined then "Object not found: {safe}"
    else if {modifier_index} > obj.modifiers.count then "Modifier index out of range"
    else if classof obj.modifiers[{modifier_index}] != DataChannelModifier then "Not a DataChannelModifier"
    else
    (
        local dcMod = obj.modifiers[{modifier_index}]
        local dcIF = dcMod.DataChannelModifier
        local beforeCount = dcMod.operators.count
        dcIF.AddOperator {mxs_id_a}L {mxs_id_b}L (dcIF.StackCount())
        local scriptOp = dcMod.operators[beforeCount + 1]
        scriptOp.script = "{safe_script}"
        scriptOp.elementtype = {element_type}
        scriptOp.DataType = {data_type}
        "Added Script Operator to " + obj.name + " -> output: {output_to}"
    )
)"""
    else:
        out_id_a, out_id_b = _OP_IDS[out_type]
        body = [
            *_resolve_dc_modifier_lines(
                modifier_index=modifier_index,
                create_new=create_new,
                display=True,
            ),
            f"dcIF.AddOperator {mxs_id_a}L {mxs_id_b}L (dcIF.StackCount())",
            "local scriptIdx = beforeCount + 1",
            f'dcMod.operators[scriptIdx].script = "{safe_script}"',
            f"dcMod.operators[scriptIdx].elementtype = {element_type}",
            f"dcMod.operators[scriptIdx].DataType = {data_type}",
            "if beforeCount == 0 do (",
            f"    dcIF.AddOperator {out_id_a}L {out_id_b}L (dcIF.StackCount())",
            f"    dcMod.operators[2].output = {out_val}",
            f"    dcMod.operators[2].channelNum = {out_chan}",
            ")",
            f'"Added Script Operator to " + obj.name + " -> output: {output_to}"',
        ]
        maxscript = _mxs_object_block(name, "\n        ".join(body))

    response = client.send_command(maxscript)
    return response.get("result", str(response))


@mcp.tool()
def list_dc_presets() -> str:
    """List all available Data Channel modifier presets."""
    maxscript = """(
    local b = Box name:"__dc_temp__" length:1 width:1 height:1
    convertToMesh b
    local dcMod = DataChannelModifier()
    addModifier b dcMod
    local dcIF = dcMod.DataChannelModifier
    dcIF.GatherOperators()

    local count = dcIF.PresetCount()
    local result = "["
    for i = 1 to count do (
        local pname = ""
        dcIF.PresetName i &pname
        result += "\\"" + pname + "\\""
        if i < count do result += ", "
    )
    result += "]"
    delete b
    result
)"""
    response = client.send_command(maxscript)
    return response.get("result", str(response))


@mcp.tool()
def load_dc_preset(
    name: str,
    preset_name: str,
    modifier_index: int = 0,
    create_new: bool = False,
) -> str:
    """Load a Data Channel preset into the object's DC modifier internal stack."""
    safe_preset = _mxs_str(preset_name)
    body = [
        *_resolve_dc_modifier_lines(
            modifier_index=modifier_index,
            create_new=create_new,
            display=True,
        ),
        f'dcIF.LoadPreset "{safe_preset}"',
        f'"Loaded preset \'{safe_preset}\' onto " + obj.name + " (" + dcIF.StackCount() as string + " operators, DC stack " + modStackIndex as string + ")"',
    ]
    maxscript = _mxs_object_block(name, "\n        ".join(body))
    response = client.send_command(maxscript)
    return response.get("result", str(response))
