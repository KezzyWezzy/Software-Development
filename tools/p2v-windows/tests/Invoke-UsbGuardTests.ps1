<#
.SYNOPSIS
    Verifies that New-ProxmoxInstallUsb.ps1 refuses to write to the wrong disk.

.DESCRIPTION
    Runs on PowerShell 7+ on any OS. For each case it generates a small driver script with
    the fake disk's properties baked in, mocks Get-Disk / Get-Partition / Get-Volume /
    Get-FileHash and the elevation check, and runs the real script with -WhatIf.

    The write path itself is NOT exercised - -WhatIf returns before it. What this asserts is
    the target-selection and refusal logic, which is where a defect destroys somebody's data.

    Each case declares whether the script should REFUSE or PROCEED, and a refusal case also
    declares the substring its reason must contain - so a disk rejected for the wrong reason
    still counts as a failure.

.EXAMPLE
    pwsh -File tests/Invoke-UsbGuardTests.ps1
#>

param(
    [string] $ScriptPath = (Join-Path (Split-Path $PSScriptRoot -Parent) 'New-ProxmoxInstallUsb.ps1')
)

$ErrorActionPreference = 'Stop'
$ScriptPath = (Resolve-Path $ScriptPath).Path

$tmpDir  = [System.IO.Path]::GetTempPath()
$fakeIso = Join-Path $tmpDir 'fake-pve.iso'
Set-Content -Path $fakeIso -Value 'not a real iso' -NoNewline

$cases = @(
    @{ Name = 'genuine 32 GB USB stick'
       Num = 3; Model = 'SanDisk Ultra'; Size = '32GB'; Bus = 'USB'; Boot = '$false'
       Force = $false; Expect = 'PROCEED' }

    @{ Name = 'internal NVMe data drive'
       Num = 1; Model = 'Samsung 990 PRO'; Size = '2TB'; Bus = 'NVMe'; Boot = '$false'
       Force = $false; Expect = 'REFUSE'; Because = 'not USB' }

    @{ Name = 'internal SATA data drive'
       Num = 2; Model = 'WDC WD40EZAZ'; Size = '4TB'; Bus = 'SATA'; Boot = '$false'
       Force = $false; Expect = 'REFUSE'; Because = 'not USB' }

    @{ Name = 'boot disk, even with -Force'
       Num = 0; Model = 'Samsung 990 PRO'; Size = '1TB'; Bus = 'NVMe'; Boot = '$true'
       Force = $true; Expect = 'REFUSE'; Because = 'boot/system disk' }

    @{ Name = 'huge USB external drive'
       Num = 4; Model = 'Seagate Expansion'; Size = '8TB'; Bus = 'USB'; Boot = '$false'
       Force = $false; Expect = 'REFUSE'; Because = 'sanity limit' }

    @{ Name = 'huge USB external drive, with -Force'
       Num = 4; Model = 'Seagate Expansion'; Size = '8TB'; Bus = 'USB'; Boot = '$false'
       Force = $true; Expect = 'PROCEED' }

    @{ Name = '2 GB stick, too small'
       Num = 5; Model = 'Generic Flash'; Size = '2GB'; Bus = 'USB'; Boot = '$false'
       Force = $true; Expect = 'REFUSE'; Because = 'at least' }
)

$results = @()

