param(
    [Parameter(Mandatory = $true)]
    [string]$BaseUrl,

    [string]$PythonExe = "d:/user/aprav/Downloads/fullstack/.venv/Scripts/python.exe",

    [string]$AdminEmail = "admin@socialsphere.app",
    [string]$AdminPassword = "admin123",
    [string]$UserEmail = "",
    [string]$UserPassword = "",

    [switch]$RunRateLimit,
    [switch]$SkipBackendTests,
    [switch]$SkipFrontendBuild,
    [switch]$SkipLicenseAudit,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

function Invoke-Step {
    param(
        [string]$Name,
        [ScriptBlock]$Action
    )

    Write-Host ""
    Write-Host "=== $Name ===" -ForegroundColor Cyan

    if ($DryRun) {
        Write-Host "[DRY-RUN] Skipped" -ForegroundColor Yellow
        return
    }

    & $Action
}

function Assert-Command {
    param([string]$Command)

    if (-not (Get-Command $Command -ErrorAction SilentlyContinue)) {
        throw "Required command not found: $Command"
    }
}

function Invoke-External {
    param(
        [string]$Name,
        [ScriptBlock]$Action
    )

    & $Action
    if ($LASTEXITCODE -ne 0) {
        throw "$Name failed with exit code $LASTEXITCODE"
    }
}

Assert-Command -Command "npm"
if (-not (Test-Path $PythonExe)) {
    throw "Python executable not found: $PythonExe"
}

Invoke-Step -Name "Backend unit tests" -Action {
    if ($SkipBackendTests) {
        Write-Host "Skipped by flag -SkipBackendTests" -ForegroundColor Yellow
        return
    }

    Invoke-External -Name "backend coverage tests" -Action {
        & $PythonExe -m pytest --cov=backend_code --cov-report=term-missing --cov-fail-under=60 -q backend_code/tests
    }
    Invoke-External -Name "release tooling tests" -Action {
        & $PythonExe -m pytest -q tests
    }
    Invoke-External -Name "backend compile check" -Action {
        & $PythonExe -m compileall backend_code
    }
}

Invoke-Step -Name "Frontend production build" -Action {
    if ($SkipFrontendBuild) {
        Write-Host "Skipped by flag -SkipFrontendBuild" -ForegroundColor Yellow
        return
    }

    Push-Location frontend_react
    try {
        Invoke-External -Name "frontend install" -Action {
            npm ci
        }
        Invoke-External -Name "frontend build" -Action {
            npm run build
        }
    }
    finally {
        Pop-Location
    }
}

Invoke-Step -Name "License compliance audit" -Action {
    if ($SkipLicenseAudit) {
        Write-Host "Skipped by flag -SkipLicenseAudit" -ForegroundColor Yellow
        return
    }

    Invoke-External -Name "license compliance audit" -Action {
        & $PythonExe scripts/check_dependency_licenses.py --verify-notices --strict `
            --allowed-license MIT `
            --allowed-license Apache-2.0 `
            --allowed-license BSD-3-Clause `
            --allowed-license BSD `
            --allowed-license Unlicense `
            --allowed-license ISC `
            --fail-on-risk medium `
            --report-json artifacts/license-compliance-local.json
    }

    Invoke-External -Name "license dashboard generation" -Action {
        & $PythonExe scripts/generate_license_dashboard.py --input artifacts/license-compliance-local.json --output artifacts/license-compliance-local.html --title "Local License Compliance Dashboard"
    }
}

Invoke-Step -Name "Post-deploy smoke tests" -Action {
    $smokeArgs = @{
        BaseUrl = $BaseUrl
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

    Invoke-External -Name "post-deploy smoke tests" -Action {
        ./scripts/smoke_test.ps1 @smokeArgs
    }
}

Write-Host ""
Write-Host "Release checklist completed." -ForegroundColor Green
