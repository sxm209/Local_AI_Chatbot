$nodePath = "C:\Program Files\nodejs"
$cargoPath = Join-Path $env:USERPROFILE ".cargo\bin"
$ollamaPath = Join-Path $env:LOCALAPPDATA "Programs\Ollama"
$ollamaUserPath = Join-Path $env:USERPROFILE "AppData\Local\Programs\Ollama"

foreach ($candidate in @($nodePath, $cargoPath, $ollamaPath, $ollamaUserPath)) {
  if ((Test-Path $candidate) -and (($env:Path -split ';') -notcontains $candidate)) {
    $env:Path = "$candidate;$env:Path"
  }
}

if (-not $env:NODE_OPTIONS) {
  $env:NODE_OPTIONS = "--use-system-ca"
} elseif ($env:NODE_OPTIONS -notlike "*--use-system-ca*") {
  $env:NODE_OPTIONS = "--use-system-ca $env:NODE_OPTIONS"
}

if (-not $env:CARGO_HTTP_CHECK_REVOKE) {
  $env:CARGO_HTTP_CHECK_REVOKE = "false"
}
