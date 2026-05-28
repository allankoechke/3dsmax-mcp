from pathlib import Path

import install


def test_max_year_for_reads_standard_install_folder_names() -> None:
    assert install.max_year_for(Path(r"C:\Program Files\Autodesk\3ds Max 2023")) == 2023
    assert install.max_year_for(Path(r"C:\Program Files\Autodesk\3ds Max 2027")) == 2027
    assert install.max_year_for(Path(r"C:\weird\Max")) is None


def test_native_bridge_sources_are_exact_versioned_binaries() -> None:
    for year in (2023, 2024, 2025, 2026, 2027):
        assert install.GUP_SRCS[year].name == f"mcp_bridge_{year}.gup"
        assert install.gup_src_for(Path(fr"C:\Program Files\Autodesk\3ds Max {year}")) == install.GUP_SRCS[year]

    assert install.gup_src_for(Path(r"C:\Program Files\Autodesk\3ds Max 2028")) is None


def test_app_mcp_config_paths_includes_cursor() -> None:
    labels = [label for label, _ in install.app_mcp_config_paths()]
    paths = [path for _, path in install.app_mcp_config_paths()]
    assert "Cursor" in labels
    assert paths[labels.index("Cursor")] == Path.home() / ".cursor" / "mcp.json"


def test_mcp_server_entry_uses_uv_run() -> None:
    entry = install.mcp_server_entry(r"C:\repo\3dsmax-mcp")
    assert entry == {
        "command": "uv",
        "args": ["run", "--directory", r"C:\repo\3dsmax-mcp", "3dsmax-mcp"],
    }
