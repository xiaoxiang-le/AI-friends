$ErrorActionPreference = 'Stop'
$projectRoot = $PSScriptRoot
$pythonPath = Join-Path $projectRoot '.venv\Scripts\python.exe'
$backendPath = Join-Path $projectRoot 'backend'
$frontendPath = Join-Path $projectRoot 'frontend'
$logPath = Join-Path $projectRoot '.local'
New-Item -ItemType Directory -Force -Path $logPath | Out-Null
if (!(Test-Path $pythonPath)) { throw 'Missing .venv. Install Python dependencies first.' }
foreach ($port in @(8000, 5173)) {
    if (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue) {
        throw "Port $port is already in use."
    }
}
Push-Location $backendPath
try {
    & $pythonPath manage.py migrate --noinput
    if ($LASTEXITCODE -ne 0) { throw 'Database migration failed.' }
} finally { Pop-Location }
$backendProcess = Start-Process -FilePath $pythonPath -ArgumentList 'manage.py runserver 127.0.0.1:8000 --noreload' -WorkingDirectory $backendPath -WindowStyle Hidden -RedirectStandardOutput (Join-Path $logPath 'backend.log') -RedirectStandardError (Join-Path $logPath 'backend-error.log') -PassThru
$nodePath = (Get-Command node.exe).Source
& $nodePath (Join-Path $projectRoot 'scripts/prepare-vad-assets.js')
if ($LASTEXITCODE -ne 0) { throw 'VAD asset preparation failed.' }
$frontendProcess = Start-Process -FilePath $nodePath -ArgumentList 'node_modules/vite/bin/vite.js --host 127.0.0.1 --port 5173 --strictPort' -WorkingDirectory $frontendPath -WindowStyle Hidden -RedirectStandardOutput (Join-Path $logPath 'frontend.log') -RedirectStandardError (Join-Path $logPath 'frontend-error.log') -PassThru
$jobsProcess = Start-Process -FilePath $pythonPath -ArgumentList 'manage.py run_jobs' -WorkingDirectory $backendPath -WindowStyle Hidden -RedirectStandardOutput (Join-Path $logPath 'jobs.log') -RedirectStandardError (Join-Path $logPath 'jobs-error.log') -PassThru
@{ jobs = $jobsProcess.Id; backend = $backendProcess.Id; frontend = $frontendProcess.Id } | ConvertTo-Json | Set-Content (Join-Path $logPath 'pids.json')
Write-Host 'Frontend: http://127.0.0.1:5173'
Write-Host 'Backend:  http://127.0.0.1:8000'
Write-Host "Logs: $logPath"
