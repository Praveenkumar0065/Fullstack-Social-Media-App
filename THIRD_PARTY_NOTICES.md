# Third-Party Notices

This project uses third-party open-source software. The dependency list below is based on installed package metadata in this workspace on 2026-03-22.

## Frontend Dependencies (frontend_react)

| Package | Version | License |
|---|---:|---|
| axios | 1.13.6 | MIT |
| framer-motion | 12.38.0 | MIT |
| react | 18.3.1 | MIT |
| react-dom | 18.3.1 | MIT |
| react-hot-toast | 2.6.0 | MIT |
| react-router-dom | 6.30.3 | MIT |
| @types/react | 18.3.28 | MIT |
| @types/react-dom | 18.3.7 | MIT |
| @vitejs/plugin-react | 4.7.0 | MIT |
| autoprefixer | 10.4.27 | MIT |
| postcss | 8.5.8 | MIT |
| tailwindcss | 3.4.19 | MIT |
| vite | 5.4.21 | MIT |

## Backend Dependencies (backend_code)

| Package | Version | License |
|---|---:|---|
| fastapi | 0.115.0 | MIT |
| uvicorn[standard] | 0.30.6 | BSD |
| pydantic | 2.9.2 | MIT |
| python-dotenv | 1.0.1 | BSD-3-Clause |
| email-validator | 2.2.0 | Unlicense |
| pymongo | 4.11.1 | Apache-2.0 |
| PyJWT | 2.10.1 | MIT |
| cloudinary | 1.44.0 | MIT |
| python-multipart | 0.0.20 | Apache-2.0 |

## Compliance Notes

- Most dependencies are permissive licenses (MIT, BSD, Apache-2.0, Unlicense).
- Apache-2.0 dependencies generally require preserving license and notice text where distributed.
- License obligations can change with dependency upgrades. Re-audit after dependency updates.
- Third-party media, icons, logos, and fonts may have separate terms and are not covered by package-manager metadata.

Allowed license policy currently enforced in CI/release gate:
- MIT
- Apache-2.0
- BSD-3-Clause
- BSD (generic classifier)
- Unlicense
- ISC

Risk threshold policy currently enforced in CI/release gate:
- fail-on-risk medium
- Outcome:
  - medium-risk and high-risk licenses fail CI/release gate
  - only low-risk licenses pass under the current dependency set

## Re-audit Commands (PowerShell)

Strict + whitelist policy check:

```powershell
d:/user/aprav/Downloads/fullstack/.venv/Scripts/python.exe scripts/check_dependency_licenses.py --verify-notices --strict --allowed-license MIT --allowed-license Apache-2.0 --allowed-license BSD-3-Clause --allowed-license BSD --allowed-license Unlicense --allowed-license ISC --fail-on-risk medium --report-json artifacts/license-compliance-local.json
```

Generate local HTML dashboard from JSON report:

```powershell
d:/user/aprav/Downloads/fullstack/.venv/Scripts/python.exe scripts/generate_license_dashboard.py --input artifacts/license-compliance-local.json --output artifacts/license-compliance-local.html --title "Local License Compliance Dashboard"
```

Frontend direct dependency licenses:

```powershell
$pkg = Get-Content frontend_react\package.json -Raw | ConvertFrom-Json
$names = @()
$names += $pkg.dependencies.PSObject.Properties.Name
$names += $pkg.devDependencies.PSObject.Properties.Name
foreach ($n in $names) {
  $p = Join-Path "frontend_react\node_modules" ($n + "\package.json")
  if (Test-Path $p) {
    $j = Get-Content $p -Raw | ConvertFrom-Json
    "$($j.name)|$($j.version)|$($j.license)"
  } else {
    "$n|MISSING|MISSING"
  }
}
```

Backend dependency licenses from venv metadata:

```powershell
$reqs = Get-Content backend_code\requirements.txt | Where-Object { $_ -and -not $_.StartsWith('#') }
foreach ($r in $reqs) {
  $base = ($r -split '==')[0]
  $name = ($base -split '\[')[0]
  $candidates = @($name, ($name -replace '-', '_'))
  $f = $null
  foreach ($c in $candidates) {
    $pattern = ".venv\Lib\site-packages\$c-*dist-info\METADATA"
    $hit = Get-ChildItem -Path $pattern -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($hit) { $f = $hit; break }
  }
  if (-not $f) { "$base|MISSING|MISSING"; continue }
  $meta = Get-Content $f.FullName
  $verMatch = ($meta | Select-String '^Version:\s*(.+)$' | Select-Object -First 1)
  $licMatch = ($meta | Select-String '^License:\s*(.+)$' | Select-Object -First 1)
  $clfMatch = ($meta | Select-String '^Classifier:\s*License\s*::\s*(.+)$' | Select-Object -First 1)
  $ver = if ($verMatch) { $verMatch.Matches.Groups[1].Value } else { 'UNKNOWN' }
  $lic = if ($licMatch -and $licMatch.Matches.Groups[1].Value) { $licMatch.Matches.Groups[1].Value } elseif ($clfMatch) { $clfMatch.Matches.Groups[1].Value } else { 'UNKNOWN' }
  "$base|$ver|$lic"
}
```

## Disclaimer

This file is for engineering traceability and is not legal advice.
