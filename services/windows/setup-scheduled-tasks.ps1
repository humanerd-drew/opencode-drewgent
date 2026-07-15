# {{AGENT_NAME}} — Windows Scheduled Tasks Setup
# Run as Administrator: powershell -ExecutionPolicy Bypass -File setup-scheduled-tasks.ps1

$AgentDir = $env:AGENT_DIR
$PythonPath = $env:PYTHON_PATH
$OpenCodePath = $env:OPENCODE_PATH

if (-not $AgentDir) {
    $AgentDir = "$HOME\.drewgent"
    Write-Warning "AGENT_DIR not set, using $AgentDir"
}

$Tasks = @(
    @{
        Name = "{{AGENT_NAME}}-cron"
        Description = "{{AGENT_NAME}} Cron Runner"
        Script = "scripts\{{AGENT_NAME_LOWER}}_cron.py"
        Log = "logs\cron.stdout.log"
        ErrLog = "logs\cron.stderr.log"
    },
    @{
        Name = "{{AGENT_NAME}}-discord-bot"
        Description = "{{AGENT_NAME}} Discord Bot"
        Script = "scripts\discord_bot.py"
        Log = "logs\discord-bot.log"
        ErrLog = "logs\discord-bot.err.log"
    },
    @{
        Name = "{{AGENT_NAME}}-opencode"
        Description = "opencode Server ({{AGENT_NAME}})"
        Exec = "$OpenCodePath"
        Args = "serve --port 8642 --hostname 0.0.0.0 --print-logs"
        Log = "logs\opencode.stdout.log"
        ErrLog = "logs\opencode.stderr.log"
    }
)

foreach ($Task in $Tasks) {
    $Action = New-ScheduledTaskAction -Execute $PythonPath -Argument "$AgentDir\$($Task.Script)" -WorkingDirectory $AgentDir
    if ($Task.Exec) {
        $Action = New-ScheduledTaskAction -Execute $Task.Exec -Argument $Task.Args -WorkingDirectory $AgentDir
    }

    $Trigger = New-ScheduledTaskTrigger -AtStartup
    $Settings = New-ScheduledTaskSettingsSet -RestartCount 999 -RestartInterval (New-TimeSpan -Seconds 10) -StartWhenAvailable

    $Principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest

    Register-ScheduledTask -TaskName $Task.Name `
        -Action $Action `
        -Trigger $Trigger `
        -Settings $Settings `
        -Principal $Principal `
        -Description $Task.Description `
        -Force

    # Logging via Start-Transcript in the action itself
    Write-Host "Created task: $($Task.Name)"
}

Write-Host "`nDone. All {{AGENT_NAME}} services registered."
Write-Host "To check: Get-ScheduledTask -TaskName '{{AGENT_NAME}}-*'"
Write-Host "To remove: Unregister-ScheduledTask -TaskName '<name>' -Confirm:`$false"
