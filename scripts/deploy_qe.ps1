param(
    [string]$Distribution = "Ubuntu-22.04",
    [string]$Uv = "uv",
    [string]$RuntimeBase = "",
    [string]$ApplicationEnvironment = "",
    [string]$BubblewrapDirectory = ""
)
$ErrorActionPreference = "Stop"
# Windows physical reserves must pass before WSL startup or any package action.
if ((Get-PSDrive C).Free -lt 5GB) {
    throw "QE setup blocked: restore at least 5 GiB free on Windows C before starting WSL."
}
$distributionRecord = Get-ChildItem 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Lxss' |
    ForEach-Object { Get-ItemProperty $_.PSPath } |
    Where-Object DistributionName -EQ $Distribution | Select-Object -First 1
if (-not $distributionRecord) { throw "The selected existing WSL distribution was not found." }
$backingPath = $distributionRecord.BasePath
if ($backingPath.StartsWith('\\?\')) { $backingPath = $backingPath.Substring(4) }
$backingDrive = [IO.Path]::GetPathRoot($backingPath).TrimEnd('\').TrimEnd(':')
if (-not $backingDrive -or (Get-PSDrive $backingDrive).Free -lt 3GB) {
    throw "QE setup blocked: the WSL backing volume needs at least 3 GiB free."
}
$project = Split-Path -Parent $PSScriptRoot
$linuxProject = (& wsl.exe -d $Distribution --exec wslpath -a $project).Trim()
if ($LASTEXITCODE -ne 0) { throw "Cannot access the existing WSL distribution" }
$arguments = @()
if ($ApplicationEnvironment) {
    $arguments += @("env", "UV_PROJECT_ENVIRONMENT=$ApplicationEnvironment")
}
$arguments += @("/bin/bash", "$linuxProject/skills/quantum-espresso/scripts/deploy.sh",
    "--project-root", $linuxProject, "--uv", $Uv)
if ($RuntimeBase) { $arguments += @("--runtime-base", $RuntimeBase) }
if ($BubblewrapDirectory) { $arguments += @("--bubblewrap-dir", $BubblewrapDirectory) }
& wsl.exe -d $Distribution --exec @arguments
if ($LASTEXITCODE -ne 0) { throw "QE deployment failed; inspect installer diagnostics" }
