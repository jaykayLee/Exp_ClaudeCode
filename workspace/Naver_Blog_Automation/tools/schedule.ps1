param([switch]$Remove)
$ErrorActionPreference = 'Stop'
$Root = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$Hash = [BitConverter]::ToString([Security.Cryptography.SHA256]::Create().ComputeHash([Text.Encoding]::UTF8.GetBytes($Root))).Replace('-','').Substring(0,8)
$TaskName = 'BlogWorkspace_LocalReview_'+$Hash
if ($Remove) {
    $answer=Read-Host "Remove task $TaskName only? [Y/N]"
    if ($answer -match '^[Yy]$') {
        $existing=Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
        if ($existing) { Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false; Write-Host 'Task removed.' }
        else { Write-Host 'This workspace has no registered task.' }
    }
    exit
}
$Python = Join-Path $Root '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $Python)) { throw 'Run install.bat first.' }
Write-Host 'This optional task ONLY validates current inbox data and creates a local preview.'
Write-Host 'It does NOT refresh prices, scrape websites, log in, or publish a blog post.'
Write-Host 'The PC must be on and this Windows user must be signed in. Do not enable until a manual run works.'
$answer=Read-Host 'Register this local-only task? [Y/N]'
if ($answer -notmatch '^[Yy]$') { Write-Host 'No task registered.'; exit }
$Time=Read-Host 'Daily time in this PC local time, HH:mm (for example 08:00)'
if ($Time -notmatch '^([01][0-9]|2[0-3]):[0-5][0-9]$') { throw 'Invalid HH:mm.' }
$At=[DateTime]::Today.Add([TimeSpan]::Parse($Time))
$Existing=Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($Existing) {
    $answer=Read-Host 'A task for this workspace exists. Replace its schedule? [Y/N]'
    if ($answer -notmatch '^[Yy]$') { exit }
}
$Action=New-ScheduledTaskAction -Execute $Python -Argument ('"'+(Join-Path $Root 'tools\run_once.py')+'"') -WorkingDirectory $Root
$Trigger=New-ScheduledTaskTrigger -Daily -At $At
$Settings=New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 10)
$User=[Security.Principal.WindowsIdentity]::GetCurrent().Name
$Principal=New-ScheduledTaskPrincipal -UserId $User -LogonType Interactive -RunLevel Limited
Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -Principal $Principal -Description 'Local review only: no collection and no publication.' -Force | Out-Null
Write-Host "Created $TaskName at $Time (PC timezone). Moving the workspace requires re-registration."
