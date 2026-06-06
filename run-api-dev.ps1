# API without login (uses your existing batch LinkedIn on 9223). Batch email scripts unaffected.
Set-Location $PSScriptRoot
$env:PYTHONIOENCODING = "utf-8"
$env:REQUIRE_AUTH = "false"

$dotenv = Join-Path $PSScriptRoot ".env"
if (Test-Path $dotenv) {
    Get-Content $dotenv | ForEach-Object {
        $line = $_.Trim()
        if (-not $line -or $line.StartsWith("#")) { return }
        $eq = $line.IndexOf("=")
        if ($eq -lt 1) { return }
        $key = $line.Substring(0, $eq).Trim()
        $val = $line.Substring($eq + 1).Trim().Trim('"')
        Set-Item -Path "env:$key" -Value $val
    }
}

python -m api.server
