param(
    [Parameter(Mandatory = $true)]
    [string]$Name,
    [int]$Port
)

$ErrorActionPreference = 'Stop'

if ($Name -notmatch '^[a-z0-9][a-z0-9-]*$') {
    throw "Invalid challenge name '$Name'. Use lowercase, digits and hyphens only."
}

$repoRoot = Split-Path -Parent $PSScriptRoot
$templatePath = Join-Path $repoRoot 'challenges/_template'
$targetPath = Join-Path $repoRoot ("challenges/{0}" -f $Name)

if (-not (Test-Path $templatePath)) {
    throw "Template folder not found: $templatePath"
}

if (Test-Path $targetPath) {
    throw "Target challenge already exists: $targetPath"
}

if (-not $Port) {
    $usedPorts = @()
    Get-ChildItem -Path (Join-Path $repoRoot 'challenges') -Directory | ForEach-Object {
        $challengeFile = Join-Path $_.FullName 'challenge.yml'
        if (Test-Path $challengeFile) {
            $line = Select-String -Path $challengeFile -Pattern '^port:\s*(\d+)' | Select-Object -First 1
            if ($line) {
                $usedPorts += [int]$line.Matches[0].Groups[1].Value
            }
        }
    }

    if ($usedPorts.Count -eq 0) {
        $Port = 5001
    } else {
        $Port = ([int]($usedPorts | Measure-Object -Maximum).Maximum) + 1
    }
}

if ($Port -lt 5001 -or $Port -gt 5999) {
    throw "Port must be between 5001 and 5999. Provided: $Port"
}

Copy-Item -Path $templatePath -Destination $targetPath -Recurse

$challengeYml = Join-Path $targetPath 'challenge.yml'
$composeYml = Join-Path $targetPath 'docker-compose.yml'

(Get-Content $challengeYml -Raw) `
    -replace '(?m)^name:\s*.*$', ("name: {0}" -f $Name) `
    -replace '(?m)^port:\s*\d+\s*$', ("port: {0}" -f $Port) `
    -replace '(?m)^flag:\s*.*$', ("flag: CTF{{{0}_flag}}" -f ($Name -replace '-', '_')) |
    Set-Content $challengeYml

(Get-Content $composeYml -Raw) `
    -replace 'container_name:\s*.*', ("container_name: {0}" -f $Name) `
    -replace '"\d+:5000"', ("`"{0}:5000`"" -f $Port) |
    Set-Content $composeYml

Write-Host "Challenge created: $targetPath"
Write-Host "Assigned port: $Port"
Write-Host "Next step: ./scripts/validate-challenge.ps1 -Path challenges/$Name"
