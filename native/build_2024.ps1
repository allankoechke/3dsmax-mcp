[CmdletBinding()]
param(
    [string]$MaxSdkPath = $env:MAXSDK_PATH,
    [string]$CMakePath = $env:CMAKE_EXE,
    [string]$Generator = "Visual Studio 17 2022",
    [string]$Toolset = "v142",
    [switch]$Deploy
)

$ErrorActionPreference = "Stop"

$NativeDir = $PSScriptRoot
if (-not $NativeDir) {
    $NativeDir = Split-Path -Parent $MyInvocation.MyCommand.Path
}

if (-not $MaxSdkPath) {
    $MaxSdkPath = "C:\Program Files\Autodesk\3ds Max 2024 SDK\maxsdk"
}

function Resolve-CMake {
    param([string]$ExplicitPath)

    if ($ExplicitPath) {
        if (Test-Path -LiteralPath $ExplicitPath) {
            return (Resolve-Path -LiteralPath $ExplicitPath).Path
        }
        throw "CMakePath was set but does not exist: $ExplicitPath"
    }

    $fromPath = Get-Command cmake.exe -ErrorAction SilentlyContinue
    if ($fromPath) {
        return $fromPath.Source
    }

    $defaultPath = "C:\Program Files\CMake\bin\cmake.exe"
    if (Test-Path -LiteralPath $defaultPath) {
        return $defaultPath
    }

    throw "cmake.exe was not found. Install CMake 3.20+ or pass -CMakePath."
}

$MaxHeader = Join-Path $MaxSdkPath "include\max.h"
if (-not (Test-Path -LiteralPath $MaxHeader)) {
    throw "3ds Max 2024 SDK was not found at '$MaxSdkPath'. Install the SDK or pass -MaxSdkPath."
}

$CMakeExe = Resolve-CMake -ExplicitPath $CMakePath
$BuildDir = Join-Path $NativeDir "build-2024"
$OutDir = Join-Path $NativeDir "bin"
$BuiltGup = Join-Path $BuildDir "Release\mcp_bridge.gup"
$StagedGup = Join-Path $OutDir "mcp_bridge_2024.gup"

New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

$ConfigureArgs = @(
    "-S", $NativeDir,
    "-B", $BuildDir,
    "-G", $Generator,
    "-A", "x64",
    "-DMAX_VERSION=2024",
    "-DMAXSDK_PATH=$MaxSdkPath"
)
if ($Toolset) {
    $ConfigureArgs += @("-T", $Toolset)
}

Write-Host "[1/3] Configuring 3ds Max 2024 native bridge"
& $CMakeExe @ConfigureArgs
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host "[2/3] Building Release"
& $CMakeExe --build $BuildDir --config Release
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

if (-not (Test-Path -LiteralPath $BuiltGup)) {
    throw "Build finished but output was not found: $BuiltGup"
}

Write-Host "[3/3] Staging native/bin/mcp_bridge_2024.gup"
Copy-Item -LiteralPath $BuiltGup -Destination $StagedGup -Force
Write-Host "OK: $StagedGup"

if ($Deploy) {
    $PluginDir = "C:\Program Files\Autodesk\3ds Max 2024\plugins"
    $PluginDst = Join-Path $PluginDir "mcp_bridge.gup"
    Write-Host "Deploying to $PluginDst"
    try {
        Copy-Item -LiteralPath $StagedGup -Destination $PluginDst -Force
        Write-Host "OK: deployed"
    }
    catch [System.UnauthorizedAccessException] {
        $CopyScript = "Copy-Item -LiteralPath '$StagedGup' -Destination '$PluginDst' -Force"
        Start-Process powershell.exe -ArgumentList "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", $CopyScript -Verb RunAs -Wait
        Write-Host "OK: deploy command completed"
    }
}
