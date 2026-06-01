from pathlib import Path


def test_tcp_timer_tick_does_not_probe_native_bridge() -> None:
    script = Path("maxscript/mcp_server.ms").read_text()
    on_tick = script.split("fn onTick sender args =", 1)[1].split("-- Start the TCP server", 1)[0]

    assert "nativeBridgeAvailable" not in on_tick
    assert "windows.getChildHWND" not in on_tick
