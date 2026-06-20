param(
    [string]$DatabaseUrl = $env:DATABASE_URL,
    [string]$CollectionDate = "",
    [string]$SourcePath = "",
    [int]$MaxRecords = 2000,
    [int]$MinRecords = 1,
    [int]$MinCleanRecords = 1000,
    [int]$MaxUrls = 50,
    [double]$DelaySeconds = 2,
    [string]$CaptureRuntime = $env:REALTYSCOPE_CAPTURE_RUNTIME,
    [string]$ChromeBinary = $env:REALTYSCOPE_CHROME_BINARY,
    [string]$ChromePath = $env:REALTYSCOPE_CHROME_PATH,
    [string]$ChromeUserDataDir = $env:REALTYSCOPE_CHROME_USER_DATA_DIR,
    [string]$ChromeProfileDirectory = $env:REALTYSCOPE_CHROME_PROFILE_DIRECTORY,
    [string]$ChromeRemoteDebuggingPort = $env:REALTYSCOPE_CHROME_REMOTE_DEBUGGING_PORT,
    [int]$CaptureOffsetStart = 0,
    [int]$CaptureOffsetStop = 1980,
    [int]$CaptureOffsetStep = 20,
    [int]$CaptureMaxPages = 100,
    [double]$CaptureDelaySeconds = 3,
    [double]$CaptureTimeoutSeconds = 90,
    [int]$CaptureVirtualTimeBudgetMs = 10000,
    [int]$CapturePageRetries = 2,
    [double]$CaptureRetryDelaySeconds = 5,
    [string]$CaptureDiagnosticsDir = $env:REALTYSCOPE_CAPTURE_DIAGNOSTICS_DIR,
    [switch]$SkipCapture,
    [switch]$SkipDockerStart,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

function ConvertTo-WslPath {
    param([string]$WindowsPath)

    $FullPath = (Resolve-Path $WindowsPath).Path
    if ($FullPath -notmatch "^([A-Za-z]):\\(.*)$") {
        throw "Cannot convert path to WSL format: $FullPath"
    }

    $Drive = $Matches[1].ToLowerInvariant()
    $Tail = $Matches[2] -replace "\\", "/"
    return "/mnt/$Drive/$Tail"
}

function Invoke-DomclickNativeCommand {
    param(
        [string]$FilePath,
        [string[]]$Arguments
    )

    $PreviousErrorActionPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = "Continue"
        $Output = @(& $FilePath @Arguments 2>&1 | ForEach-Object { "$_" })
        $ExitCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $PreviousErrorActionPreference
    }

    if ($Output.Count -gt 0) {
        $Output | ForEach-Object { Write-Host $_ }
    }

    return $ExitCode
}

function Get-DomclickSnapshotPayloadFiles {
    param([string]$SnapshotDir)

    if (-not (Test-Path $SnapshotDir -PathType Container)) {
        return @()
    }

    return @(
        Get-ChildItem -LiteralPath $SnapshotDir -Recurse -File -ErrorAction SilentlyContinue |
            Where-Object {
                $_.Name.ToLowerInvariant() -ne "manifest.json" -and
                @( ".json", ".html", ".htm" ) -contains $_.Extension.ToLowerInvariant()
            }
    )
}

function Get-DomclickPartialSnapshotObservedAt {
    param([object[]]$PayloadFiles)

    $EarliestPayload = @($PayloadFiles) | Sort-Object LastWriteTimeUtc | Select-Object -First 1
    if ($null -eq $EarliestPayload) {
        return ""
    }
    return $EarliestPayload.LastWriteTimeUtc.ToString("o", [System.Globalization.CultureInfo]::InvariantCulture)
}

