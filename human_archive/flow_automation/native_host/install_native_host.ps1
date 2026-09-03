[CmdletBinding(SupportsShouldProcess)]
param(
  [Parameter(Mandatory=$true)][string]$ExtensionId,
  [string]$PythonExe = 'python'
)
$ErrorActionPreference = 'Stop'
if ($ExtensionId -notmatch '^[a-p]{32}$') { throw 'ExtensionId must be 32 lowercase letters a-p' }
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$launcher = (Resolve-Path (Join-Path $PSScriptRoot 'host_launcher.cmd')).Path
$template = Join-Path $PSScriptRoot 'com.nollam.flow_automation.json.template'
$installDir = Join-Path $env:LOCALAPPDATA 'NollamFlowAutomation'
$manifestPath = Join-Path $installDir 'com.nollam.flow_automation.json'
$manifest = (Get-Content -Raw $template).Replace('__HOST_LAUNCHER__', $launcher).Replace('__EXTENSION_ID__', $ExtensionId)
$registryPath = 'HKCU:\Software\Google\Chrome\NativeMessagingHosts\com.nollam.flow_automation'
$result = [ordered]@{ manifest_path=$manifestPath; registry_path=$registryPath; extension_id=$ExtensionId; python_exe=$PythonExe; what_if=[bool]$WhatIfPreference }
if ($PSCmdlet.ShouldProcess($manifestPath, 'write native host manifest')) {
  New-Item -ItemType Directory -Path $installDir -Force | Out-Null
  [IO.File]::WriteAllText($manifestPath, $manifest, (New-Object Text.UTF8Encoding($false)))
  New-Item -Path $registryPath -Force | Out-Null
  New-ItemProperty -Path $registryPath -Name '(default)' -Value $manifestPath -PropertyType String -Force | Out-Null
}
$result | ConvertTo-Json -Compress
