import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.tools.material_ops import create_shell_material
from src.tools.material_shell import build_shell_wrap_maxscript


class ShellMaterialTests(unittest.TestCase):
    def test_wrap_existing_materials(self) -> None:
        ms = build_shell_wrap_maxscript(
            "MyShell",
            render_material="OctaneMat",
            export_material="ExportMat",
            assign_to=["Box001"],
        )
        self.assertIn("mcp_findMaterialByName", ms)
        self.assertIn('"OctaneMat"', ms)
        self.assertIn('"ExportMat"', ms)
        self.assertIn("Shell_Material()", ms)
        self.assertIn("shell.originalMaterial = renderMat", ms)
        self.assertIn("shell.bakedMaterial = exportMat", ms)
        self.assertNotIn("ai_multiply", ms)

    def test_create_shell_wraps_by_name(self) -> None:
        with patch(
            "src.tools.material_ops.client.send_command",
            return_value={"result": '{"status":"success","workflow":"shell_wrap"}'},
        ) as send:
            result = create_shell_material(
                "PlantShell",
                render_material="xikkdhjja",
                export_material="xikkdhjja_export",
            )

        self.assertIn("success", result)
        send.assert_called_once()
        ms = send.call_args.args[0]
        self.assertIn("shell_wrap", ms)
        self.assertIn("mcp_findMaterialByName", ms)

    def test_create_shell_builds_any_renderer_from_textures(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "asset_basecolor.png").write_bytes(b"x")
            (root / "asset_roughness.png").write_bytes(b"x")

            with patch(
                "src.tools.material_ops.client.send_command",
                return_value={"result": '{"status":"success"}'},
            ) as send:
                create_shell_material(
                    "DualShell",
                    texture_folder=tmp,
                    render_material_class="octane",
                    export_material_class="OpenPBRMaterial",
                )

        ms = send.call_args.args[0]
        self.assertIn("Std_Surface_Mtl", ms)
        self.assertIn("OpenPBRMaterial", ms)
        self.assertIn("shell.originalMaterial = renderMat", ms)
        self.assertIn("shell.bakedMaterial = exportMat", ms)

    def test_create_shell_requires_render_or_textures(self) -> None:
        result = create_shell_material("EmptyShell")
        self.assertIn("render_material is required", result)


if __name__ == "__main__":
    unittest.main()
