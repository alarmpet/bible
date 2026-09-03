@echo off
setlocal
pushd "%~dp0..\.."
python -m flow_automation.native_host.host
popd
