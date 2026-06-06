$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot "env.ps1")
$env:PYTHONPATH = Join-Path $root "backend"

python -m pytest
