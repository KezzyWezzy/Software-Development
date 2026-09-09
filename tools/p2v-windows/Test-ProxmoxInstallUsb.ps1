<#
.SYNOPSIS
    Verifies that a USB stick actually contains the Proxmox VE installer image, by
    comparing the physical disk against the ISO byte for byte.

.DESCRIPTION
    New-ProxmoxInstallUsb.ps1 writes the ISO raw. Windows cannot read the resulting
    filesystem, so "did it work?" is not answerable from Explorer or Get-Partition -
    a disk that was cleared but never written and a disk that was written correctly
    can look identical there (MBR, no enumerable partitions).

    This reads the raw device and compares it to the ISO. It writes nothing.

.PARAMETER DiskNumber
    Physical disk to verify. After a raw write the stick usually has no drive letter,
    so this is the normal way to name it. 'Get-Disk' lists them.

.PARAMETER DriveLetter
    Verify whatever disk this letter lives on, if the stick still has one.

.PARAMETER IsoPath
    ISO to compare against. Defaults to proxmox-ve_9.2-1.iso in Downloads.

.PARAMETER Full
    Compare the whole ISO. The default compares the first 64 MB, which is enough to
    catch a failed or partial write; -Full catches truncation and mid-write corruption.

.EXAMPLE
    .\Test-ProxmoxInstallUsb.ps1 -DiskNumber 1
    .\Test-ProxmoxInstallUsb.ps1 -DiskNumber 1 -Full

.NOTES
    Elevated PowerShell required - opening \\.\PhysicalDriveN needs administrator.
#>

