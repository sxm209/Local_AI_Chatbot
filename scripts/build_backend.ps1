$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$venvPython = Join-Path $root ".venv\Scripts\python.exe"
$binaryDir = Join-Path $root "src-tauri\binaries"
$backendName = "local-chatbot-backend"
$targetBinary = Join-Path $binaryDir "$backendName-x86_64-pc-windows-msvc.exe"

if (!(Test-Path $venvPython)) {
  python -m venv (Join-Path $root ".venv")
}

& $venvPython -m pip install --upgrade pip
& $venvPython -m pip install -e "$root[dev]"
& $venvPython -m PyInstaller --onefile --name $backendName --paths (Join-Path $root "backend") (Join-Path $root "backend\run_backend.py")

New-Item -ItemType Directory -Force $binaryDir | Out-Null
Copy-Item -Force (Join-Path $root "dist\$backendName.exe") $targetBinary
Write-Host "Backend sidecar written to $targetBinary"
