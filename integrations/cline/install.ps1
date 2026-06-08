#Requires -Version 5.1
param(
  [string]$Project = "",
  [switch]$Uninstall
)
$ErrorActionPreference = "Stop"

# Repo root = two levels up from this script (integrations/cline/).
$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$ScriptsSrc = Join-Path $RepoRoot "plugin\cline\scripts"

if ($Project) {
  $HooksDir = Join-Path (Resolve-Path $Project) ".clinerules\hooks"
} else {
  $HooksDir = Join-Path $env:USERPROFILE "Documents\Cline\Rules\Hooks"
}
$AgentDir = Join-Path $HooksDir ".agentmemory"

# Hook type -> compiled script. Keep in sync with src/cli/connect/cline-hooks.ts.
$Hooks = [ordered]@{
  "TaskStart"        = "task-start.mjs"
  "TaskResume"       = "task-resume.mjs"
  "TaskCancel"       = "task-cancel.mjs"
  "TaskComplete"     = "task-complete.mjs"
  "PreToolUse"       = "pre-tool-use.mjs"
  "PostToolUse"      = "post-tool-use.mjs"
  "UserPromptSubmit" = "prompt-submit.mjs"
  "PreCompact"       = "pre-compact.mjs"
}

if ($Uninstall) {
  foreach ($name in $Hooks.Keys) {
    Remove-Item (Join-Path $HooksDir "$name.ps1") -Force -ErrorAction SilentlyContinue
  }
  Remove-Item $AgentDir -Recurse -Force -ErrorAction SilentlyContinue
  Write-Host "Uninstalled agentmemory Cline hooks from $HooksDir"
  exit 0
}

if (-not (Test-Path $ScriptsSrc)) { throw "Compiled scripts not found at $ScriptsSrc. Run 'npx tsdown' first." }

New-Item -ItemType Directory -Force -Path $AgentDir | Out-Null
Copy-Item (Join-Path $ScriptsSrc "*.mjs") $AgentDir -Force

# Resolve URL + secret: env first, then ~/.agentmemory/.env
$Url = if ($env:AGENTMEMORY_URL) { $env:AGENTMEMORY_URL } else { "http://localhost:3111" }
$Secret = $env:AGENTMEMORY_SECRET
$DotEnv = Join-Path $env:USERPROFILE ".agentmemory\.env"
if (-not $Secret -and (Test-Path $DotEnv)) {
  $line = Select-String -Path $DotEnv -Pattern '^\s*AGENTMEMORY_SECRET\s*=' | Select-Object -First 1
  if ($line) { $Secret = ($line.Line -replace '^\s*AGENTMEMORY_SECRET\s*=\s*', '').Trim('"').Trim("'") }
}
$SecretVal = if ($Secret) { $Secret } else { "" }
$Config = @{ url = $Url; secret = $SecretVal } | ConvertTo-Json -Compress
Set-Content -Path (Join-Path $AgentDir "config.json") -Value $Config -Encoding utf8 -NoNewline

foreach ($name in $Hooks.Keys) {
  $script = $Hooks[$name]
  $shim = "`$ErrorActionPreference = 'SilentlyContinue'`r`n`$stdin = [Console]::In.ReadToEnd()`r`n`$stdin | node `"`$PSScriptRoot\.agentmemory\$script`""
  Set-Content -Path (Join-Path $HooksDir "$name.ps1") -Value $shim -Encoding utf8
}

Write-Host "Installed agentmemory Cline hooks to $HooksDir"
Write-Host "Auth: $(if ($Secret) { 'Bearer secret configured' } else { 'no secret (open local deployment)' })"