function Move-DomclickPartialSnapshot {
    param([string]$SnapshotDir)

    if (-not (Test-Path $SnapshotDir -PathType Container)) {
        return ""
    }

    $Parent = Split-Path -Parent $SnapshotDir
    $Leaf = Split-Path -Leaf $SnapshotDir
    $Stamp = [datetime]::UtcNow.ToString("yyyyMMdd-HHmmss", [System.Globalization.CultureInfo]::InvariantCulture)
    $Candidate = Join-Path $Parent "$Leaf-partial-$Stamp"
    $Index = 1
    while (Test-Path $Candidate) {
        $Candidate = Join-Path $Parent "$Leaf-partial-$Stamp-$Index"
        $Index += 1
    }

    Move-Item -LiteralPath $SnapshotDir -Destination $Candidate
    Write-Host "Quarantined partial Domclick snapshot $SnapshotDir -> $Candidate"
    return $Candidate
}

function Resolve-DomclickExistingSnapshotArgs {
    param(
        [string]$SnapshotDir,
        [switch]$RecoverPartial
    )

    if (-not (Test-Path $SnapshotDir -PathType Container)) {
        return $null
    }

    $ManifestPath = Join-Path $SnapshotDir "manifest.json"
    if (Test-Path $ManifestPath -PathType Leaf) {
        return @("--source-path", $SnapshotDir)
    }

    $PayloadFiles = @(Get-DomclickSnapshotPayloadFiles -SnapshotDir $SnapshotDir)
    if ($PayloadFiles.Count -gt 0) {
        if (-not $RecoverPartial) {
            Move-DomclickPartialSnapshot -SnapshotDir $SnapshotDir | Out-Null
            return $null
        }
        $ObservedAt = Get-DomclickPartialSnapshotObservedAt -PayloadFiles $PayloadFiles
        $script:DomclickAllowMissingManifest = $true
        $script:DomclickObservedAt = $ObservedAt
        Write-Host "Partial Domclick payloads found in $SnapshotDir without manifest.json; recovery observed_at=$ObservedAt"
        return @("--source-path", $SnapshotDir)
    }

    return $null
}

