param(
    [Parameter(Mandatory = $true)]
    [string]$BaseUrl,

    [string]$AdminEmail = "admin@socialsphere.app",
    [string]$AdminPassword = "admin123",

    [string]$UserEmail = "",
    [string]$UserPassword = "",

    [string]$ExpectedVersion = "",

    [switch]$RunRateLimit
)

$ErrorActionPreference = "Stop"
$SupportsWebRequestBasicParsing = (Get-Command Invoke-WebRequest).Parameters.ContainsKey("UseBasicParsing")
$SupportsRestMethodBasicParsing = (Get-Command Invoke-RestMethod).Parameters.ContainsKey("UseBasicParsing")

function Normalize-BaseUrl {
    param([string]$Url)

    if ([string]::IsNullOrWhiteSpace($Url)) {
        throw "BaseUrl is required"
    }

    $trimmed = $Url.Trim().TrimEnd('/')
    if ($trimmed -notmatch '^https?://') {
        throw "BaseUrl must start with http:// or https://"
    }

    return $trimmed
}

$BaseUrl = Normalize-BaseUrl -Url $BaseUrl

$passed = 0
$failed = 0
$warnings = 0

function Write-Pass {
    param([string]$Name, [string]$Detail)
    $script:passed++
    Write-Host "[PASS] $Name - $Detail" -ForegroundColor Green
}

function Write-Fail {
    param([string]$Name, [string]$Detail)
    $script:failed++
    Write-Host "[FAIL] $Name - $Detail" -ForegroundColor Red
}

function Write-Warn {
    param([string]$Name, [string]$Detail)
    $script:warnings++
    Write-Host "[WARN] $Name - $Detail" -ForegroundColor Yellow
}

function Normalize-VersionToken {
    param([string]$Value)

    $token = [string]$Value
    if ([string]::IsNullOrWhiteSpace($token)) {
        return ""
    }

    $token = $token.Trim()
    if ($token.StartsWith("v", [System.StringComparison]::OrdinalIgnoreCase)) {
        return $token.Substring(1)
    }

    return $token
}

function Invoke-JsonRequest {
    param(
        [string]$Method,
        [string]$Url,
        [hashtable]$Headers,
        [object]$Body,
        [switch]$Raw,
        [int]$TimeoutSec = 30
    )

    $params = @{
        Method      = $Method
        Uri         = $Url
        TimeoutSec  = $TimeoutSec
        Headers     = @{}
    }

    if ($Headers) {
        $params.Headers = $Headers
    }

    if ($Body -ne $null) {
        $params.ContentType = "application/json"
        $params.Body = ($Body | ConvertTo-Json -Depth 10)
    }

    # PowerShell 5 may prompt interactively unless basic parsing is forced.
    if ($Raw -and $SupportsWebRequestBasicParsing) {
        $params.UseBasicParsing = $true
    }
    elseif ((-not $Raw) -and $SupportsRestMethodBasicParsing) {
        $params.UseBasicParsing = $true
    }

    if ($Raw) {
        return Invoke-WebRequest @params
    }

    return Invoke-RestMethod @params
}

function Assert-Status {
    param(
        [string]$Name,
        [string]$Method,
        [string]$Url,
        [int]$ExpectedStatus,
        [hashtable]$Headers,
        [object]$Body
    )

    try {
        $resp = Invoke-JsonRequest -Method $Method -Url $Url -Headers $Headers -Body $Body -Raw
        if ($resp.StatusCode -eq $ExpectedStatus) {
            Write-Pass $Name "status $($resp.StatusCode)"
            return $true
        }

        Write-Fail $Name "expected $ExpectedStatus got $($resp.StatusCode)"
        return $false
    }
    catch {
        $status = $null
        if ($_.Exception.Response -and $_.Exception.Response.StatusCode) {
            $status = $_.Exception.Response.StatusCode.value__
        }

        if ($status -eq $ExpectedStatus) {
            Write-Pass $Name "status $status"
            return $true
        }

        if ($null -eq $status) {
            Write-Fail $Name "expected $ExpectedStatus got connection/runtime error: $($_.Exception.Message)"
        }
        else {
            Write-Fail $Name "expected $ExpectedStatus got $status"
        }
        return $false
    }
}

Write-Host "Running smoke tests against $BaseUrl" -ForegroundColor Cyan

# 1) Health and docs
try {
    $healthRaw = Invoke-JsonRequest -Method GET -Url "$BaseUrl/health" -Raw
    if ($healthRaw.StatusCode -eq 200) {
        Write-Pass "Health endpoint" "status 200"

        if ($ExpectedVersion) {
            try {
                $healthJson = $healthRaw.Content | ConvertFrom-Json
                $actualVersion = [string]$healthJson.version
                $actualNormalized = Normalize-VersionToken -Value $actualVersion
                $expectedNormalized = Normalize-VersionToken -Value $ExpectedVersion

                if ($actualNormalized -and $actualNormalized -eq $expectedNormalized) {
                    Write-Pass "Health version" "expected $ExpectedVersion"
                }
                elseif ($actualVersion) {
                    Write-Fail "Health version" "expected $ExpectedVersion got $actualVersion"
                }
                else {
                    Write-Fail "Health version" "expected $ExpectedVersion but response has no version"
                }
            }
            catch {
                Write-Fail "Health version" "unable to parse /health JSON: $($_.Exception.Message)"
            }
        }
    }
    else {
        Write-Fail "Health endpoint" "expected 200 got $($healthRaw.StatusCode)"
    }
}
catch {
    Write-Fail "Health endpoint" $_.Exception.Message
}

