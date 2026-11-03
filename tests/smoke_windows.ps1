$ErrorActionPreference = 'Stop'

# Reproduce updating while an older release remains open at the default port.
# Do not override MDZ_TRACKER_PORT: the executable must discover a fresh port.
Remove-Item Env:MDZ_TRACKER_PORT -ErrorAction SilentlyContinue
$env:MDZ_TRACKER_CONFIG = Join-Path $env:RUNNER_TEMP 'mdz-windows-config.json'
$oldStdout = Join-Path $env:RUNNER_TEMP 'mdz-old-server.stdout.txt'
$oldStderr = Join-Path $env:RUNNER_TEMP 'mdz-old-server.stderr.txt'
$newStdout = Join-Path $env:RUNNER_TEMP 'mdz-new-server.stdout.txt'
$newStderr = Join-Path $env:RUNNER_TEMP 'mdz-new-server.stderr.txt'
$fixture = (Resolve-Path 'tests/old_server_fixture.py').Path
$executable = (Resolve-Path 'dist/MDZ-SkyScan/MDZ-SkyScan.exe').Path
$python = (Get-Command python).Source
$oldProcess = $null
$newProcess = $null

try {
    $oldProcess = Start-Process -FilePath $python -ArgumentList @('-u', ('"' + $fixture + '"')) `
        -PassThru -RedirectStandardOutput $oldStdout -RedirectStandardError $oldStderr
    $oldReady = $false
    for ($i = 0; $i -lt 40; $i++) {
        $oldProcess.Refresh()
        if ($oldProcess.HasExited) {
            throw "Legacy fixture exited: $(Get-Content $oldStderr -Raw -ErrorAction SilentlyContinue)"
        }
        try {
            $response = Invoke-WebRequest 'http://127.0.0.1:8765/health' -TimeoutSec 1
            if ($response.Headers['X-MDZ-Old-Fixture'] -eq '1') {
                $oldHealth = $response.Content | ConvertFrom-Json
                if ($oldHealth.ok -and @($oldHealth.PSObject.Properties).Count -eq 1) {
                    $oldReady = $true
                    break
                }
            }
        } catch { }
        Start-Sleep -Milliseconds 250
    }
    if (-not $oldReady) { throw 'Legacy fixture did not bind the default port' }

    $newProcess = Start-Process -FilePath $executable -PassThru `
        -RedirectStandardOutput $newStdout -RedirectStandardError $newStderr
    $serverUrl = $null
    $health = $null
    for ($i = 0; $i -lt 120; $i++) {
        $newProcess.Refresh()
        if ($newProcess.HasExited) {
            throw "New executable exited instead of starting its own release: $(Get-Content $newStderr -Raw -ErrorAction SilentlyContinue)"
        }
        if (Test-Path $newStdout) {
            $log = Get-Content $newStdout -Raw
            if ($log -match 'running at (http://127\.0\.0\.1:\d+)') {
                $candidateUrl = $Matches[1]
                if (([uri]$candidateUrl).Port -eq 8765) {
                    throw 'New executable opened the old server port'
                }
                try {
                    $health = Invoke-RestMethod ($candidateUrl + '/health') -TimeoutSec 1
                    $serverUrl = $candidateUrl
                    break
                } catch { }
            }
        }
        Start-Sleep -Milliseconds 500
    }
    if (-not $serverUrl) { throw 'Packaged server did not report a working fresh-port URL' }
    if (-not $health.ok -or $health.app -ne 'mdz-skyscan' -or $health.version -ne '1.0.5' `
        -or $health.build -notmatch '^[0-9a-f]{64}$') {
        throw "Unexpected packaged release identity: $($health | ConvertTo-Json -Compress)"
    }

    $expectedJson = & $python -c 'import app,json; print(json.dumps(app.health_payload()))'
    if ($LASTEXITCODE -ne 0) { throw 'Could not calculate the expected bundled frontend identity' }
    $expected = $expectedJson | ConvertFrom-Json
    if ($health.build -ne $expected.build) { throw 'Packaged assets differ from the release source' }

    $page = Invoke-WebRequest ($serverUrl + '/')
    if (-not $page.Content.Contains('aircraftSilhouette')) { throw 'Missing silhouette markup in the packaged app' }
    $font = Invoke-WebRequest ($serverUrl + '/Silkscreen-Regular.ttf')
    if ($font.StatusCode -ne 200 -or $font.RawContentLength -lt 1024) { throw 'Bundled pixel font is missing or empty' }
    if ($font.Headers['Cache-Control'] -ne 'no-store') { throw 'Font caching can retain an old release' }

    $env:MDZ_TEST_URL = $serverUrl
    $env:MDZ_BROWSER_CHANNEL = 'msedge'
    $env:NODE_PATH = Join-Path $env:RUNNER_TEMP 'mdz-browser/node_modules'
    & node tests/test_browser.cjs
    if ($LASTEXITCODE -ne 0) { throw 'Packaged Windows browser regression checks failed' }

    $oldStillRunning = Invoke-WebRequest 'http://127.0.0.1:8765/health'
    if ($oldStillRunning.Headers['X-MDZ-Old-Fixture'] -ne '1') { throw 'The old server was replaced or stopped' }
    Write-Output "PASS: Windows executable uses $serverUrl while the old release stays on 8765; silhouette and pixel font verified in Edge"
} finally {
    # Stop only the two processes this test explicitly started.
    foreach ($process in @($newProcess, $oldProcess)) {
        if ($null -ne $process) {
            Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
        }
    }
    foreach ($logFile in @($newStdout, $newStderr, $oldStderr)) {
        if (Test-Path $logFile) { Get-Content $logFile }
    }
}
