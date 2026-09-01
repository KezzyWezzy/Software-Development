<#
.SYNOPSIS
    Downloads the Proxmox VE installer ISO, verifies its SHA256, and writes it to a USB
    stick in DD (raw image) mode.

.DESCRIPTION
    The Proxmox VE ISO is a hybrid image that must be written raw, sector for sector. Copying
    the files onto a FAT32 stick does not produce a bootable installer, and Rufus's default
    "ISO mode" rewrites the boot layout in a way the PVE installer does not survive - which is
    the single most common reason a Proxmox stick fails to boot.

    THIS SCRIPT DESTROYS EVERYTHING ON THE TARGET DISK. It therefore refuses to run against
    anything that does not look like a USB stick, and makes you type the disk's model name
    before it writes.

.PARAMETER DriveLetter
    Drive letter of the USB stick, e.g. 'D'. Resolved to a physical disk number up front,
    before the partition table is wiped.

.PARAMETER DiskNumber
    Target the physical disk directly instead of by letter. Use this when the stick has no
    letter (already wiped, or an aborted previous run).

.PARAMETER WorkDir
    Where to download the ISO. Defaults to the user's Downloads folder. Needs ~1.7 GB.
    Must NOT be on the USB stick.

.PARAMETER IsoPath
    Use an ISO you already have instead of downloading. Still SHA256-verified.

.PARAMETER Force
    Bypass the "this doesn't look like a USB stick" and "this disk is suspiciously large"
    guards. The typed confirmation is still required. Think before using this.

.PARAMETER WhatIf
    Run every check and the download, report the exact disk that would be written, and stop
    without writing a byte.

.EXAMPLE
    .\New-ProxmoxInstallUsb.ps1 -DriveLetter D -WhatIf
    .\New-ProxmoxInstallUsb.ps1 -DriveLetter D

.NOTES
    Elevated PowerShell required. 8 GB stick or larger.

    If the raw write fails on your system, Rufus is the reliable fallback - select the ISO,
    and when Rufus asks, choose **DD Image mode**, not ISO mode.
#>