function Resolve-DomclickSourceArgs {
    param(
        [string]$RepoRoot,
        [string]$CollectionDate,
        [string]$SourcePath,
        [string]$Python,
        [switch]$DryRun
    )

    $script:DomclickAllowMissingManifest = $false
    $script:DomclickObservedAt = ""

    if (-not [string]::IsNullOrWhiteSpace($SourcePath)) {
        if (-not (Test-Path $SourcePath -PathType Container)) {
            throw "Configured source path does not exist: $SourcePath"
        }
        $ExistingSourceArgs = Resolve-DomclickExistingSnapshotArgs -SnapshotDir $SourcePath -RecoverPartial
        if ($null -ne $ExistingSourceArgs) {
            return $ExistingSourceArgs
        }
        return @("--source-path", $SourcePath)
    }

    $RawRoot = Join-Path $RepoRoot "data\raw\domclick"
    $DayDir = Join-Path $RawRoot $CollectionDate
    $BulkDir = Join-Path $RawRoot "$CollectionDate-bulk"
    $UrlFile = Join-Path $RepoRoot "data\raw\domclick-urls.txt"

    $RecoverExistingPartial = $SkipCapture -or $DryRun

    $ExistingDayArgs = Resolve-DomclickExistingSnapshotArgs `
        -SnapshotDir $DayDir `
        -RecoverPartial:$RecoverExistingPartial
    if ($null -ne $ExistingDayArgs) {
        return $ExistingDayArgs
    }
    $ExistingBulkArgs = Resolve-DomclickExistingSnapshotArgs `
        -SnapshotDir $BulkDir `
        -RecoverPartial:$RecoverExistingPartial
    if ($null -ne $ExistingBulkArgs) {
        return $ExistingBulkArgs
    }
    if (-not $SkipCapture) {
        if ([string]::IsNullOrWhiteSpace($CaptureRuntime)) {
            $CaptureRuntime = "cdp"
        }
        if ([string]::IsNullOrWhiteSpace($ChromeBinary) -and -not [string]::IsNullOrWhiteSpace($ChromePath)) {
            $ChromeBinary = $ChromePath
        }

        $CaptureArgs = @(
            "-m", "realtyscope.ingestion.domclick_chrome_capture",
            "--output-root", (Join-Path $RepoRoot "data\raw\domclick"),
            "--collection-date", $CollectionDate,
            "--capture-runtime", $CaptureRuntime,
            "--offset-start", "$CaptureOffsetStart",
            "--offset-stop", "$CaptureOffsetStop",
            "--offset-step", "$CaptureOffsetStep",
            "--max-pages", "$CaptureMaxPages",
            "--delay-seconds", "$CaptureDelaySeconds",
            "--timeout-seconds", "$CaptureTimeoutSeconds",
            "--virtual-time-budget-ms", "$CaptureVirtualTimeBudgetMs",
            "--page-retries", "$CapturePageRetries",
            "--retry-delay-seconds", "$CaptureRetryDelaySeconds",
            "--min-records", "$MinCleanRecords",
            "--operator-note", "scheduled batch fallback capture using configured Chrome automation profile",
            "--json"
        )
        if (-not [string]::IsNullOrWhiteSpace($ChromeBinary)) {
            $CaptureArgs += @("--chrome-binary", $ChromeBinary)
        }
        if (-not [string]::IsNullOrWhiteSpace($ChromeUserDataDir)) {
            $CaptureArgs += @("--chrome-user-data-dir", $ChromeUserDataDir)
        }
        if (-not [string]::IsNullOrWhiteSpace($ChromeProfileDirectory)) {
            $CaptureArgs += @("--profile-directory", $ChromeProfileDirectory)
        }
        if (-not [string]::IsNullOrWhiteSpace($ChromeRemoteDebuggingPort)) {
            $CaptureArgs += @("--remote-debugging-port", $ChromeRemoteDebuggingPort)
        }
        if (-not [string]::IsNullOrWhiteSpace($CaptureDiagnosticsDir)) {
            $CaptureArgs += @("--diagnostics-dir", $CaptureDiagnosticsDir)
        }

        if ($DryRun) {
            $script:DryRunCaptureArgs = $CaptureArgs
            return @("--source-path", $BulkDir)
        }

        Write-Host ("Capture command: " + $Python + " " + ($CaptureArgs -join " "))
        $CaptureExitCode = Invoke-DomclickNativeCommand -FilePath $Python -Arguments $CaptureArgs
        if ($CaptureExitCode -ne 0) {
            $PartialBulkArgs = Resolve-DomclickExistingSnapshotArgs -SnapshotDir $BulkDir -RecoverPartial
            if ($null -ne $PartialBulkArgs) {
                return $PartialBulkArgs
            }
            throw "Domclick Chrome capture failed with exit code $CaptureExitCode"
        }
        $CapturedBulkArgs = Resolve-DomclickExistingSnapshotArgs -SnapshotDir $BulkDir -RecoverPartial
        if ($null -ne $CapturedBulkArgs) {
            return $CapturedBulkArgs
        }
        throw "Domclick Chrome capture completed but did not create expected snapshot directory: $BulkDir"
    }
    if (Test-Path $UrlFile -PathType Leaf) {
        return @("--url-file", $UrlFile)
    }

    throw "No Domclick input found for $CollectionDate. Expected $DayDir, $BulkDir, or $UrlFile."
}

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $RepoRoot

$LogDir = Join-Path $RepoRoot "data\processed\runtime_logs"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

$RunStartedAt = [System.TimeZoneInfo]::ConvertTimeBySystemTimeZoneId(
    [datetime]::UtcNow,
    "Russian Standard Time"
)
$RunStamp = $RunStartedAt.ToString("yyyyMMdd-HHmmss")
$LogPath = Join-Path $LogDir "domclick-scheduled-task-$RunStamp.log"

