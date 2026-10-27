param([string]$TestRoot = $env:TEMP)
$ErrorActionPreference = 'Stop'
# Isolated command doubles only; never starts WSL or installs anything.
$source = Join-Path (Split-Path -Parent $PSScriptRoot) 'scripts\deploy_qe.ps1'
$temporary = Join-Path $TestRoot ('qe-wrapper-' + [Guid]::NewGuid().ToString('N'))
$scriptDirectory = Join-Path $temporary 'project with spaces\scripts'
New-Item -ItemType Directory -Path $scriptDirectory -Force | Out-Null
$entry = Join-Path $scriptDirectory 'deploy_qe.ps1'
Copy-Item -LiteralPath $source -Destination $entry
$global:qeWrapperScenario = ''
$global:qeWrapperCalls = @()
function Get-Command { param($Name, $ErrorAction) if ($global:qeWrapperScenario -ne 'missing-wsl') { [pscustomobject]@{Name=$Name} } }
function Test-Path { param($LiteralPath) $global:qeWrapperScenario -ne 'no-distributions' }
function Get-PSDrive { param($Name) [pscustomobject]@{Free=$(if ($global:qeWrapperScenario -eq 'low-disk') { 1GB } else { 100GB })} }
function Get-ChildItem { param($LiteralPath) [pscustomobject]@{PSPath='mock-registry'} }
function Get-ItemProperty {
    param($Path)
    [pscustomobject]@{
        DistributionName=$(if ($global:qeWrapperScenario -eq 'wrong-distribution') {'Other'} else {'Test Linux'})
        Version=$(if ($global:qeWrapperScenario -eq 'wsl1') {1} else {2})
        BasePath='D:\mock-wsl'
    }
}
function wsl.exe {
    $global:qeWrapperCalls += ,$args
    $global:LASTEXITCODE = 0
    if ($args -contains 'wslpath') { '/mnt/d/project with spaces' }
}
$results = @()
foreach ($item in @(
    @('missing-wsl', 'Missing WSL'),
    @('no-distributions', 'No WSL distributions'),
    @('wrong-distribution', '-Distribution'),
    @('wsl1', 'requires an existing WSL2'),
    @('low-disk', '5 GiB')
)) {
    $global:qeWrapperScenario = $item[0]
    $global:qeWrapperCalls = @()
    $message = ''
    try { & $entry -Distribution 'Test Linux' } catch { $message = $_.Exception.Message }
    if (-not $message.Contains($item[1])) { throw "Wrong diagnostic for $($item[0]): $message" }
    if ($global:qeWrapperCalls.Count -ne 0) { throw "WSL started after failed prerequisite: $($item[0])" }
    $results += [pscustomobject]@{test=$item[0];passed=$true;diagnostic=$message;wsl_calls=0}
}
$global:qeWrapperScenario = 'success'
$global:qeWrapperCalls = @()
& $entry -Distribution 'Test Linux' -Uv '/tools with spaces/uv' -ApplicationEnvironment '/app with spaces' -RuntimeBase '/runtime with spaces' -BubblewrapDirectory '/bubblewrap with spaces'
if ($global:qeWrapperCalls.Count -ne 2) { throw 'Expected path conversion and deployment only' }
$actual = $global:qeWrapperCalls[1]
foreach ($expected in @('UV_PROJECT_ENVIRONMENT=/app with spaces', '/mnt/d/project with spaces/skills/quantum-espresso/scripts/deploy.sh', '/tools with spaces/uv', '/runtime with spaces', '/bubblewrap with spaces')) {
    if ($actual -notcontains $expected) { throw "Lost argument boundary: $expected" }
}
$results += [pscustomobject]@{test='success-space-paths';passed=$true;wsl_calls=2}
$results | ConvertTo-Json -Depth 5
