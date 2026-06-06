$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot "env.ps1")
$env:PYTHONPATH = Join-Path $root "backend"
$env:LOCAL_CHATBOT_PORT = "8765"

python -m local_chatbot.cli --port 8765