Start-Transcript -Path $LogPath -Append | Out-Null
try {
    if ([string]::IsNullOrWhiteSpace($DatabaseUrl)) {
        $DatabaseUrl = "postgresql+psycopg://realtyscope:realtyscope@localhost:5432/realtyscope"
    }

    if ([string]::IsNullOrWhiteSpace($CollectionDate)) {
        $CollectionDate = $RunStartedAt.ToString("yyyy-MM-dd")
    }

    $env:PYTHONIOENCODING = "utf-8"
    $env:DATABASE_URL = $DatabaseUrl

    $Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"

    if ($DryRun) {
        $SourceArgs = Resolve-DomclickSourceArgs `
            -RepoRoot $RepoRoot `
            -CollectionDate $CollectionDate `
            -SourcePath $SourcePath `
            -Python $Python `
            -DryRun

        $BatchArgs = @(
            "-m", "realtyscope.ingestion.domclick_scheduled_batch", "run",
            "--database-url", $DatabaseUrl,
            "--commit",
            "--max-records", "$MaxRecords",
            "--min-records", "$MinRecords",
            "--min-normalized-records", "$MinCleanRecords",
            "--json"
        )
        $BatchArgs += $SourceArgs

        if ($script:DomclickAllowMissingManifest) {
            $BatchArgs += @("--allow-missing-manifest")
        }
        if (-not [string]::IsNullOrWhiteSpace($script:DomclickObservedAt)) {
            $BatchArgs += @("--observed-at", $script:DomclickObservedAt)
        }

        if ($SourceArgs[0] -eq "--url-file") {
            $BatchArgs += @(
                "--output-root", (Join-Path $RepoRoot "data\raw\domclick"),
                "--collection-date", $CollectionDate,
                "--max-urls", "$MaxUrls",
                "--delay-seconds", "$DelaySeconds"
            )
        }

        Write-Host "Dry run only; no Docker, Alembic, Chrome capture, batch ingestion, or database commit executed."
        if ($script:DryRunCaptureArgs) {
            Write-Host ("Capture command: " + $Python + " " + ($script:DryRunCaptureArgs -join " "))
        }
        Write-Host ("Batch command: " + $Python + " " + ($BatchArgs -join " "))
        return
    }

    if (-not $SkipDockerStart) {
        $WslRepoRoot = ConvertTo-WslPath $RepoRoot
        wsl -d Ubuntu -- bash -lc "cd '$WslRepoRoot' && docker compose up -d db"
        if ($LASTEXITCODE -ne 0) {
            throw "WSL Docker startup failed with exit code $LASTEXITCODE"
        }
    }

    $AlembicExitCode = Invoke-DomclickNativeCommand -FilePath $Python -Arguments @("-m", "alembic", "upgrade", "head")
    if ($AlembicExitCode -ne 0) {
        throw "Alembic upgrade failed with exit code $AlembicExitCode"
    }

    $SourceArgs = Resolve-DomclickSourceArgs `
        -RepoRoot $RepoRoot `
        -CollectionDate $CollectionDate `
        -SourcePath $SourcePath `
        -Python $Python

    $BatchArgs = @(
        "-m", "realtyscope.ingestion.domclick_scheduled_batch", "run",
        "--database-url", $DatabaseUrl,
        "--commit",
        "--max-records", "$MaxRecords",
        "--min-records", "$MinRecords",
        "--min-normalized-records", "$MinCleanRecords",
        "--json"
    )
    $BatchArgs += $SourceArgs

    if ($script:DomclickAllowMissingManifest) {
        $BatchArgs += @("--allow-missing-manifest")
    }
    if (-not [string]::IsNullOrWhiteSpace($script:DomclickObservedAt)) {
        $BatchArgs += @("--observed-at", $script:DomclickObservedAt)
    }

    if ($SourceArgs[0] -eq "--url-file") {
        $BatchArgs += @(
            "--output-root", (Join-Path $RepoRoot "data\raw\domclick"),
            "--collection-date", $CollectionDate,
            "--max-urls", "$MaxUrls",
            "--delay-seconds", "$DelaySeconds"
        )
    }

    $BatchExitCode = Invoke-DomclickNativeCommand -FilePath $Python -Arguments $BatchArgs
    if ($BatchExitCode -ne 0) {
        throw "Domclick scheduled batch failed with exit code $BatchExitCode"
    }
}
finally {
    Stop-Transcript | Out-Null
}
