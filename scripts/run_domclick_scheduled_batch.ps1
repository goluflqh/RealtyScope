param(
    [string]$DatabaseUrl = $env:DATABASE_URL,
    [string]$CollectionDate = "",
    [string]$SourcePath = "",
    [int]$MaxRecords = 2000,
    [int]$MinRecords = 1,
    [int]$MinCleanRecords = 1000,
    [int]$MaxUrls = 50,
    [double]$DelaySeconds = 2,
    [string]$ChromePath = $env:REALTYSCOPE_CHROME_PATH,
    [string]$ChromeUserDataDir = "",
    [string]$ChromeProfileDirectory = "Default",
    [int]$CaptureOffsetStart = 0,
    [int]$CaptureOffsetStop = 1980,
    [int]$CaptureOffsetStep = 20,
    [int]$CaptureMaxPages = 100,
    [double]$CaptureDelaySeconds = 3,
    [double]$CaptureTimeoutSeconds = 90,
    [int]$CaptureVirtualTimeBudgetMs = 10000,
    [switch]$SkipCapture,
    [switch]$SkipDockerStart
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

function Resolve-DomclickSourceArgs {
    param(
        [string]$RepoRoot,
        [string]$CollectionDate,
        [string]$SourcePath,
        [string]$Python
    )

    if (-not [string]::IsNullOrWhiteSpace($SourcePath)) {
        if (-not (Test-Path $SourcePath -PathType Container)) {
            throw "Configured source path does not exist: $SourcePath"
        }
        return @("--source-path", $SourcePath)
    }

    $RawRoot = Join-Path $RepoRoot "data\raw\domclick"
    $DayDir = Join-Path $RawRoot $CollectionDate
    $BulkDir = Join-Path $RawRoot "$CollectionDate-bulk"
    $UrlFile = Join-Path $RepoRoot "data\raw\domclick-urls.txt"

    if (Test-Path $DayDir -PathType Container) {
        return @("--source-path", $DayDir)
    }
    if (Test-Path $BulkDir -PathType Container) {
        return @("--source-path", $BulkDir)
    }
    if (-not $SkipCapture) {
        $CaptureArgs = @(
            "-m", "realtyscope.ingestion.domclick_chrome_capture",
            "--output-root", (Join-Path $RepoRoot "data\raw\domclick"),
            "--collection-date", $CollectionDate,
            "--offset-start", "$CaptureOffsetStart",
            "--offset-stop", "$CaptureOffsetStop",
            "--offset-step", "$CaptureOffsetStep",
            "--max-pages", "$CaptureMaxPages",
            "--delay-seconds", "$CaptureDelaySeconds",
            "--timeout-seconds", "$CaptureTimeoutSeconds",
            "--virtual-time-budget-ms", "$CaptureVirtualTimeBudgetMs",
            "--profile-directory", $ChromeProfileDirectory,
            "--min-records", "$MinCleanRecords",
            "--operator-note", "scheduled batch fallback capture using Chrome profile $ChromeProfileDirectory",
            "--json"
        )
        if (-not [string]::IsNullOrWhiteSpace($ChromePath)) {
            $CaptureArgs += @("--chrome-path", $ChromePath)
        }
        if (-not [string]::IsNullOrWhiteSpace($ChromeUserDataDir)) {
            $CaptureArgs += @("--chrome-user-data-dir", $ChromeUserDataDir)
        }

        $CaptureOutput = & $Python @CaptureArgs
        $CaptureExitCode = $LASTEXITCODE
        if ($CaptureOutput) {
            $CaptureOutput | ForEach-Object { Write-Host $_ }
        }
        if ($CaptureExitCode -ne 0) {
            throw "Domclick Chrome capture failed with exit code $CaptureExitCode"
        }
        if (Test-Path $BulkDir -PathType Container) {
            return @("--source-path", $BulkDir)
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

    if (-not $SkipDockerStart) {
        $WslRepoRoot = ConvertTo-WslPath $RepoRoot
        wsl -d Ubuntu -- bash -lc "cd '$WslRepoRoot' && docker compose up -d db"
        if ($LASTEXITCODE -ne 0) {
            throw "WSL Docker startup failed with exit code $LASTEXITCODE"
        }
    }

    $Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"
    & $Python -m alembic upgrade head
    if ($LASTEXITCODE -ne 0) {
        throw "Alembic upgrade failed with exit code $LASTEXITCODE"
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

    if ($SourceArgs[0] -eq "--url-file") {
        $BatchArgs += @(
            "--output-root", (Join-Path $RepoRoot "data\raw\domclick"),
            "--collection-date", $CollectionDate,
            "--max-urls", "$MaxUrls",
            "--delay-seconds", "$DelaySeconds"
        )
    }

    & $Python @BatchArgs
    if ($LASTEXITCODE -ne 0) {
        throw "Domclick scheduled batch failed with exit code $LASTEXITCODE"
    }
}
finally {
    Stop-Transcript | Out-Null
}
