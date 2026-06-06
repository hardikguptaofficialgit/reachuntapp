# 5 startups with Mailmeteor emails (interactive warmup on first run)
Set-Location $PSScriptRoot
$env:PYTHONIOENCODING = "utf-8"
python run.py --reset --limit 5 --warmup-mailmeteor --manual-mailmeteor
