$ErrorActionPreference = 'Stop'
$numberExe = Join-Path $PSScriptRoot 'dist\NumberTool\NumberTool.exe'
if (-not (Test-Path -LiteralPath $numberExe)) { throw '没有找到NumberTool.exe' }
$numberDesktop = [Environment]::GetFolderPath('Desktop')
$numberLinkPath = Join-Path $numberDesktop '随机号码分组工具 2.0.lnk'
if (Test-Path -LiteralPath $numberLinkPath) { Write-Output "快捷方式已存在，保留：$numberLinkPath"; exit 0 }
$numberLinkShell = New-Object -ComObject WScript.Shell
$numberLink = $numberLinkShell.CreateShortcut($numberLinkPath)
$numberLink.TargetPath = $numberExe
$numberData = Join-Path $PSScriptRoot 'data'
$numberLink.Arguments = 'gui --data-dir "{0}"' -f $numberData
$numberLink.WorkingDirectory = $PSScriptRoot
$numberLink.Description = '随机号码分组工具 2.0'
$numberLink.WindowStyle = 1
$numberLink.Save()
Write-Output "已创建：$numberLinkPath"
