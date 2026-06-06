# Build React app and start API (single port 8000)
Set-Location $PSScriptRoot
$env:PYTHONIOENCODING = "utf-8"
Push-Location web
npm run build
if ($LASTEXITCODE -ne 0) { Pop-Location; exit $LASTEXITCODE }
Pop-Location
python -m api.server --host 0.0.0.0 --port 8000