[CmdletBinding(DefaultParameterSetName = 'ByDisk')]
param(
    [Parameter(ParameterSetName = 'ByDisk', Mandatory = $true)]
    [int] $DiskNumber,

    [Parameter(ParameterSetName = 'ByLetter', Mandatory = $true)]
    [ValidatePattern('^[A-Za-z]$')]
    [string] $DriveLetter,

    [string] $IsoPath,

    [switch] $Full
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

function Write-Step { param($m) Write-Host "`n==> $m" -ForegroundColor Cyan }
function Write-Ok   { param($m) Write-Host "    [ok]   $m" -ForegroundColor Green }
function Write-Bad  { param($m) Write-Host "    [FAIL] $m" -ForegroundColor Red }
function Write-Info { param($m) Write-Host "    $m" -ForegroundColor Gray }

function Format-Bytes {
    param([double] $Bytes)
    if ($Bytes -ge 1GB) { return ('{0:N2} GB' -f ($Bytes / 1GB)) }
    if ($Bytes -ge 1MB) { return ('{0:N1} MB' -f ($Bytes / 1MB)) }
    return ('{0:N0} bytes' -f $Bytes)
}

$id = [Security.Principal.WindowsIdentity]::GetCurrent()
if (-not (New-Object Security.Principal.WindowsPrincipal $id).IsInRole(
          [Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'Run this from an elevated PowerShell prompt - reading \\.\PhysicalDriveN needs administrator.'
}

if ($PSCmdlet.ParameterSetName -eq 'ByLetter') {
    $letter = $DriveLetter.ToUpperInvariant()
    try   { $DiskNumber = (Get-Partition -DriveLetter $letter -ErrorAction Stop).DiskNumber }
    catch { throw "No volume at ${letter}:. After a raw write the stick normally has no letter - pass -DiskNumber instead." }
}

if (-not $IsoPath) { $IsoPath = Join-Path $env:USERPROFILE 'Downloads\proxmox-ve_9.2-1.iso' }
if (-not (Test-Path $IsoPath)) { throw "ISO not found: $IsoPath" }

$disk    = Get-Disk -Number $DiskNumber -ErrorAction Stop
$isoSize = (Get-Item $IsoPath).Length

Write-Step 'Verifying'
Write-Info ("Disk {0} : {1} ({2}, {3})" -f $disk.Number, $disk.FriendlyName,
            (Format-Bytes $disk.Size), $disk.BusType)
Write-Info ("ISO     : {0} ({1})" -f $IsoPath, (Format-Bytes $isoSize))

$src = $null; $dev = $null
$failed = $false
try {
    $src = [System.IO.File]::Open($IsoPath, 'Open', 'Read', 'Read')
    # ReadWrite share: the volume may still be claimed by the system.
    $dev = New-Object System.IO.FileStream("\\.\PhysicalDrive$DiskNumber",
              [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read,
              [System.IO.FileShare]::ReadWrite)

    # -- signatures, the cheap tell -------------------------------------------
    $sector = New-Object byte[] 512
    $null = $dev.Read($sector, 0, 512)
    $bootSig = '{0:X2}{1:X2}' -f $sector[510], $sector[511]
    if ($bootSig -eq '55AA') { Write-Ok "Boot signature present (0x55AA)" }
    else                     { Write-Bad "No boot signature in sector 0 (got 0x$bootSig)"; $failed = $true }

    # ISO9660 primary volume descriptor lives at offset 0x8001.
    $null = $dev.Seek(32768, [System.IO.SeekOrigin]::Begin)
    $pvd = New-Object byte[] 8
    $null = $dev.Read($pvd, 0, 8)
    $isoSig = [System.Text.Encoding]::ASCII.GetString($pvd, 1, 5)
    if ($isoSig -eq 'CD001') { Write-Ok "ISO9660 descriptor present ('CD001')" }
    else                     { Write-Bad "No ISO9660 descriptor at 0x8001 (got '$isoSig') - the image is not on this disk"; $failed = $true }

    # -- byte-for-byte compare -------------------------------------------------
    $limit = if ($Full) { $isoSize } else { [Math]::Min(64MB, $isoSize) }
    Write-Info ("Comparing {0}{1}..." -f (Format-Bytes $limit), $(if ($Full) { '' } else { ' (pass -Full for the whole image)' }))

    # Everything below this offset is partition metadata - protective MBR, GPT header,
    # GPT entry array. Windows REWRITES it the moment the stick comes back online, to
    # make the backup-LBA and last-usable-LBA span the physical device instead of the
    # 1.7 GB image. On a good 28.9 GB write that is ~500 bytes of legitimate difference,
    # so comparing it byte-for-byte reports a perfect stick as corrupt. The image proper
    # starts at the ISO9660 primary volume descriptor at 0x8000, and from there on any
    # difference is real. Metadata differences are counted and reported, not failed.
    $MetadataBytes = 32768

    $null = $src.Seek(0, [System.IO.SeekOrigin]::Begin)
    $null = $dev.Seek(0, [System.IO.SeekOrigin]::Begin)

    $bufSize = 4MB
    $a = New-Object byte[] $bufSize
    $b = New-Object byte[] $bufSize
    $done = 0L
    $mismatchAt = -1L
    $metaDiff = 0L
    $sw = [System.Diagnostics.Stopwatch]::StartNew()

    while ($done -lt $limit -and $mismatchAt -lt 0) {
        $want = [int][Math]::Min([long]$bufSize, $limit - $done)

        # Raw device reads must be whole sectors; round the request up and only
        # compare the bytes the ISO actually has.
        $devWant = $want
        if ($devWant % 512 -ne 0) { $devWant += 512 - ($devWant % 512) }

        $ra = 0; while ($ra -lt $want)    { $n = $src.Read($a, $ra, $want - $ra);       if ($n -le 0) { break }; $ra += $n }
        $rb = 0; while ($rb -lt $devWant) { $n = $dev.Read($b, $rb, $devWant - $rb);    if ($n -le 0) { break }; $rb += $n }

        if ($ra -eq 0 -or $rb -eq 0) { break }
        $cmp = [Math]::Min($ra, $rb)

        for ($i = 0; $i -lt $cmp; $i++) {
            if ($a[$i] -ne $b[$i]) {
                $abs = $done + $i
                if ($abs -lt $MetadataBytes) { $metaDiff++ }   # expected; keep going
                else { $mismatchAt = $abs; break }
            }
        }
        $done += $cmp

        $pct = [int](($done / $limit) * 100)
        Write-Progress -Activity 'Comparing disk against ISO' `
                       -Status ("{0} of {1}" -f (Format-Bytes $done), (Format-Bytes $limit)) `
                       -PercentComplete $pct
    }
    Write-Progress -Activity 'Comparing disk against ISO' -Completed
    $sw.Stop()

    if ($mismatchAt -ge 0) {
        Write-Bad ("Image content differs at byte {0} ({1} in)" -f $mismatchAt, (Format-Bytes $mismatchAt))
        $failed = $true
    } else {
        Write-Ok ("{0} of image content identical to the ISO ({1:mm\:ss})" -f (Format-Bytes $done), $sw.Elapsed)
    }
    if ($metaDiff -gt 0) {
        Write-Info ("{0} bytes differ in the partition metadata below {1} - expected: Windows" -f $metaDiff, (Format-Bytes $MetadataBytes))
        Write-Info 'rewrites the GPT to span the whole stick when it remounts. Not corruption.'
    }
}
finally {
    if ($dev) { $dev.Dispose() }
    if ($src) { $src.Dispose() }
}

Write-Step 'Result'
if ($failed) {
    Write-Bad 'This stick will NOT boot the Proxmox installer.'
    Write-Info 'Re-run New-ProxmoxInstallUsb.ps1. If the raw write keeps failing, use Rufus'
    Write-Info 'and choose DD Image mode - not ISO mode.'
    exit 1
}
Write-Ok 'Verified - the installer image is on this stick.'
if (-not $Full) { Write-Info 'Only the first 64 MB was compared; -Full checks the whole image.' }
exit 0