[CmdletBinding(SupportsShouldProcess = $true, ConfirmImpact = 'High')]
param(
    [Parameter(ParameterSetName = 'ByLetter')]
    [ValidatePattern('^[A-Za-z]$')]
    [string] $DriveLetter = 'D',

    [Parameter(ParameterSetName = 'ByDisk', Mandatory = $true)]
    [int] $DiskNumber,

    [string] $WorkDir,

    [string] $IsoPath,

    [switch] $Force
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

# Proxmox VE 9.2-1, released 2026-05-21. Checksum taken from
# https://enterprise.proxmox.com/iso/SHA256SUMS - note the arm64 ISO is a DIFFERENT file.
$IsoName   = 'proxmox-ve_9.2-1.iso'
$IsoUrl    = "https://enterprise.proxmox.com/iso/$IsoName"
$IsoSha256 = '4e88fe416df9b527624a175f24c9aa07c714d3332afb1ee3dbf3879573ef2c6c'

# A USB installer stick is small. An internal data disk is not. Refuse anything above this
# without -Force, because the cost of a wrong target here is somebody's whole drive.
$MaxSaneUsbBytes = 512GB
$MinUsbBytes     = 4GB

function Write-Step { param($m) Write-Host "`n==> $m" -ForegroundColor Cyan }
function Write-Ok   { param($m) Write-Host "    [ok]   $m" -ForegroundColor Green }
function Write-Warn { param($m) Write-Host "    [warn] $m" -ForegroundColor Yellow }
function Write-Info { param($m) Write-Host "    $m" -ForegroundColor Gray }

function Test-Elevated {
    $id = [Security.Principal.WindowsIdentity]::GetCurrent()
    (New-Object Security.Principal.WindowsPrincipal $id).IsInRole(
        [Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Format-Bytes {
    param([double] $Bytes)
    if ($Bytes -ge 1TB) { return ('{0:N1} TB' -f ($Bytes / 1TB)) }
    if ($Bytes -ge 1GB) { return ('{0:N1} GB' -f ($Bytes / 1GB)) }
    return ('{0:N1} MB' -f ($Bytes / 1MB))
}

# ------------------------------------------------------------------ preflight --

Write-Step 'Preflight'

if (-not (Test-Elevated)) {
    throw 'Run this from an elevated PowerShell prompt (Run as Administrator).'
}
Write-Ok 'Running elevated'

# Resolve the target disk BEFORE anything wipes the partition table - once the disk is
# cleared the drive letter is gone, and re-resolving by letter would find the wrong disk.
if ($PSCmdlet.ParameterSetName -eq 'ByLetter') {
    $letter = $DriveLetter.ToUpperInvariant()
    try {
        $part = Get-Partition -DriveLetter $letter -ErrorAction Stop
    } catch {
        throw ("No volume is mounted at ${letter}:. Plug the stick in, or pass -DiskNumber " +
               "if it has no letter. 'Get-Disk' lists the disks.")
    }
    $DiskNumber = $part.DiskNumber
    Write-Ok "${letter}: is on physical disk $DiskNumber"
}

$disk = Get-Disk -Number $DiskNumber -ErrorAction Stop

Write-Step 'Target disk'
Write-Host ''
Write-Host ("    Disk number   : {0}" -f $disk.Number)
Write-Host ("    Model         : {0}" -f $disk.FriendlyName)
Write-Host ("    Serial        : {0}" -f $disk.SerialNumber)
Write-Host ("    Size          : {0}" -f (Format-Bytes $disk.Size))
Write-Host ("    Bus type      : {0}" -f $disk.BusType)
Write-Host ("    Removable     : {0}" -f $(if ($disk.BusType -eq 'USB') { 'yes (USB)' } else { 'NO' }))
Write-Host ''

$volumes = Get-Partition -DiskNumber $DiskNumber -ErrorAction SilentlyContinue |
           Where-Object { $_.DriveLetter } |
           ForEach-Object {
               $v = Get-Volume -DriveLetter $_.DriveLetter -ErrorAction SilentlyContinue
               '{0}: {1} ({2} of {3} free)' -f $_.DriveLetter,
                   $(if ($v -and $v.FileSystemLabel) { $v.FileSystemLabel } else { 'no label' }),
                   $(if ($v) { Format-Bytes $v.SizeRemaining } else { '?' }),
                   $(if ($v) { Format-Bytes $v.Size } else { '?' })
           }
if ($volumes) {
    Write-Host '    Volumes that will be DESTROYED:' -ForegroundColor Red
    $volumes | ForEach-Object { Write-Host "      $_" -ForegroundColor Red }
} else {
    Write-Info 'No lettered volumes on this disk.'
}
Write-Host ''

# ---------------------------------------------------------------- safety gates --

if ($disk.BusType -ne 'USB') {
    $msg = ("Disk $DiskNumber is on the $($disk.BusType) bus, not USB. This looks like an " +
            "internal drive, not a USB stick. Refusing.")
    if (-not $Force) { throw "$msg Pass -Force only if you are certain." }
    Write-Warn "$msg -Force given, continuing."
}

if ($disk.Size -gt $MaxSaneUsbBytes) {
    $msg = ("Disk $DiskNumber is $(Format-Bytes $disk.Size), larger than the " +
            "$(Format-Bytes $MaxSaneUsbBytes) sanity limit for a USB installer stick.")
    if (-not $Force) { throw "$msg Refusing. Pass -Force only if you are certain." }
    Write-Warn "$msg -Force given, continuing."
}

if ($disk.Size -lt $MinUsbBytes) {
    throw ("Disk $DiskNumber is only $(Format-Bytes $disk.Size). The Proxmox ISO needs a " +
           "stick of at least $(Format-Bytes $MinUsbBytes); 8 GB or more is recommended.")
}

if ($disk.IsBoot -or $disk.IsSystem) {
    throw "Disk $DiskNumber is the boot/system disk. Refusing outright - -Force will not override this."
}
Write-Ok 'Safety checks passed'

# --------------------------------------------------------------------- the ISO --

if (-not $WorkDir) { $WorkDir = Join-Path $env:USERPROFILE 'Downloads' }
if (-not (Test-Path $WorkDir)) { New-Item -ItemType Directory -Path $WorkDir -Force | Out-Null }
$WorkDir = (Resolve-Path $WorkDir).Path

$workDisk = $null
try {
    $workDisk = (Get-Partition -DriveLetter $WorkDir.Substring(0,1) -ErrorAction Stop).DiskNumber
} catch { }
if ($null -ne $workDisk -and $workDisk -eq $DiskNumber) {
    throw "WorkDir '$WorkDir' is on the disk being wiped. Pass -WorkDir somewhere else."
}

if (-not $IsoPath) { $IsoPath = Join-Path $WorkDir $IsoName }

Write-Step 'Proxmox VE ISO'
if (Test-Path $IsoPath) {
    Write-Ok "Already present: $IsoPath ($(Format-Bytes (Get-Item $IsoPath).Length))"
} else {
    Write-Info "Downloading $IsoUrl"
    Write-Info 'About 1.7 GB.'
    try {
        Import-Module BitsTransfer -ErrorAction Stop
        Start-BitsTransfer -Source $IsoUrl -Destination $IsoPath -Description 'Proxmox VE ISO'
    } catch {
        Write-Warn "BITS unavailable ($($_.Exception.Message)); falling back to Invoke-WebRequest."
        $progress = $ProgressPreference
        $ProgressPreference = 'SilentlyContinue'   # the progress bar makes IWR crawl
        try   { Invoke-WebRequest -Uri $IsoUrl -OutFile $IsoPath -UseBasicParsing }
        finally { $ProgressPreference = $progress }
    }
    Write-Ok "Downloaded to $IsoPath"
}

Write-Info 'Verifying SHA256 (takes a moment on 1.7 GB)...'
$actual = (Get-FileHash -Path $IsoPath -Algorithm SHA256).Hash
if ($actual -ne $IsoSha256.ToUpperInvariant()) {
    throw ("SHA256 MISMATCH - not writing this to a disk.`n" +
           "  expected $($IsoSha256.ToUpperInvariant())`n" +
           "  got      $actual`n" +
           "Delete '$IsoPath' and re-run. If it mismatches again, the published checksum has " +
           "moved on to a newer release; update `$IsoSha256 from " +
           "https://enterprise.proxmox.com/iso/SHA256SUMS")
}
Write-Ok "SHA256 verified: $actual"

$isoSize = (Get-Item $IsoPath).Length
if ($isoSize -gt $disk.Size) {
    throw "ISO is $(Format-Bytes $isoSize) but the stick is only $(Format-Bytes $disk.Size)."
}

# ---------------------------------------------------------------- confirmation --

$target = "physical disk $DiskNumber - $($disk.FriendlyName), $(Format-Bytes $disk.Size)"

if (-not $PSCmdlet.ShouldProcess($target, 'ERASE COMPLETELY and write the Proxmox VE installer')) {
    Write-Step 'Stopped before writing (-WhatIf)'
    Write-Info "Would have written $IsoPath to $target"
    return
}

Write-Step 'Point of no return'
Write-Host "    Everything on $target will be destroyed." -ForegroundColor Red
$expect = $disk.FriendlyName.Trim()
Write-Host "    Type the disk model exactly to confirm: " -NoNewline -ForegroundColor Yellow
Write-Host $expect -ForegroundColor White
$typed = Read-Host '    >'
if ($typed.Trim() -ne $expect) {
    throw "Confirmation did not match ('$typed' != '$expect'). Nothing was written."
}

# ----------------------------------------------------------------- the write ---

Write-Step 'Writing'

# Clear-Disk drops the partition table, which releases the volume locks that would otherwise
# make the raw handle fail with access-denied. Offline keeps Windows from re-mounting mid-write.
Clear-Disk -Number $DiskNumber -RemoveData -RemoveOEM -Confirm:$false
Set-Disk   -Number $DiskNumber -IsOffline $true
Write-Ok 'Disk cleared and taken offline'

$src = $null; $dst = $null
$sw  = [System.Diagnostics.Stopwatch]::StartNew()
try {
    $src = [System.IO.File]::Open($IsoPath, 'Open', 'Read', 'Read')
    $dst = New-Object System.IO.FileStream("\\.\PhysicalDrive$DiskNumber",
              [System.IO.FileMode]::Open, [System.IO.FileAccess]::Write,
              [System.IO.FileShare]::None)

    $bufSize = 4MB
    $buf     = New-Object byte[] $bufSize
    $written = 0L
    $lastPct = -1

    while (($read = $src.Read($buf, 0, $bufSize)) -gt 0) {
        # Raw device writes must be a whole number of sectors; pad the final short read.
        $chunk = $read
        if ($chunk % 512 -ne 0) {
            $pad = 512 - ($chunk % 512)
            [Array]::Clear($buf, $chunk, $pad)
            $chunk += $pad
        }
        $dst.Write($buf, 0, $chunk)
        $written += $read
        $pct = [int](($written / $isoSize) * 100)
        if ($pct -ne $lastPct) {
            Write-Progress -Activity 'Writing Proxmox VE installer' `
                           -Status ("{0} of {1}" -f (Format-Bytes $written), (Format-Bytes $isoSize)) `
                           -PercentComplete $pct
            $lastPct = $pct
        }
    }
    $dst.Flush()
    Write-Progress -Activity 'Writing Proxmox VE installer' -Completed
    $sw.Stop()
    Write-Ok ("Wrote {0} in {1:mm\:ss} ({2:N1} MB/s)" -f (Format-Bytes $written), $sw.Elapsed,
              (($written / 1MB) / [Math]::Max($sw.Elapsed.TotalSeconds, 1)))
}
finally {
    if ($dst) { $dst.Dispose() }
    if ($src) { $src.Dispose() }
    Set-Disk -Number $DiskNumber -IsOffline $false -ErrorAction SilentlyContinue
}

Write-Step 'Done'
Write-Info 'Windows will likely offer to format the stick. DECLINE - it cannot read the'
Write-Info 'installer partition, and formatting would undo the write.'
Write-Info ''
Write-Info 'Boot the target machine from this stick in UEFI mode, with VT-x/AMD-V enabled.'
Write-Info 'If it does not appear as a boot option, disable Secure Boot on the Proxmox host.'
