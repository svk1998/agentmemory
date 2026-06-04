#!/usr/bin/env pwsh
# Manual control for the local containerized agentmemory deployment.
#
#   .\deploy\local\agentmemory.ps1 start     # engine + worker up, wait for ready
#   .\deploy\local\agentmemory.ps1 stop      # both down
#   .\deploy\local\agentmemory.ps1 restart   # down then up
#   .\deploy\local\agentmemory.ps1 status    # container + livez status
#   .\deploy\local\agentmemory.ps1 logs      # follow worker logs
#   .\deploy\local\agentmemory.ps1 rebuild   # rebuild worker image after code changes
#
# The containers also carry restart: unless-stopped, so they come back on
# their own when Docker Desktop starts. This script is for explicit control.
param([Parameter(Position = 0)][string]$Cmd = "status")

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$Engine = Join-Path $RepoRoot "docker-compose.yml"
$Worker = Join-Path $RepoRoot "deploy/local/docker-compose.yml"
$Livez = "http://localhost:3111/agentmemory/livez"

function Wait-Ready {
  Write-Host "Waiting for REST API at $Livez ..."
  for ($i = 0; $i -lt 30; $i++) {
    try {
      if ((Invoke-WebRequest -UseBasicParsing $Livez -TimeoutSec 5).StatusCode -eq 200) {
        Write-Host "agentmemory is up -> http://localhost:3111  (MCP: /agentmemory/mcp)"
        return
      }
    } catch {}
    Start-Sleep -Seconds 2
  }
  Write-Host "REST API not ready within 60s. Check: .\deploy\local\agentmemory.ps1 logs"
}

function Start-Stack {
  docker compose -f $Engine up -d
  docker compose -f $Worker up -d
  Wait-Ready
}

function Stop-Stack {
  docker compose -f $Worker down
  docker compose -f $Engine down
  Write-Host "agentmemory stopped."
}

function Show-Status {
  docker ps --filter "name=agentmemory" --filter "name=iii-engine" --format "{{.Names}}: {{.Status}}"
  try {
    $r = Invoke-WebRequest -UseBasicParsing $Livez -TimeoutSec 5
    Write-Host "livez: $($r.StatusCode) OK"
  } catch {
    Write-Host "livez: DOWN"
  }
}

switch ($Cmd.ToLower()) {
  "start"   { Start-Stack }
  "stop"    { Stop-Stack }
  "restart" { Stop-Stack; Start-Stack }
  "status"  { Show-Status }
  "logs"    { docker compose -f $Worker logs -f }
  "rebuild" { docker compose -f $Worker up -d --build; Wait-Ready }
  default   { Write-Host "Usage: agentmemory.ps1 <start|stop|restart|status|logs|rebuild>" }
}
