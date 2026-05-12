"""Shell Material + UberBitmap helpers for material tools."""

from __future__ import annotations

from pathlib import Path

from src.helpers.maxscript import safe_string


# MultiOutputChannelTexmapToTexmap output indices for UberBitmap2:
#   1=Col(RGB), 2=R, 3=G, 4=B, 5=A, 6=Luminance, 7=Average
UBER_OUT_COL = 1
UBER_OUT_R = 2
UBER_OUT_G = 3
UBER_OUT_B = 4


def _ms_path(value: str | Path) -> str:
    return str(value).replace("\\", "/")


def ms_uber_bitmap(var: str, name: str, filepath: str | Path) -> list[str]:
    """Generate MAXScript lines to create a UberBitmap OSLMap."""
    fp = safe_string(_ms_path(filepath))
    return [
        f"{var} = OSLMap()",
        f'{var}.name = "{safe_string(name)}"',
        f"{var}.OSLPath = oslPath",
        f"{var}.OSLAutoUpdate = true",
        f'{var}.filename = @"{fp}"',
    ]


def ms_channel_selector(var: str, source_var: str, output_index: int) -> list[str]:
    """Generate MAXScript lines for a MultiOutputChannelTexmapToTexmap."""
    return [
        f"{var} = MultiOutputChannelTexmapToTexmap()",
        f"{var}.sourceMap = {source_var}",
        f"{var}.outputChannelIndex = {output_index}",
    ]


