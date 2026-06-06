. (Join-Path $PSScriptRoot "env.ps1")

$commands = @("python", "git", "node", "npm", "cargo", "rustc", "ollama")

foreach ($command in $commands) {
  $found = Get-Command $command -ErrorAction SilentlyContinue
  if ($found) {
    Write-Host "${command}: $($found.Source)"
  } else {
    Write-Host "${command}: missing"
  }
}
