<#
.SYNOPSIS
    Executes Capture-WindowsVM.ps1 -DryRun on a non-Windows host by substituting the
    Windows-only calls, so the script's logic can be regression-tested anywhere.

.DESCRIPTION
    Runs on PowerShell 7+ on Linux or macOS. Mocks Get-CimInstance, Get-BitLockerVolume,
    Suspend/Resume-BitLocker, Get-ItemProperty, Get-Command, bcdedit and mountvol, patches
    out the elevation check, then dot-sources the real script with -DryRun.

    WHAT THIS PROVES: control flow, arithmetic, StrictMode compliance, manifest contents,
    and that the `finally` cleanup unmounts the EFI partition and resumes BitLocker on
    every exit path including a mid-preflight throw.

    WHAT IT DOES NOT PROVE: anything about actual Windows behaviour. VSS, the real
    mountvol/bcdedit/Disk2vhd, and Windows path semantics are all mocked. The
    destination-on-a-captured-volume check in particular cannot be exercised here,
    because a Linux path root is `/`, never a drive letter.

.PARAMETER Scenario
    Substring flags, combined freely:
      bios      legacy BIOS boot (default: UEFI)
      +bl       BitLocker active on C: (default: none)
      noefi     mountvol fails to letter the EFI System Partition
      smalldest destination has 9 GB free, tripping the space guard
    e.g. 'uefi-win11+bl', 'bios-plain', 'uefi-noefi-smalldest'

.PARAMETER Star
    Run the script with -Volumes '*' instead of the default 'auto'.

.EXAMPLE
    pwsh -File tests/Invoke-DryRunHarness.ps1 -Scenario uefi-win11+bl
#>

param(
    [string] $ScriptPath = (Join-Path (Split-Path $PSScriptRoot -Parent) 'Capture-WindowsVM.ps1'),
    [string] $OutRoot    = ([System.IO.Path]::GetTempPath()),
    [string] $Scenario   = 'uefi-win11+bl',
    [switch] $Star
)

$ErrorActionPreference = 'Stop'

$env:SystemDrive            = 'C:'
$env:COMPUTERNAME           = 'HARNESS-PC'
$env:PROCESSOR_ARCHITECTURE = 'AMD64'
$env:TEMP                   = $OutRoot

# ------------------------------------------------------------------- mocks --

function script:bcdedit {
    if ($Scenario -like '*bios*') { 'path   \Windows\system32\winload.exe' }
    else                          { 'path   \Windows\system32\winload.efi' }
}

function script:mountvol {
    param($Letter, $Flag)
    if ($Scenario -like '*noefi*') { $global:LASTEXITCODE = 1; return 'cannot find the path' }
    $global:LASTEXITCODE = 0; return ''
}

function script:Test-Path {
    param([Parameter(ValueFromPipeline = $true, Position = 0)] $Path, $PathType)
    switch -Regex ("$Path") {
        '^HKLM:'      { return $true }
        '^[A-Z]:\\?$' { return $false }      # no drive letters exist on this host
        default       { return (Microsoft.PowerShell.Management\Test-Path -LiteralPath "$Path" -ErrorAction SilentlyContinue) }
    }
}

function script:Get-CimInstance {
    param([Parameter(Position = 0)] $ClassName, $Filter)
    switch ($ClassName) {
        'Win32_OperatingSystem' { return [pscustomobject]@{ Caption = 'Microsoft Windows 11 Pro' } }
        'Win32_ComputerSystem'  { return [pscustomobject]@{ NumberOfLogicalProcessors = 16
                                                            TotalPhysicalMemory       = 34359738368 } }
        'SoftwareLicensingProduct' { return [pscustomobject]@{ Description = 'Windows(R) Operating System, OEM_DM channel' } }
        'Win32_LogicalDisk' {
            if ($Filter -eq 'DriveType=3') {
                return @(
                    [pscustomobject]@{ DeviceID = 'C:'; Size = 1000204886016; FreeSpace = 412316860416 },
                    [pscustomobject]@{ DeviceID = 'D:'; Size = 2000398934016; FreeSpace = 1800000000000 }
                )
            }
            if ($Filter -match "DeviceID='C:'") {
                return [pscustomobject]@{ DeviceID = 'C:'; Size = 1000204886016; FreeSpace = 412316860416 }
            }
            if ($Filter -match "DeviceID='S:'") { return $null }   # EFI has no logical-disk entry
            if ($Scenario -like '*smalldest*') {
                return [pscustomobject]@{ DeviceID = 'E:'; Size = 128000000000; FreeSpace = 10000000000 }
            }
            return [pscustomobject]@{ DeviceID = 'E:'; Size = 4000787030016; FreeSpace = 3500000000000 }
        }
    }
}