def build_shell_maxscript(
    shell_name: str,
    render_name: str,
    base_color_path: str | Path,
    orm_path: str | Path,
    normal_path: str | Path | None,
    gltf_material_name: str | None,
    assign_to: list[str] | None,
    *,
    create_export_material: bool = True,
) -> str:
    """Build MAXScript for Shell Material with UberBitmap RGB split Arnold setup."""
    lines: list[str] = []
    safe_shell = safe_string(shell_name)
    safe_render = safe_string(render_name)
    export_mat_name = safe_string(gltf_material_name or f"{render_name}_gltf")

    lines.extend([
        'oslPath = (getDir #maxRoot) + "OSL\\\\UberBitmap2.osl"',
        "fn mcp_setFirstMap target propNames tex = (",
        "    for propName in propNames do (",
        "        try (setProperty target (propName as name) tex; return propName) catch ()",
        "    )",
        "    undefined",
        ")",
        "fn mcp_enableMapSlot target slotName = (",
        "    if slotName != undefined do (",
        '        try (setProperty target ((slotName + "_on") as name) true) catch ()',
        '        try (setProperty target ((slotName + "_enable") as name) true) catch ()',
        "    )",
        ")",
        "fn mcp_createGltfExportMaterial matName = (",
        "    local m = undefined",
        "    try (m = glTFMaterial name:matName) catch ()",
        "    if m == undefined do try (m = GLTFMaterial name:matName) catch ()",
        "    if m == undefined do try (m = glTF_Material name:matName) catch ()",
        "    if m == undefined do try (m = OpenPBRMaterial name:matName) catch ()",
        "    if m == undefined do try (m = OpenPBR_Material name:matName) catch ()",
        "    if m == undefined do try (m = PhysicalMaterial name:matName) catch ()",
        '    if m == undefined do throw "No glTF/OpenPBR/Physical export material class is available"',
        "    m",
        ")",
    ])

    lines.append("gltfMat = undefined")
    if gltf_material_name:
        safe_gltf = safe_string(gltf_material_name)
        lines.append("for obj in objects where obj.material != undefined do (")
        lines.append(f'    if obj.material.name == "{safe_gltf}" do (gltfMat = obj.material; exit)')
        lines.append(")")
        lines.append("if gltfMat == undefined do (")
        lines.append("    for obj in objects where obj.material != undefined do (")
        lines.append('        if (classOf obj.material) as string == "Shell_Material" and obj.material.bakedMaterial != undefined do (')
        lines.append(f'            if obj.material.bakedMaterial.name == "{safe_gltf}" do (gltfMat = obj.material.bakedMaterial; exit)')
        lines.append("        )")
        lines.append("    )")
        lines.append(")")
    if create_export_material:
        lines.append(f'if gltfMat == undefined do gltfMat = mcp_createGltfExportMaterial "{export_mat_name}"')

    lines.extend(ms_uber_bitmap("uberBC", f"{safe_render}_diffuse", base_color_path))
    lines.extend(ms_uber_bitmap("uberORM", f"{safe_render}_orm", orm_path))
    lines.extend(ms_channel_selector("bcCol", "uberBC", UBER_OUT_COL))
    lines.extend(ms_channel_selector("ormR", "uberORM", UBER_OUT_R))
    lines.extend(ms_channel_selector("ormG", "uberORM", UBER_OUT_G))
    lines.extend(ms_channel_selector("ormB", "uberORM", UBER_OUT_B))

    lines.extend([
        "mult = ai_multiply()",
        f'mult.name = "{safe_render}_multiply"',
        "mult.input1_shader = bcCol",
        "mult.input2_shader = ormR",
        "arnoldMat = ai_standard_surface()",
        f'arnoldMat.name = "{safe_render}"',
        "arnoldMat.base_color_shader = mult",
        "arnoldMat.specular_roughness_shader = ormG",
        "arnoldMat.metalness_shader = ormB",
    ])

    if create_export_material:
        lines.extend([
            'exportDiffuseSlot = mcp_setFirstMap gltfMat #("base_color_map", "baseColor_map", "basecolor_map", "base_map", "diffuse_map") bcCol',
            "mcp_enableMapSlot gltfMat exportDiffuseSlot",
            'exportRoughSlot = mcp_setFirstMap gltfMat #("roughness_map", "specular_roughness_map", "base_roughness_map") ormG',
            "mcp_enableMapSlot gltfMat exportRoughSlot",
            'exportMetalSlot = mcp_setFirstMap gltfMat #("metalness_map", "metallic_map", "base_metalness_map") ormB',
            "mcp_enableMapSlot gltfMat exportMetalSlot",
        ])

    if normal_path:
        lines.extend(ms_uber_bitmap("uberNrm", f"{safe_render}_normal", normal_path))
        lines.extend(ms_channel_selector("nrmCol", "uberNrm", UBER_OUT_COL))
        lines.extend([
            "nrmMap = ai_normal_map()",
            f'nrmMap.name = "{safe_render}_nrm"',
            "nrmMap.input_shader = nrmCol",
            "bmpNode = ai_bump2d()",
            f'bmpNode.name = "{safe_render}_bump"',
            "bmpNode.normal_shader = nrmMap",
            "arnoldMat.normal_shader = bmpNode",
        ])
        if create_export_material:
            lines.extend([
                'exportNrm = Normal_Bump name:"Export_Normal"',
                "exportNrm.normal_map = nrmCol",
                'exportNrmSlot = mcp_setFirstMap gltfMat #("bump_map", "normal_map") exportNrm',
                "mcp_enableMapSlot gltfMat exportNrmSlot",
            ])

    lines.extend([
        "shell = Shell_Material()",
        f'shell.name = "{safe_shell}"',
        "shell.originalMaterial = arnoldMat",
        "if gltfMat != undefined do shell.bakedMaterial = gltfMat",
        "shell.renderMtlIndex = 0",
        "shell.viewportMtlIndex = 1",
        "assignCount = 0",
    ])

    if assign_to:
        names_arr = "#(" + ", ".join(f'"{safe_string(n)}"' for n in assign_to) + ")"
        lines.append(f"nameList = {names_arr}")
        lines.append("for n in nameList do (obj = getNodeByName n; if obj != undefined then (obj.material = shell; assignCount += 1))")
    elif gltf_material_name:
        safe_gltf = safe_string(gltf_material_name)
        lines.append("if gltfMat != undefined do (")
        lines.append("    for obj in objects where obj.material != undefined do (")
        lines.append(f'        if obj.material == gltfMat or obj.material.name == "{safe_gltf}" do (')
        lines.append("            obj.material = shell; assignCount += 1")
        lines.append("        )")
        lines.append("    )")
        lines.append(")")

    lines.extend([
        'resultJson = "{"',
        'resultJson += "\\"workflow\\":\\"shell_arnold_uberbitmap_orm\\","',
        'resultJson += "\\"shell_name\\":\\"" + shell.name + "\\","',
        'resultJson += "\\"render_material\\":\\"" + arnoldMat.name + "\\","',
        'resultJson += "\\"export_material\\":\\"" + (if gltfMat != undefined then gltfMat.name else "not_found") + "\\","',
        'resultJson += "\\"export_material_class\\":\\"" + (if gltfMat != undefined then ((classOf gltfMat) as string) else "undefined") + "\\","',
        'resultJson += "\\"assigned_count\\":" + (assignCount as string) + ","',
        'resultJson += "\\"status\\":\\"success\\""',
        'resultJson += "}"',
        "resultJson",
    ])

    return "(\n    " + "\n    ".join(lines) + "\n)"