Assert-Status -Name "Docs endpoint" -Method GET -Url "$BaseUrl/docs" -ExpectedStatus 200 | Out-Null

# 2) Admin login and token rotation
$adminAccess = ""
$adminRefresh = ""
$newAdminRefresh = ""

try {
    $adminLogin = Invoke-JsonRequest -Method POST -Url "$BaseUrl/api/auth/login" -Body @{
        email    = $AdminEmail
        password = $AdminPassword
    }

    $adminAccess = [string]$adminLogin.access_token
    $adminRefresh = [string]$adminLogin.refresh_token

    if (-not $adminAccess -or -not $adminRefresh) {
        Write-Fail "Admin login" "missing access_token or refresh_token"
    }
    else {
        Write-Pass "Admin login" "tokens received"
    }
}
catch {
    Write-Fail "Admin login" $_.Exception.Message
}

if ($adminAccess) {
    Assert-Status -Name "Protected me/social with admin token" -Method GET -Url "$BaseUrl/api/users/me/social" -ExpectedStatus 200 -Headers @{ Authorization = "Bearer $adminAccess" } | Out-Null
}

if ($adminRefresh) {
    try {
        $rotated = Invoke-JsonRequest -Method POST -Url "$BaseUrl/api/auth/refresh" -Body @{ refresh_token = $adminRefresh }
        $newAdminRefresh = [string]$rotated.refresh_token
        $newAdminAccess = [string]$rotated.access_token

        if ($newAdminRefresh -and $newAdminAccess) {
            Write-Pass "Refresh token rotation" "new access and refresh tokens received"
        }
        else {
            Write-Fail "Refresh token rotation" "missing rotated tokens"
        }
    }
    catch {
        Write-Fail "Refresh token rotation" $_.Exception.Message
    }

    Assert-Status -Name "Old refresh replay blocked" -Method POST -Url "$BaseUrl/api/auth/refresh" -ExpectedStatus 401 -Body @{ refresh_token = $adminRefresh } | Out-Null
}

# 3) Admin guard
if ($adminAccess) {
    Assert-Status -Name "Admin endpoint with admin token" -Method GET -Url "$BaseUrl/api/admin/audit-logs" -ExpectedStatus 200 -Headers @{ Authorization = "Bearer $adminAccess" } | Out-Null
}

$nonAdminAccess = ""
if ($UserEmail -and $UserPassword) {
    try {
        $userLogin = Invoke-JsonRequest -Method POST -Url "$BaseUrl/api/auth/login" -Body @{
            email    = $UserEmail
            password = $UserPassword
        }
        $nonAdminAccess = [string]$userLogin.access_token
        if ($nonAdminAccess) {
            Write-Pass "Non-admin login" "token received"
        }
        else {
            Write-Fail "Non-admin login" "missing access token"
        }
    }
    catch {
        Write-Fail "Non-admin login" $_.Exception.Message
    }

    if ($nonAdminAccess) {
        Assert-Status -Name "Admin endpoint denied for non-admin" -Method GET -Url "$BaseUrl/api/admin/audit-logs" -ExpectedStatus 403 -Headers @{ Authorization = "Bearer $nonAdminAccess" } | Out-Null
    }
}
else {
    Write-Warn "Admin guard non-admin check" "skipped; pass -UserEmail and -UserPassword to enable"
}

# 4) Legacy endpoint deprecation
Assert-Status -Name "Legacy users social deprecated" -Method GET -Url "$BaseUrl/api/users/$([uri]::EscapeDataString($AdminEmail))/social" -ExpectedStatus 410 | Out-Null
Assert-Status -Name "Legacy notifications deprecated" -Method GET -Url "$BaseUrl/api/notifications/$([uri]::EscapeDataString($AdminEmail))" -ExpectedStatus 410 | Out-Null
Assert-Status -Name "Legacy messages deprecated" -Method GET -Url "$BaseUrl/api/messages/$([uri]::EscapeDataString($AdminEmail))" -ExpectedStatus 410 | Out-Null

# 5) Optional rate-limit probes
if ($RunRateLimit) {
    $hit429 = $false
    for ($i = 1; $i -le 16; $i++) {
        try {
            Invoke-JsonRequest -Method POST -Url "$BaseUrl/api/auth/login" -Body @{ email = "nobody+$i@example.com"; password = "bad-pass" } | Out-Null
        }
        catch {
            $status = $_.Exception.Response.StatusCode.value__
            if ($status -eq 429) {
                $hit429 = $true
                break
            }
        }
    }

    if ($hit429) {
        Write-Pass "Login rate limit" "received 429 under repeated invalid attempts"
    }
    else {
        Write-Warn "Login rate limit" "did not observe 429 in current run window"
    }
}
else {
    Write-Warn "Rate limit tests" "skipped; pass -RunRateLimit to enable"
}

# 6) Logout rotate token cleanup
if ($adminAccess -and $newAdminRefresh) {
    Assert-Status -Name "Logout with rotated refresh token" -Method POST -Url "$BaseUrl/api/auth/logout" -ExpectedStatus 200 -Headers @{ Authorization = "Bearer $adminAccess" } -Body @{ refresh_token = $newAdminRefresh } | Out-Null
}

Write-Host ""
Write-Host "Smoke test summary" -ForegroundColor Cyan
Write-Host "Passed: $passed"
Write-Host "Failed: $failed"
Write-Host "Warnings: $warnings"

if ($failed -gt 0) {
    exit 1
}

exit 0