function script:Get-ItemProperty {
    param([Parameter(Position = 0)] $Path)
    return [pscustomobject]@{ CurrentBuild = '22631' }
}

function script:Get-BitLockerVolume {
    if ($Scenario -like '*+bl*') { return @([pscustomobject]@{ MountPoint = 'C:'; ProtectionStatus = 'On' }) }
    return @()
}

$script:SuspendCalls = @(); $script:ResumeCalls = @()
function script:Suspend-BitLocker { param($MountPoint, $RebootCount)
    $script:SuspendCalls += "$MountPoint(RebootCount=$RebootCount)"; return $null }
function script:Resume-BitLocker  { param($MountPoint)
    $script:ResumeCalls += $MountPoint; return $null }

function script:Get-Command {
    [CmdletBinding()]
    param([Parameter(ValueFromRemainingArguments = $true)] $Name)
    return [pscustomobject]@{ Source = 'C:\Sysinternals\disk2vhd64.exe' }
}

function script:Start-Process { throw 'Start-Process must NOT be called during -DryRun' }

# --------------------------------------------------------------- patch + run --

$src     = Get-Content $ScriptPath -Raw
$patched = $src -replace '(?s)function Test-Elevated \{.*?\n\}', 'function Test-Elevated { $true }'
if ($patched -eq $src) { throw 'harness: failed to patch out the elevation check' }

$tmp  = Join-Path $OutRoot 'Capture-Patched.ps1'
$dest = Join-Path $OutRoot ('p2v-' + [guid]::NewGuid().ToString('N').Substring(0, 8))
Set-Content -Path $tmp -Value $patched -Encoding UTF8

$threw = $null
try {
    if ($Star) { . $tmp -OutputPath $dest -Volumes '*' -DryRun }
    else       { . $tmp -OutputPath $dest -DryRun }
} catch {
    $threw = $_.Exception.Message
}

# ------------------------------------------------------------- assertions ----

Write-Host "`n--- harness result ---" -ForegroundColor Magenta
Write-Host ("scenario                : {0}{1}" -f $Scenario, $(if ($Star) { " -Volumes '*'" } else { '' }))
Write-Host ("script threw            : {0}" -f $(if ($threw) { $threw } else { 'no' }))

$leaks = @()
if ($script:AssignedEfiLetter) { $leaks += "EFI still lettered as $($script:AssignedEfiLetter):" }
if ($script:SuspendCalls.Count -ne $script:ResumeCalls.Count) { $leaks += 'BitLocker suspended but not resumed' }

Write-Host ("suspend / resume calls  : [{0}] / [{1}]" -f ($script:SuspendCalls -join ','), ($script:ResumeCalls -join ','))
if ($leaks.Count -gt 0) {
    Write-Host ("STATE LEAKED            : {0}" -f ($leaks -join '; ')) -ForegroundColor Red
} else {
    Write-Host 'state leaked            : none' -ForegroundColor Green
}

$mf = Get-ChildItem $dest -Filter 'manifest-*.json' -ErrorAction SilentlyContinue | Select-Object -First 1
if ($mf) {
    Write-Host "`n--- manifest ---" -ForegroundColor Magenta
    Get-Content $mf.FullName -Raw
} elseif (-not $threw) {
    Write-Host 'NO MANIFEST WRITTEN on a successful run' -ForegroundColor Red
}

Remove-Item $dest -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item $tmp -Force -ErrorAction SilentlyContinue
if ($leaks.Count -gt 0) { exit 1 }
