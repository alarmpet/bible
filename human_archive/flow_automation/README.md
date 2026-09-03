# NOLLAM Flow Automation

## Install

1. Open chrome://extensions, enable Developer mode, choose Load unpacked, and select the extension directory.
2. Copy the extension ID (32 lowercase letters).
3. Run from D:\module\bible\human_archive:

powershell -ExecutionPolicy Bypass -File "D:\module\bible\human_archive\flow_automation\native_host\install_native_host.ps1" -ExtensionId "ACTUAL_32_CHARACTER_EXTENSION_ID"

Use the visible Google Flow project URL in the job compiler; replace every uppercase placeholder before running.

## Operation

Compile a job, open the exact Flow project, and use Generate Missing. The extension submits one shot at a time and waits for an unambiguous new completed card. Stop is always available during an active job. Resume reloads durable host state after a restart. Generate All requires a new job ID after progress exists.

## Recovery

PROJECT_MISMATCH, FLOW_UI_CHANGED, AMBIGUOUS_RESULT, authentication, CAPTCHA, purchase prompts, and interrupted downloads pause the job. Resolve the issue manually, then Resume. Never approve a purchase, CAPTCHA, or ambiguous result through automation.

## Update and uninstall

Reload the unpacked extension after updating source files. To uninstall, remove only HKCU:\Software\Google\Chrome\NativeMessagingHosts\com.nollam.flow_automation and %LOCALAPPDATA%\NollamFlowAutomation\com.nollam.flow_automation.json; keep job logs and approved assets unless separately archived.
