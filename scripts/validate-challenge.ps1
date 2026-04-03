param(
    [Parameter(Mandatory = $true)]
    [string]$Path
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$challengePath = Join-Path $repoRoot $Path

if (-not (Test-Path $challengePath)) {
    throw "Challenge path not found: $challengePath"
}

$requiredFiles = @(
    'Dockerfile',
    'app.py',
    'flag.txt',
    'requirements.txt',
    'docker-compose.yml',
    'challenge.yml'
)

$errors = @()
foreach ($file in $requiredFiles) {
    if (-not (Test-Path (Join-Path $challengePath $file))) {
        $errors += "Missing required file: $file"
    }
}

$challengeYml = Join-Path $challengePath 'challenge.yml'
$composeYml = Join-Path $challengePath 'docker-compose.yml'

if (Test-Path $challengeYml) {
    $content = Get-Content $challengeYml -Raw
    foreach ($key in @('name', 'category', 'value', 'type', 'description', 'flag', 'port')) {
        if ($content -notmatch ("(?m)^{0}:" -f [regex]::Escape($key))) {
            $errors += "challenge.yml missing key: $key"
        }
    }

    $portMatch = Select-String -Path $challengeYml -Pattern '^port:\s*(\d+)' | Select-Object -First 1
    if (-not $portMatch) {
        $errors += 'challenge.yml missing numeric port'
    } else {
        $port = [int]$portMatch.Matches[0].Groups[1].Value
        if ($port -lt 5001 -or $port -gt 5999) {
            $errors += "Port out of expected range (5001-5999): $port"
        }

        if (Test-Path $composeYml) {
            $compose = Get-Content $composeYml -Raw
            if ($compose -notmatch ("`"{0}:5000`"" -f $port)) {
                $errors += "docker-compose.yml does not expose expected port mapping: $port:5000"
            }
        }
    }
}

if ($errors.Count -gt 0) {
    Write-Host 'Validation FAILED:' -ForegroundColor Red
    $errors | ForEach-Object { Write-Host (" - {0}" -f $_) -ForegroundColor Red }
    exit 1
}

Write-Host 'Validation OK' -ForegroundColor Green
Write-Host ("Challenge path: {0}" -f $Path)
