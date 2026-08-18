$summary = 'D:\bible_healing_ep01\work\pipeline\pipeline_summary.json'
$deadline = (Get-Date).AddHours(10)
while ((Get-Date) -lt $deadline) {
    if (Test-Path $summary) {
        Start-Sleep -Seconds 2
        try {
            $j = Get-Content -Raw -Encoding UTF8 $summary | ConvertFrom-Json
            if ($j.ok -eq $true) {
                Write-Output 'DONE'
                exit 0
            }
            Write-Output 'FAILED'
            exit 1
        } catch {
            Start-Sleep -Seconds 5
        }
    }
    Start-Sleep -Seconds 30
}
Write-Output 'FAILED'
exit 1
