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
$blockedState = Join-Path $env:RUNNER_TEMP 'mdz-blocked-state.json'
$blockedStdout = Join-Path $env:RUNNER_TEMP 'mdz-blocked.stdout.txt'
$blockedStderr = Join-Path $env:RUNNER_TEMP 'mdz-blocked.stderr.txt'
$fixture = (Resolve-Path 'tests/old_server_fixture.py').Path
$stagedExecutable = (Resolve-Path 'dist/MDZ-SkyScan/MDZ-SkyScan.exe').Path
$downloadFolder = Join-Path $env:RUNNER_TEMP 'MDZ SkyScan download (4)'
New-Item -ItemType Directory -Path $downloadFolder -Force | Out-Null
Copy-Item -LiteralPath $stagedExecutable -Destination $downloadFolder
$executable = Join-Path $downloadFolder 'MDZ-SkyScan.exe'
$python = (Get-Command python).Source
$oldProcess = $null
$newProcess = $null
$windowProcess = $null
$blockedProcess = $null
$phase = 'reproducing the old downloaded DLL failure'

function Set-InternetZone([string] $path) {
    # Simulate the provenance attached by a browser download. Do not unblock
    # files or change machine/.NET security settings anywhere in this test.
    Set-Content -LiteralPath $path -Stream Zone.Identifier -Value "[ZoneTransfer]`r`nZoneId=3" -Encoding ascii
    if ((Get-Content -LiteralPath $path -Stream Zone.Identifier -Raw) -notmatch 'ZoneId=3') {
        throw "Could not mark the download as Internet Zone: $path"
    }
}

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
    # Use the published failing package and require the exact error shown in
    # the user's screenshot, independently of the new app's error handling.
    $baselineArchive = Join-Path $env:RUNNER_TEMP 'mdz-v1.0.7-windows.zip'
    $baselineFolder = Join-Path $env:RUNNER_TEMP 'MDZ SkyScan old download (4)'
    Invoke-WebRequest -Uri 'https://github.com/MDZ-code-dev/MDZ-flight-tracker/releases/download/v1.0.7/MDZ-SkyScan-windows.zip' -OutFile $baselineArchive
    if ((Get-FileHash -LiteralPath $baselineArchive -Algorithm SHA256).Hash -ne '5cda9344dc27ec1dc5634a7588959da0c9cc039dad8562e3156da2c1ec42d603') {
        throw 'The v1.0.7 regression package does not match its pinned release checksum'
    }
    Expand-Archive -LiteralPath $baselineArchive -DestinationPath $baselineFolder -Force
    $baselineExecutable = Join-Path $baselineFolder 'MDZ-SkyScan/MDZ-SkyScan.exe'
    $baselineDll = Join-Path $baselineFolder 'MDZ-SkyScan/_internal/pythonnet/runtime/Python.Runtime.dll'
    if (-not (Test-Path -LiteralPath $baselineDll)) { throw 'The v1.0.7 regression package is missing Python.Runtime.dll' }
    $baselineDll = (Resolve-Path -LiteralPath $baselineDll).Path
    Set-InternetZone $baselineDll
    Remove-Item -LiteralPath $blockedState -ErrorAction SilentlyContinue
    $nativeState = $env:MDZ_DESKTOP_STATE_FILE
    $nativeConfig = $env:MDZ_TRACKER_CONFIG
    try {
        $env:MDZ_DESKTOP_STATE_FILE = $blockedState
        $env:MDZ_TRACKER_CONFIG = Join-Path $env:RUNNER_TEMP 'mdz-blocked-config.json'
        $blockedProcess = Start-Process -FilePath $baselineExecutable -PassThru `
            -RedirectStandardOutput $blockedStdout -RedirectStandardError $blockedStderr
        $failure = $null
        for ($i = 0; $i -lt 120; $i++) {
            if (Test-Path -LiteralPath $blockedState) {
                try { $failure = Get-Content -LiteralPath $blockedState -Raw | ConvertFrom-Json } catch { $failure = $null }
            }
            if ($failure -and $failure.error) { break }
            $blockedProcess.Refresh()
            if ($blockedProcess.HasExited) { throw 'The old package exited without reporting the expected blocked-assembly failure' }
            Start-Sleep -Milliseconds 250
        }
        if (-not $failure -or $failure.error -ne "Failed to resolve Python.Runtime.Loader.Initialize from $baselineDll") {
            throw "The old package did not reproduce the reported CLR failure: $($failure | ConvertTo-Json -Compress)"
        }
        if ($failure.pid -ne $blockedProcess.Id) { throw 'The old package reported an unexpected process ID' }
        Write-Output 'PASS: Internet-marked v1.0.7 Python.Runtime.dll reproduces the reported CLR assembly failure'
    } finally {
        $env:MDZ_DESKTOP_STATE_FILE = $nativeState
        $env:MDZ_TRACKER_CONFIG = $nativeConfig
        if ($null -ne $blockedProcess) { Stop-Process -Id $blockedProcess.Id -Force -ErrorAction SilentlyContinue }
    }

    $phase = 'starting the legacy fixture'
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

    $phase = 'starting the Internet-marked self-contained app'
    if (Test-Path 'dist/MDZ-SkyScan/_internal') { throw 'The Windows download still depends on an external _internal directory' }
    if (Get-ChildItem -LiteralPath $downloadFolder -File -Filter '*.dll') { throw 'The native executable test directory must not contain external DLLs' }
    Set-InternetZone $executable
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
        if ($state -and $state.pid) {
            # PyInstaller onefile owns a launcher process and a Python child.
            # Check ownership before touching any PID supplied by diagnostics.
            $child = Get-CimInstance Win32_Process -Filter "ProcessId = $($state.pid)"
            if ($child -and $child.ExecutablePath -eq $executable `
                -and ($child.ProcessId -eq $newProcess.Id -or $child.ParentProcessId -eq $newProcess.Id)) {
                $windowProcess = Get-Process -Id $state.pid -ErrorAction SilentlyContinue
                if ($windowProcess -and -not $state.error -and $windowProcess.MainWindowHandle -ne [IntPtr]::Zero `
                    -and $windowProcess.MainWindowTitle -eq 'MDZ SkyScan') {
                    $windowReady = $true
                    break
                }
            }
        }
        if ($state -and $state.error) { throw "Native app startup failed: $($state.error)" }
        Start-Sleep -Milliseconds 500
    }
    if (-not $windowReady) { throw 'Packaged app did not create its own MDZ SkyScan native window' }
    if ($state.pid -ne $windowProcess.Id -or $state.renderer -ne 'edgechromium' `
        -or $state.window_title -ne 'MDZ SkyScan') {
        throw "Unexpected native window state: $($state | ConvertTo-Json -Compress)"
    }
    $serverUrl = $state.url
    if (([uri]$serverUrl).Host -ne '127.0.0.1' -or ([uri]$serverUrl).Port -eq 8765) {
        throw "Native app did not start its private local backend: $serverUrl"
    }

    $phase = 'checking private extraction and unblocked bundled runtime files'
    if (-not $state.bundle_dir) { throw 'The native app did not report its bundled runtime directory' }
    $bundleDirectory = [System.IO.Path]::GetFullPath($state.bundle_dir).TrimEnd('\')
    $tempDirectory = [System.IO.Path]::GetFullPath($env:TEMP).TrimEnd('\') + '\'
    if (-not $bundleDirectory.StartsWith($tempDirectory, [System.StringComparison]::OrdinalIgnoreCase) `
        -or (Split-Path $bundleDirectory -Leaf) -notlike '_MEI*') {
        throw "The onefile app did not extract into its private temporary directory: $bundleDirectory"
    }
    foreach ($required in @('Microsoft.Web.WebView2.Core.dll', 'Microsoft.Web.WebView2.WinForms.dll', 'WebView2Loader.dll', 'Python.Runtime.dll')) {
        $libraries = @(Get-ChildItem -LiteralPath $bundleDirectory -Recurse -File -Filter $required)
        if ($libraries.Count -eq 0) { throw "The self-contained executable is missing $required" }
        foreach ($library in $libraries) {
            if (Get-Item -LiteralPath $library.FullName -Stream Zone.Identifier -ErrorAction SilentlyContinue) {
                throw "An extracted bundled runtime still has an Internet Zone stream: $($library.FullName)"
            }
        }
    }
    if ((Get-Content -LiteralPath $executable -Stream Zone.Identifier -Raw) -notmatch 'ZoneId=3') {
        throw 'The test executable lost its original Internet Zone provenance'
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
    $windowProcess.Refresh()
    if ($windowProcess.MainWindowHandle -eq [IntPtr]::Zero -or -not $windowProcess.CloseMainWindow()) {
        throw 'Could not close the actual native app window'
    }
    if (-not $windowProcess.WaitForExit(20000)) { throw 'Closing the native window did not exit its Python child process' }
    if (-not $newProcess.WaitForExit(20000)) { throw 'Closing the native window did not exit the app process' }
    if ($newProcess.ExitCode -ne 0) { throw "Native app exited with $($newProcess.ExitCode) after closing its window" }
    # Antivirus/file indexing can briefly retain extracted DLL handles after
    # the GUI exits; allow the launcher cleanup to settle before asserting.
    for ($i = 0; $i -lt 40 -and (Test-Path -LiteralPath $bundleDirectory); $i++) {
        Start-Sleep -Milliseconds 250
    }
    if (Test-Path -LiteralPath $bundleDirectory) { throw 'The native launcher did not remove its temporary runtime directory' }
    $probe = [System.Net.Sockets.TcpClient]::new()
    $backendAlive = $false
    try {
        $connected = $probe.ConnectAsync('127.0.0.1', ([uri]$serverUrl).Port)
        if ($connected.Wait(1000) -and $probe.Connected) { $backendAlive = $true }
    } catch { } finally { $probe.Dispose() }
    if ($backendAlive) { throw 'The app backend kept running after its native window closed' }

    $oldStillRunning = Invoke-WebRequest 'http://127.0.0.1:8765/health'
    if ($oldStillRunning.Headers['X-MDZ-Old-Fixture'] -ne '1') { throw 'The old server was replaced or stopped' }
    Write-Output 'PASS: Internet-marked onefile app, private runtime extraction, native WebView2 silhouette/font/radar, private backend, and clean window-close lifecycle'
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
    foreach ($process in @($windowProcess, $newProcess, $oldProcess, $blockedProcess)) {
        if ($null -ne $process) { Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue }
    }
    foreach ($logFile in @($newStdout, $newStderr, $oldStderr, $blockedStderr, $blockedState, $env:MDZ_DESKTOP_STATE_FILE)) {
        if (Test-Path $logFile) { Get-Content $logFile }
    }
}
