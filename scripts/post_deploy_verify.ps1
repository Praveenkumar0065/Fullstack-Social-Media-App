param(
    [Parameter(Mandatory = $true)]
    [string]$BaseUrl,

    [string]$ExpectedVersion = "",
    [string]$AdminEmail = "admin@socialsphere.app",
    [string]$AdminPassword = "admin123",
    [string]$UserEmail = "",
    [string]$UserPassword = "",
    [switch]$RunRateLimit
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$versionFile = Join-Path $repoRoot "VERSION"
$smokeScript = Join-Path $PSScriptRoot "smoke_test.ps1"

if (-not (Test-Path $smokeScript)) {
    throw "Smoke script not found at $smokeScript"
}

if (-not $ExpectedVersion) {
    if (-not (Test-Path $versionFile)) {
        throw "VERSION file not found at $versionFile"
    }

    $ExpectedVersion = (Get-Content $versionFile -Raw).Trim()
    if (-not $ExpectedVersion) {
        throw "VERSION file is empty"
    }
}

Write-Host "Running post-deploy verification" -ForegroundColor Cyan
Write-Host "BaseUrl: $BaseUrl"
Write-Host "ExpectedVersion: $ExpectedVersion"

$smokeArgs = @{
    BaseUrl = $BaseUrl
    ExpectedVersion = $ExpectedVersion
    AdminEmail = $AdminEmail
    AdminPassword = $AdminPassword
}

if ($UserEmail -and $UserPassword) {
    $smokeArgs.UserEmail = $UserEmail
    $smokeArgs.UserPassword = $UserPassword
}

if ($RunRateLimit) {
    $smokeArgs.RunRateLimit = $true
}

& $smokeScript @smokeArgs
exit $LASTEXITCODE
