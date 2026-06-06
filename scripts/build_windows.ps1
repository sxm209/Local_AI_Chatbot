$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot "env.ps1")

$backendBinary = Join-Path $root "src-tauri\binaries\local-chatbot-backend-x86_64-pc-windows-msvc.exe"
$env:CARGO_TARGET_DIR = Join-Path $root "cargo-target"
New-Item -ItemType Directory -Force $env:CARGO_TARGET_DIR | Out-Null

if (!(Get-Command npm -ErrorAction SilentlyContinue)) {
  throw "npm is required to build the frontend."
}
if (!(Get-Command cargo -ErrorAction SilentlyContinue)) {
  throw "Rust/Cargo is required to build the Tauri installer."
}
if (!(Test-Path $backendBinary)) {
  throw "Backend sidecar is missing. Run .\scripts\build_backend.ps1 first."
}

Push-Location (Join-Path $root "frontend")
npm.cmd install
Pop-Location

Push-Location (Join-Path $root "src-tauri")
cargo tauri build
Pop-Location
