param([int]$Port = 8000, [switch]$Demo, [switch]$Build)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$projectPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (!(Test-Path -LiteralPath $projectPython)) {
    python -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Failed to create the Python environment.' }
}
& $projectPython -c 'import fastapi, uvicorn, dotenv, httpx'
if ($LASTEXITCODE -ne 0) {
    & $projectPython -m pip install -r requirements.lock.txt
    if ($LASTEXITCODE -ne 0) { throw 'Failed to install Python dependencies.' }
}
if ($Build -or !(Test-Path -LiteralPath 'frontend\dist\index.html')) {
    Push-Location frontend
    try {
        npm.cmd ci --no-audit --no-fund
        if ($LASTEXITCODE -ne 0) { throw 'Failed to install frontend dependencies.' }
        npm.cmd run build
        if ($LASTEXITCODE -ne 0) { throw 'Failed to build the frontend.' }
    } finally { Pop-Location }
}
$priorAgentMode = $env:AGENT_MODE
$priorDatabasePath = $env:DATABASE_PATH
try {
    if ($Demo) {
        $env:AGENT_MODE = 'mock'
        $env:DATABASE_PATH = Join-Path $PSScriptRoot 'data\demo.db'
        & $projectPython -X utf8 -m scripts.seed_demo --db $env:DATABASE_PATH
        if ($LASTEXITCODE -ne 0) { throw 'Failed to initialize demo data.' }
        Write-Host 'Mock demo mode: fixed development examples, not formal evaluation results.'
    }
    Write-Host "Open http://127.0.0.1:$Port"
    & $projectPython -X utf8 -m uvicorn backend.main:app --host 127.0.0.1 --port $Port
} finally {
    [Environment]::SetEnvironmentVariable('AGENT_MODE', $priorAgentMode, 'Process')
    [Environment]::SetEnvironmentVariable('DATABASE_PATH', $priorDatabasePath, 'Process')
}