foreach ($case in $cases) {

    $driver = @"
`$ErrorActionPreference = 'Stop'

`$global:FakeDisk = [pscustomobject]@{
    Number       = $($case.Num)
    FriendlyName = '$($case.Model)'
    SerialNumber = 'TESTSERIAL'
    Size         = $($case.Size)
    BusType      = '$($case.Bus)'
    IsBoot       = $($case.Boot)
    IsSystem     = $($case.Boot)
}

function global:Get-Disk {
    [CmdletBinding()] param([Parameter(Position=0)] `$Number)
    return `$global:FakeDisk
}

function global:Get-Partition {
    [CmdletBinding()] param(`$DriveLetter, `$DiskNumber)
    # Only a real A-Z letter maps to a partition. The WorkDir check passes a path root,
    # which on a non-Windows host is '/' - that must behave like "no such volume".
    if (`$DriveLetter -and "`$DriveLetter" -match '^[A-Za-z]`$') {
        return [pscustomobject]@{ DiskNumber = `$global:FakeDisk.Number; DriveLetter = `$DriveLetter }
    }
    if (`$null -ne `$DiskNumber) { return @() }
    throw 'no volume mounted'
}

function global:Get-Volume {
    [CmdletBinding()] param(`$DriveLetter)
    return [pscustomobject]@{ FileSystemLabel = 'DATA'
                              Size = `$global:FakeDisk.Size
                              SizeRemaining = `$global:FakeDisk.Size }
}

function global:Get-FileHash {
    [CmdletBinding()] param(`$Path, `$Algorithm)
    return [pscustomobject]@{ Hash = '4E88FE416DF9B527624A175F24C9AA07C714D3332AFB1EE3DBF3879573EF2C6C' }
}

# Patch out the .NET elevation check, which throws on non-Windows.
`$src = Get-Content '$ScriptPath' -Raw
`$src = `$src -replace '(?s)function Test-Elevated \{.*?\n\}', 'function Test-Elevated { `$true }'
`$patched = Join-Path '$tmpDir' 'usbguard-patched.ps1'
Set-Content -Path `$patched -Value `$src -Encoding UTF8

`$splat = @{
    DiskNumber = $($case.Num)
    IsoPath    = '$fakeIso'
    WorkDir    = '$tmpDir'
    WhatIf     = `$true
}
$(if ($case.Force) { "`$splat['Force'] = `$true" })

try   { & `$patched @splat | Out-Null; Write-Output 'VERDICT=PROCEED' }
catch { Write-Output ('VERDICT=REFUSE: ' + `$_.Exception.Message.Replace("``n", ' ')) }
"@

    $driverFile = Join-Path $tmpDir ('usbguard-driver-{0}.ps1' -f [guid]::NewGuid().ToString('N').Substring(0,6))
    Set-Content -Path $driverFile -Value $driver -Encoding UTF8

    $out  = & pwsh -NoProfile -File $driverFile 2>&1 | Out-String
    $line = ($out -split "`n" | Where-Object { $_ -match '^VERDICT=' } | Select-Object -First 1)

    Remove-Item $driverFile -Force -ErrorAction SilentlyContinue

    if (-not $line) {
        $results += [pscustomobject]@{ Case = $case.Name; Expected = $case.Expect
                                       Actual = 'NO VERDICT'; Pass = $false
                                       Reason = ($out -split "`n" | Select-Object -Last 3) -join ' ' }
        continue
    }

    $actual = if ($line -match '^VERDICT=PROCEED') { 'PROCEED' } else { 'REFUSE' }
    $reason = if ($line -match '^VERDICT=REFUSE: (.*)$') { $Matches[1].Trim() } else { '' }

    $pass = $actual -eq $case.Expect
    if ($pass -and $case.Expect -eq 'REFUSE') {
        $pass = $reason -match [regex]::Escape($case.Because)
    }

    $results += [pscustomobject]@{
        Case     = $case.Name
        Expected = $case.Expect
        Actual   = $actual
        Pass     = $pass
        Reason   = if ($reason.Length -gt 62) { $reason.Substring(0, 62) + '...' } else { $reason }
    }
}

Write-Host ''
# Explicit formatting rather than Format-Table: Format-* renders nothing when there is no
# console width to measure, which silently hides the whole report in CI and in pipes.
Write-Host ('{0,-38} {1,-8} {2,-10} {3,-5}  {4}' -f 'CASE', 'EXPECT', 'ACTUAL', 'PASS', 'REASON')
Write-Host ('-' * 110)
foreach ($r in $results) {
    $color = if ($r.Pass) { 'Green' } else { 'Red' }
    Write-Host ('{0,-38} {1,-8} {2,-10} {3,-5}  {4}' -f
                $r.Case, $r.Expected, $r.Actual, $(if ($r.Pass) { 'yes' } else { 'NO' }), $r.Reason) `
               -ForegroundColor $color
}
Write-Host ''

$failed = @($results | Where-Object { -not $_.Pass })
if ($failed.Count -gt 0) {
    Write-Host "$($failed.Count) of $($results.Count) guard tests FAILED" -ForegroundColor Red
    exit 1
}
Write-Host "all $($results.Count) guard tests passed" -ForegroundColor Green
