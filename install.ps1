[CmdletBinding()]
param(
    [string]$Version = "latest",
    [switch]$Editable
)

$ErrorActionPreference = "Stop"

function Find-Python {
    $launcher = Get-Command py.exe -ErrorAction SilentlyContinue
    if ($null -ne $launcher) {
        return @{ Path = $launcher.Source; Arguments = @("-3") }
    }

    $python = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($null -ne $python) {
        return @{ Path = $python.Source; Arguments = @() }
    }

    throw "Python 3.11 or newer is required; install Python from python.org and retry."
}

function Invoke-Python([hashtable]$Python, [string[]]$Arguments) {
    & $Python.Path @($Python.Arguments + $Arguments)
    if ($LASTEXITCODE -ne 0) {
        throw "Python command failed with exit code $LASTEXITCODE."
    }
}

function Install-Runtime([hashtable]$Python, [string]$VenvPath, [string]$Package) {
    if (-not (Test-Path -LiteralPath $VenvPath -PathType Container)) {
        Invoke-Python $Python @("-m", "venv", $VenvPath)
    }

    $venvPython = Join-Path $VenvPath "Scripts\python.exe"
    if (-not (Test-Path -LiteralPath $venvPython -PathType Leaf)) {
        throw "The venv Python was not created at $venvPython."
    }

    & $venvPython -m pip install --quiet --upgrade pip
    if ($LASTEXITCODE -ne 0) {
        throw "pip bootstrap failed for $VenvPath."
    }
    & $venvPython -m pip install --quiet --upgrade $Package
    if ($LASTEXITCODE -ne 0) {
        throw "louke installation failed for $VenvPath."
    }
}

function Get-RuntimeVersion([string]$VenvPath) {
    $venvPython = Join-Path $VenvPath "Scripts\python.exe"
    $installed = (& $venvPython -c "import importlib.metadata; print(importlib.metadata.version('louke'))").Trim()
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($installed)) {
        throw "Could not verify the installed louke version in $VenvPath."
    }
    return $installed
}

function Add-UserPathEntry([string]$Entry) {
    $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
    $entries = @($userPath -split ";" | Where-Object { $_ })
    if ($entries -notcontains $Entry) {
        [Environment]::SetEnvironmentVariable("Path", (($entries + $Entry) -join ";"), "User")
    }
    if (($env:Path -split ";") -notcontains $Entry) {
        $env:Path = "$Entry;$env:Path"
    }
}

function Install-LocalFirstShim([string]$GlobalVenv) {
    $shimDir = Join-Path $env:USERPROFILE ".louke\bin"
    New-Item -ItemType Directory -Force -Path $shimDir | Out-Null
    $shim = Join-Path $shimDir "lk.cmd"
    $content = @"
@echo off
if exist "%CD%\.venv\Scripts\python.exe" (
  set "LOUKE_RUNTIME_MODE=local"
  "%CD%\.venv\Scripts\python.exe" -m louke %*
  exit /b %ERRORLEVEL%
)
if exist "$GlobalVenv\Scripts\python.exe" (
  set "LOUKE_RUNTIME_MODE=global"
  "$GlobalVenv\Scripts\python.exe" -m louke %*
  exit /b %ERRORLEVEL%
)
echo no louke runtime found; run install.bat / install.ps1 / lk install first 1>&2
exit /b 1
"@
    Set-Content -LiteralPath $shim -Value $content -Encoding ASCII
    Add-UserPathEntry $shimDir
}

try {
    $python = Find-Python
    $versionText = (& $python.Path @($python.Arguments + @("-c", "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"))).Trim()
    $version = [version]$versionText
    if ($version -lt [version]"3.11") {
        throw "Python 3.11 or newer is required (found $versionText)."
    }

    $package = if ($Editable) { (Get-Location).Path } elseif ($Version -eq "latest") { "louke" } else { "louke==$Version" }
    $projectVenv = Join-Path (Get-Location) ".venv"
    $globalVenv = Join-Path $env:USERPROFILE ".louke\venv"
    Install-Runtime $python $projectVenv $package
    Install-Runtime $python $globalVenv $package

    $projectVersion = Get-RuntimeVersion $projectVenv
    $globalVersion = Get-RuntimeVersion $globalVenv
    if ($projectVersion -ne $globalVersion) {
        throw "Runtime version mismatch: local=$projectVersion global=$globalVersion."
    }
    if (-not $Editable -and $Version -ne "latest" -and $projectVersion -ne $Version) {
        throw "Requested louke $Version but installed $projectVersion."
    }

    Install-LocalFirstShim $globalVenv

    Write-Output "louke $projectVersion installed in $projectVenv and $globalVenv; local-first lk shim installed"
    exit 0
}
catch {
    Write-Error $_.Exception.Message
    exit 1
}
