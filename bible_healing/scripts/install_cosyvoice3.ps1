# Install Fun-CosyVoice3 on D: for CPU-only A/B tests.
# Does not change the production SuperTonic3 pipeline.
# Usage: powershell -ExecutionPolicy Bypass -File bible_healing/scripts/install_cosyvoice3.ps1

$ErrorActionPreference = "Stop"
$CosyRoot = "D:\Fun-CosyVoice3"
$VenvDir = "C:\Users\amd\.venvs\cosyvoice3-py310"
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"
$ModelDir = Join-Path $CosyRoot "pretrained_models\Fun-CosyVoice3-0.5B"
$Repo = "https://github.com/FunAudioLLM/CosyVoice.git"
$ModuleRoot = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
if (-not (Test-Path (Join-Path $ModuleRoot "modern\scripts\cosyvoice3_engine.py"))) {
    $ModuleRoot = "C:\Users\amd\module"
}

Write-Host "=== CosyVoice3 CPU install ==="
Write-Host "root=$CosyRoot"
Write-Host "This is a TEST path. SuperTonic3 stays production."

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw "uv is required. Install uv, then re-run."
}
uv python install 3.10 | Out-Host

if (-not (Test-Path $CosyRoot)) {
    Write-Host "cloning $Repo ..."
    git clone --recursive --depth 1 $Repo $CosyRoot
} else {
    Write-Host "repo exists, fetching submodules"
    Push-Location $CosyRoot
    git submodule update --init --recursive
    Pop-Location
}

if (-not (Test-Path $VenvPython)) {
    Write-Host "creating Python 3.10 venv on C: (D: is slow for many small files)"
    New-Item -ItemType Directory -Force -Path (Split-Path $VenvDir -Parent) | Out-Null
    $env:UV_LINK_MODE = "copy"
    uv venv --seed --python 3.10 $VenvDir
}

$ReqCpu = Join-Path $ModuleRoot "bible_healing\config\cosyvoice3_requirements_cpu_win.txt"
Write-Host "installing CPU torch + inference deps"
$env:UV_LINK_MODE = "copy"
uv pip install --python $VenvPython pip setuptools wheel
uv pip install --python $VenvPython torch==2.3.1 torchaudio==2.3.1 --index-url https://download.pytorch.org/whl/cpu
uv pip install --python $VenvPython -r $ReqCpu

New-Item -ItemType Directory -Force -Path (Join-Path $CosyRoot "pretrained_models") | Out-Null
if (-not (Test-Path (Join-Path $ModelDir "cosyvoice.yaml")) -and -not (Test-Path (Join-Path $ModelDir "configuration.json"))) {
    Write-Host "downloading Fun-CosyVoice3-0.5B-2512 (HuggingFace)..."
    & $VenvPython -c @"
from huggingface_hub import snapshot_download
snapshot_download('FunAudioLLM/Fun-CosyVoice3-0.5B-2512', local_dir=r'$ModelDir')
print('model ok', r'$ModelDir')
"@
} else {
    Write-Host "model dir already present: $ModelDir"
}

Write-Host "=== install summary ==="
Write-Host "python=$VenvPython"
& $VenvPython -c "import sys; print('python', sys.version)"
& $VenvPython -c "import torch; print('torch', torch.__version__, 'cuda', torch.cuda.is_available())"
Write-Host "model=$ModelDir"
Write-Host "smoke: python modern/scripts/test_cosyvoice3_smoke.py"
