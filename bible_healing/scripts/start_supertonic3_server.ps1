# Start the existing SuperTonic3 HTTP server so ONNX loads once.
# Does not install CosyVoice or any new TTS.
$ErrorActionPreference = "Stop"
$Root = "C:\Users\amd\supertonic3-local-tts-20260517-r4\supertonic3-local-tts"
$Py = Join-Path $Root ".venv-win\Scripts\python.exe"
if (-not (Test-Path $Py)) {
    throw "SuperTonic venv python missing: $Py"
}
$env:PYTHONPATH = (Join-Path $Root "src")
$env:SUPERTONIC3_HOST = "127.0.0.1"
$env:SUPERTONIC3_PORT = "3093"
Set-Location $Root
Write-Host "SuperTonic3 HTTP http://127.0.0.1:3093  (Ctrl+C to stop)"
& $Py "src\app.py"
