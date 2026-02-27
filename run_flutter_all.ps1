$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $MyInvocation.MyCommand.Path

function Test-PortListening {
    param([int]$Port)

    try {
        $null = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction Stop
        return $true
    } catch {
        return $false
    }
}

function Start-ServiceTerminal {
    param(
        [string]$WorkingDir,
        [string]$Command,
        [string]$Title
    )

    Start-Process powershell -ArgumentList @(
        '-NoExit',
        '-ExecutionPolicy', 'Bypass',
        '-Command',
        "`$Host.UI.RawUI.WindowTitle = '$Title'; Set-Location '$WorkingDir'; $Command"
    ) | Out-Null
}

$ttsDir = Join-Path $root 'tts_server'
$mlDir = Join-Path $root 'ml'
$flutterDir = Join-Path $root 'flutter_app'

if (-not (Test-PortListening -Port 3000)) {
    Write-Host 'Starting tts_server on :3000 ...' -ForegroundColor Cyan
    Start-ServiceTerminal -WorkingDir $ttsDir -Command 'npm start' -Title 'kitahack - tts_server'
} else {
    Write-Host 'tts_server already running on :3000' -ForegroundColor Green
}

if (-not (Test-PortListening -Port 5000)) {
    Write-Host 'Starting live_predict server on :5000 ...' -ForegroundColor Cyan
    Start-ServiceTerminal -WorkingDir $mlDir -Command 'python src/predict/live_predict.py --server --host 0.0.0.0 --port 5000' -Title 'kitahack - live_predict'
} else {
    Write-Host 'live_predict already running on :5000' -ForegroundColor Green
}

Write-Host 'Waiting for services...' -ForegroundColor DarkGray
Start-Sleep -Seconds 3

Set-Location $flutterDir
flutter run -d chrome
