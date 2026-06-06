# Full run: all startups from startups.xlsx (resumes if interrupted)
Set-Location $PSScriptRoot
$env:PYTHONIOENCODING = "utf-8"
python run.py
