$ErrorActionPreference = 'Stop'

# The actual windowed executable must own a private backend, even when an old
# browser-based release is still running on the original default port.
Remove-Item Env:MDZ_TRACKER_PORT -ErrorAction SilentlyContinue
$env:MDZ_TRACKER_CONFIG = Join-Path $env:RUNNER_TEMP 'mdz-native-config.json'
$env:MDZ_DESKTOP_STATE_FILE = Join-Path $env:RUNNER_TEMP 'mdz-native-state.json'
Remove-Item $env:MDZ_DESKTOP_STATE_FILE -ErrorAction SilentlyContinue
$oldStdout = Join-Path $env:RUNNER_TEMP 'mdz-old-server.stdout.txt'
$oldStderr = Join-Path $env:RUNNER_TEMP 'mdz-old-server.stderr.txt'
$newStdout = Join-Path $env:RUNNER_TEMP 'mdz-native.stdout.txt'
$newStderr = Join-Path $env:RUNNER_TEMP 'mdz-native.stderr.txt'
$fixture = (Resolve-Path 'tests/old_server_fixture.py').Path
$executable = (Resolve-Path 'dist/MDZ-SkyScan/MDZ-SkyScan.exe').Path
$python = (Get-Command python).Source
$oldProcess = $null
$newProcess = $null
$phase = 'starting the legacy fixture'

# WebView2 exposes CDP only for this CI process. The app normally has no remote
# debugging enabled, and this test never launches a separate Edge browser.
$portProbe = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, 0)
$portProbe.Start()
$debugPort = $portProbe.LocalEndpoint.Port
$portProbe.Stop()
$env:WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS = "--remote-debugging-port=$debugPort --remote-debugging-address=127.0.0.1"
$env:MDZ_NATIVE_TEST_PORT = [string]$debugPort
$env:MDZ_NATIVE_CDP_URL = "http://127.0.0.1:$debugPort"

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

    $phase = 'starting the packaged native app'
    $newProcess = Start-Process -FilePath $executable -PassThru `
        -RedirectStandardOutput $newStdout -RedirectStandardError $newStderr
    $state = $null
    $windowReady = $false
    for ($i = 0; $i -lt 120; $i++) {
        $newProcess.Refresh()
        if ($newProcess.HasExited) {
            throw "Native executable exited before its window opened: $(Get-Content $newStderr -Raw -ErrorAction SilentlyContinue)"
        }
        if (Test-Path $env:MDZ_DESKTOP_STATE_FILE) {
            try { $state = Get-Content $env:MDZ_DESKTOP_STATE_FILE -Raw | ConvertFrom-Json } catch { $state = $null }
        }
        if ($state -and $state.error) { throw "Native app startup failed: $($state.error)" }
        if ($state -and $newProcess.MainWindowHandle -ne [IntPtr]::Zero `
            -and $newProcess.MainWindowTitle -eq 'MDZ SkyScan') {
            $windowReady = $true
            break
        }
        Start-Sleep -Milliseconds 500
    }
    if (-not $windowReady) { throw 'Packaged app did not create its own MDZ SkyScan native window' }
    if ($state.pid -ne $newProcess.Id -or $state.renderer -ne 'edgechromium' `
        -or $state.window_title -ne 'MDZ SkyScan') {
        throw "Unexpected native window state: $($state | ConvertTo-Json -Compress)"
    }
    $serverUrl = $state.url
    if (([uri]$serverUrl).Host -ne '127.0.0.1' -or ([uri]$serverUrl).Port -eq 8765) {
        throw "Native app did not start its private local backend: $serverUrl"
    }

    $phase = 'checking native app identity and bundled assets'
    $health = Invoke-RestMethod ($serverUrl + '/health') -TimeoutSec 2
    $expectedJson = & $python -c 'import app,json; print(json.dumps(app.health_payload()))'
    if ($LASTEXITCODE -ne 0) { throw 'Could not calculate the expected bundled frontend identity' }
    $expected = $expectedJson | ConvertFrom-Json
    if (-not $health.ok -or $health.app -ne 'mdz-skyscan' -or $health.version -ne $expected.version `
        -or $health.build -ne $expected.build -or $state.version -ne $expected.version `
        -or $state.build -ne $expected.build) {
        throw "Unexpected native release identity: $($health | ConvertTo-Json -Compress)"
    }
    $font = Invoke-WebRequest ($serverUrl + '/Silkscreen-Regular.ttf')
    if ($font.StatusCode -ne 200 -or $font.RawContentLength -lt 1024) { throw 'Bundled pixel font is missing or empty' }
    if ($font.Headers['Cache-Control'] -ne 'no-store') { throw 'Font caching can retain an old release' }

    $phase = 'testing the embedded WebView2 page'
    $env:MDZ_TEST_URL = $serverUrl
    $env:MDZ_TEST_VERSION = $expected.version
    $env:NODE_PATH = Join-Path $env:RUNNER_TEMP 'mdz-browser/node_modules'
    & node tests/test_native_window.cjs
    if ($LASTEXITCODE -ne 0) { throw 'Embedded native-window UI checks failed' }

    $phase = 'closing the native window and checking backend shutdown'
    $newProcess.Refresh()
    if ($newProcess.MainWindowHandle -eq [IntPtr]::Zero -or -not $newProcess.CloseMainWindow()) {
        throw 'Could not close the actual native app window'
    }
    if (-not $newProcess.WaitForExit(20000)) { throw 'Closing the native window did not exit the app process' }
    if ($newProcess.ExitCode -ne 0) { throw "Native app exited with $($newProcess.ExitCode) after closing its window" }
    $probe = [System.Net.Sockets.TcpClient]::new()
    $backendAlive = $false
    try {
        $connected = $probe.ConnectAsync('127.0.0.1', ([uri]$serverUrl).Port)
        if ($connected.Wait(1000) -and $probe.Connected) { $backendAlive = $true }
    } catch { } finally { $probe.Dispose() }
    if ($backendAlive) { throw 'The app backend kept running after its native window closed' }

    $oldStillRunning = Invoke-WebRequest 'http://127.0.0.1:8765/health'
    if ($oldStillRunning.Headers['X-MDZ-Old-Fixture'] -ne '1') { throw 'The old server was replaced or stopped' }
    Write-Output 'PASS: native Windows app window, embedded WebView2 silhouette/font/radar, private backend, and clean window-close lifecycle'
} catch {
    $details = "Windows native smoke test failed while $phase`: $($_.Exception.Message)"
    $annotation = $details.Replace('%', '%25').Replace("`r", '%0D').Replace("`n", '%0A')
    Write-Output "::error::$annotation"
    if ($env:GITHUB_STEP_SUMMARY) {
        @("### Windows native app diagnostics", '', '```text', $details, '```') | Add-Content $env:GITHUB_STEP_SUMMARY
    }
    throw
} finally {
    # Stop only processes that this test explicitly started. Successful GUI
    # shutdown was tested above before this cleanup can force-stop anything.
    foreach ($process in @($newProcess, $oldProcess)) {
        if ($null -ne $process) { Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue }
    }
    foreach ($logFile in @($newStdout, $newStderr, $oldStderr, $env:MDZ_DESKTOP_STATE_FILE)) {
        if (Test-Path $logFile) { Get-Content $logFile }
    }
}
