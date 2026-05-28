@echo off
cd /d "%~dp0"
echo.
echo  3ds Max MCP Tool Inspector
echo  Manual testing only — nothing runs until you click a button.
echo  Max must be open with the MCP bridge loaded.
echo.
uv run python scripts/tool_playground.py
if errorlevel 1 pause
