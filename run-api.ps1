# API server (serves built web/ from web/dist when present)
Set-Location $PSScriptRoot
$env:PYTHONIOENCODING = "utf-8"

function Import-DotEnv {
    param([string]$Path)
    if (-not (Test-Path $Path)) { return }
    Get-Content $Path | ForEach-Object {
        $line = $_.Trim()
        if (-not $line -or $line.StartsWith("#")) { return }
        $eq = $line.IndexOf("=")
        if ($eq -lt 1) { return }
        $key = $line.Substring(0, $eq).Trim()
        $val = $line.Substring($eq + 1).Trim()
        if (
            ($val.StartsWith('"') -and $val.EndsWith('"')) -or
            ($val.StartsWith("'") -and $val.EndsWith("'"))
        ) {
            $val = $val.Substring(1, $val.Length - 2)
        }
        Set-Item -Path "env:$key" -Value $val
    }
}

Import-DotEnv (Join-Path $PSScriptRoot ".env")

if (-not $env:LINKIT_V5_BACKEND) {
    $defaultBackend = "C:\Disk E\Startups\Linkit\linkit_v5\backend"
    if (Test-Path (Join-Path $defaultBackend "serviceAccountKey.json")) {
        $env:LINKIT_V5_BACKEND = $defaultBackend
    }
}

if (-not $env:LINKIT_APP_URL) {
    $env:LINKIT_APP_URL = "https://linkitapp.in"
}

if (-not $env:CORS_ORIGINS) {
    $env:CORS_ORIGINS = "http://localhost:5173,http://127.0.0.1:5173"
}

if (-not $env:APP_SECRET) {
    $env:APP_SECRET = "local-dev-secret"
}

Write-Host "Founder Email API"
Write-Host "  LINKIT_V5_BACKEND = $($env:LINKIT_V5_BACKEND)"
Write-Host "  LINKIT_APP_URL    = $($env:LINKIT_APP_URL)"
Write-Host "  CORS_ORIGINS      = $($env:CORS_ORIGINS)"
Write-Host ""

python -m api.server
