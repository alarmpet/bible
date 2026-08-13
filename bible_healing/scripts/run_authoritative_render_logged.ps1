$ErrorActionPreference = 'Continue'
$root = 'D:\bible_healing_ep01\work'
New-Item -ItemType Directory -Force -Path $root | Out-Null
$out = Join-Path $root 'render.stdout.log'
$err = Join-Path $root 'render.stderr.log'
& python 'C:\Users\amd\module\bible_healing\scripts\render_authoritative_full.py' 1> $out 2> $err
exit $LASTEXITCODE
