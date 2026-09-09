<#
.SYNOPSIS
    Captures a live, running Windows PC into a bootable VHDX image without rebooting.

.DESCRIPTION
    Wraps Sysinternals Disk2vhd, which uses the Volume Shadow Copy Service (VSS) to take a
    crash-consistent snapshot of volumes that are currently in use. The machine stays online
    and usable for the whole capture. No reboot is required at any point.

    The script does the preflight work that Disk2vhd itself does not:
      * verifies elevation, destination free space, and that the destination is not on a
        volume being captured
      * detects UEFI vs legacy BIOS boot (the resulting VM firmware MUST match)
      * detects and suspends BitLocker (a captured encrypted volume will not boot elsewhere)
      * temporarily letters the EFI System Partition so the capture is actually bootable
      * records everything the conversion/import step needs into manifest.json

.PARAMETER OutputPath
    Directory for the image, on a drive that is NOT being captured. An external USB disk or a
    network share is the normal choice. Needs roughly the used space of C: plus 10%.

.PARAMETER Volumes
    'auto'  (default) - EFI System Partition + the Windows volume. Smallest bootable capture.
    '*'     - every volume on every attached disk. Do not use with a local destination drive.
    'C: D:' - an explicit space-separated list of drive letters.

.PARAMETER SkipBitLockerSuspend
    Do not touch BitLocker. The capture will contain encrypted blocks and will not boot in a
    VM without the original TPM. Only use if you have already handled decryption yourself.

.PARAMETER Disk2vhdPath
    Path to disk2vhd64.exe. If omitted, the script looks on PATH, then beside itself, then
    downloads Disk2vhd from download.sysinternals.com.

.PARAMETER DryRun
    Run every preflight check and write the manifest, but do not capture.

.EXAMPLE
    .\Capture-WindowsVM.ps1 -OutputPath E:\p2v

.EXAMPLE
    .\Capture-WindowsVM.ps1 -OutputPath \\nas\images\desktop -Volumes '*' -DryRun

.NOTES
    Run from an ELEVATED PowerShell prompt. Close what you can first - VSS gives a
    crash-consistent image, so anything mid-write behaves like it survived a power cut.
    Windows will almost certainly need reactivation in the VM; see README.md.
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string] $OutputPath,

    [string] $Volumes = 'auto',

    [switch] $SkipBitLockerSuspend,

    [string] $Disk2vhdPath,

    [switch] $DryRun
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$script:AssignedEfiLetter = $null
$script:SuspendedBitLocker = @()

function Write-Step  { param($m) Write-Host "`n==> $m" -ForegroundColor Cyan }
function Write-Ok    { param($m) Write-Host "    [ok]   $m" -ForegroundColor Green }
function Write-Warn  { param($m) Write-Host "    [warn] $m" -ForegroundColor Yellow }
function Write-Info  { param($m) Write-Host "    $m" -ForegroundColor Gray }

function Test-Elevated {
    $id = [Security.Principal.WindowsIdentity]::GetCurrent()
    (New-Object Security.Principal.WindowsPrincipal $id).IsInRole(
        [Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Get-FirmwareType {
    # Two independent signals; they should agree. bcdedit is the reliable one.
    $bcd = try { & bcdedit /enum '{current}' 2>$null | Out-String } catch { '' }
    if ($bcd -match '(?i)winload\.efi') { return 'UEFI' }
    if ($bcd -match '(?i)winload\.exe') { return 'BIOS' }
    if (Test-Path 'HKLM:\SYSTEM\CurrentControlSet\Control\SecureBoot\State') { return 'UEFI' }
    return 'Unknown'
}

function Get-ActivationChannel {
    try {
        $p = Get-CimInstance SoftwareLicensingProduct `
             -Filter "PartialProductKey IS NOT NULL AND Name LIKE 'Windows%'" |
             Select-Object -First 1
        if ($null -eq $p) { return 'Unknown' }
        switch -Regex ($p.Description) {
            'OEM_DM|OEM_SLP' { return 'OEM (locked to this hardware - will NOT transfer)' }
            'Retail|MAK'     { return 'Retail/MAK (transferable, may need phone activation)' }
            'VOLUME_KMSCLIENT|Volume' { return 'Volume/KMS (reactivates against your KMS)' }
            default          { return $p.Description }
        }
    } catch { return 'Unknown' }
}

function Resolve-Disk2vhd {
    param([string] $Hint)

    foreach ($c in @($Hint,
                     (Join-Path $PSScriptRoot 'disk2vhd64.exe'),
                     (Join-Path $PSScriptRoot 'disk2vhd.exe'))) {
        if ($c -and (Test-Path $c)) { return (Resolve-Path $c).Path }
    }
    $onPath = Get-Command disk2vhd64.exe, disk2vhd.exe -ErrorAction SilentlyContinue |
              Select-Object -First 1
    if ($onPath) { return $onPath.Source }

    Write-Info 'Disk2vhd not found locally; downloading from Sysinternals...'
    $zip = Join-Path $env:TEMP 'Disk2vhd.zip'
    $dst = Join-Path $env:TEMP 'Disk2vhd'
    try {
        Invoke-WebRequest -Uri 'https://download.sysinternals.com/files/Disk2vhd.zip' `
                          -OutFile $zip -UseBasicParsing
        if (Test-Path $dst) { Remove-Item $dst -Recurse -Force }
        Expand-Archive -Path $zip -DestinationPath $dst -Force
    } catch {
        throw ("Could not download Disk2vhd ({0}). Fetch it manually from " +
               "https://learn.microsoft.com/sysinternals/downloads/disk2vhd and pass " +
               "-Disk2vhdPath." -f $_.Exception.Message)
    }
    $exe = Get-ChildItem $dst -Filter 'disk2vhd64.exe' -Recurse |
           Select-Object -First 1
    if (-not $exe) {
        $exe = Get-ChildItem $dst -Filter 'disk2vhd.exe' -Recurse | Select-Object -First 1
    }
    if (-not $exe) { throw 'Downloaded Disk2vhd archive did not contain an executable.' }
    return $exe.FullName
}

function Mount-EfiPartition {
    # mountvol S: /S letters the EFI System Partition on a live UEFI system. No reboot.
    foreach ($letter in @('S', 'T', 'U', 'W', 'Y')) {
        if (Test-Path "$letter`:\") { continue }
        $out = & mountvol "$letter`:" /S 2>&1
        if ($LASTEXITCODE -eq 0) {
            $script:AssignedEfiLetter = $letter
            Write-Ok "EFI System Partition temporarily mounted at ${letter}:"
            return "${letter}:"
        }
        Write-Info "mountvol ${letter}: /S -> $out"
    }
    return $null
}

function Dismount-EfiPartition {
    if ($script:AssignedEfiLetter) {
        & mountvol "$($script:AssignedEfiLetter):" /D 2>&1 | Out-Null
        Write-Ok "EFI System Partition unmounted from $($script:AssignedEfiLetter):"
        $script:AssignedEfiLetter = $null
    }
}

function Restore-BitLocker {
    foreach ($mp in $script:SuspendedBitLocker) {
        try {
            Resume-BitLocker -MountPoint $mp -ErrorAction Stop | Out-Null
            Write-Ok "BitLocker protection resumed on $mp"
        } catch {
            Write-Warn ("COULD NOT RESUME BITLOCKER ON {0}. Run: Resume-BitLocker " +
                        "-MountPoint {0}" -f $mp)
        }
    }
    $script:SuspendedBitLocker = @()
}

# ---------------------------------------------------------------- preflight --

Write-Step 'Preflight'

if (-not (Test-Elevated)) {
    throw 'Run this from an elevated PowerShell prompt (Run as Administrator).'
}
Write-Ok 'Running elevated'

$sysDrive = $env:SystemDrive                      # normally 'C:'
$firmware = Get-FirmwareType
Write-Ok "Boot firmware: $firmware"
if ($firmware -eq 'Unknown') {
    Write-Warn 'Could not determine UEFI vs BIOS. Check manually before building the VM.'
}

$os     = Get-CimInstance Win32_OperatingSystem
$cs     = Get-CimInstance Win32_ComputerSystem
$build  = [int](Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion').CurrentBuild
$isWin11 = $build -ge 22000
Write-Ok ("Source OS: {0} (build {1})" -f $os.Caption, $build)
Write-Ok ("Source hardware: {0} vCPU, {1} GB RAM" -f `
          $cs.NumberOfLogicalProcessors, [math]::Round($cs.TotalPhysicalMemory / 1GB))

$activation = Get-ActivationChannel
if ($activation -like 'OEM*') {
    Write-Warn "Windows licence: $activation"
} else {
    Write-Ok "Windows licence: $activation"
}

if ($isWin11) {
    Write-Warn 'Windows 11 source: the VM must present a vTPM 2.0 and UEFI or it will not boot.'
}

# Destination
if (-not (Test-Path $OutputPath)) { New-Item -ItemType Directory -Path $OutputPath -Force | Out-Null }
$OutputPath = (Resolve-Path $OutputPath).Path
$destRoot   = [System.IO.Path]::GetPathRoot($OutputPath)
$isUnc      = $OutputPath.StartsWith('\\')
Write-Ok "Destination: $OutputPath"

# Everything below can leave state on the live machine - a lettered EFI partition, a
# suspended BitLocker protector - so it all runs under the cleanup in `finally`.
try {

    # Volume selection
    $captureList = @()
    switch -Regex ($Volumes) {
        '^\*$' {
            $captureList = @('*')
            Write-Warn 'Capturing ALL volumes on ALL disks - destination must be a network share or the capture will eat itself.'
        }
        '^auto$' {
            $captureList += $sysDrive
            if ($firmware -eq 'UEFI') {
                $efi = Mount-EfiPartition
                if ($efi) {
                    $captureList = @($efi) + $captureList
                } else {
                    Write-Warn ('Could not letter the EFI System Partition. The image will contain ' +
                                'Windows but no bootloader. Use the Disk2vhd GUI and tick the ' +
                                'unlettered EFI volume by hand, or re-run with -Volumes ''*''.')
                }
            } else {
                Write-Warn ('Legacy BIOS boot: the active "System Reserved" partition usually has no ' +
                            'drive letter. Use the Disk2vhd GUI and tick it, or -Volumes ''*''.')
            }
        }
        default {
            $captureList = $Volumes -split '\s+' | Where-Object { $_ }
        }
    }
    Write-Ok ("Volumes to capture: {0}" -f ($captureList -join ' '))

    # Destination must not be inside the capture set
    if ($captureList -contains '*' -and -not $isUnc) {
        Write-Warn "-Volumes '*' with a local destination ($destRoot) - Disk2vhd will try to capture the drive it is writing to."
    }
    foreach ($v in $captureList) {
        if ($v -ne '*' -and $destRoot -like "$v*") {
            throw "Destination $OutputPath is on $v, which is being captured. Use a different drive."
        }
    }

    # Space
    $usedBytes = 0
    foreach ($v in $captureList) {
        if ($v -eq '*') {
            # Measure-Object -Property does not accept a hashtable calculated property,
            # so project to the used-bytes figure first and sum that.
            $usedBytes = (Get-CimInstance Win32_LogicalDisk -Filter 'DriveType=3' |
                          ForEach-Object { $_.Size - $_.FreeSpace } |
                          Measure-Object -Sum).Sum
            break
        }
        $ld = Get-CimInstance Win32_LogicalDisk -Filter "DeviceID='$v'" -ErrorAction SilentlyContinue
        if ($ld) { $usedBytes += ($ld.Size - $ld.FreeSpace) }
    }
    $neededGB = [math]::Round(($usedBytes * 1.1) / 1GB, 1)
    Write-Ok "Estimated image size (used data + 10%): ${neededGB} GB"

    if (-not $isUnc) {
        $destFreeGB = [math]::Round(
            (Get-CimInstance Win32_LogicalDisk -Filter "DeviceID='$($destRoot.TrimEnd('\'))'").FreeSpace / 1GB, 1)
        Write-Ok "Free space at destination: ${destFreeGB} GB"
        if ($destFreeGB -lt $neededGB) {
            throw "Not enough room: need ~${neededGB} GB, have ${destFreeGB} GB at $destRoot."
        }
    } else {
        Write-Info 'Destination is a UNC path - free space not checked. Confirm the share has room.'
    }

    # BitLocker
    $blVolumes = @()
    try {
        # @(...) matters: a pipeline that matches nothing yields $null, and $null.Count
        # is a terminating error under Set-StrictMode -Version Latest.
        $blVolumes = @(Get-BitLockerVolume -ErrorAction Stop |
                       Where-Object { $_.ProtectionStatus -eq 'On' })
    } catch {
        Write-Info 'BitLocker cmdlets unavailable (Home edition or feature absent) - assuming no encryption.'
    }
    if ($blVolumes.Count -gt 0) {
        $names = ($blVolumes | ForEach-Object { $_.MountPoint }) -join ', '
        if ($SkipBitLockerSuspend) {
            Write-Warn "BitLocker ACTIVE on $names and -SkipBitLockerSuspend was passed. The image will not boot in a VM."
        } else {
            Write-Warn "BitLocker active on $names - suspending (no reboot, resumed automatically at the end)."
        }
    } else {
        Write-Ok 'No active BitLocker protection detected'
    }

    $disk2vhd = Resolve-Disk2vhd -Hint $Disk2vhdPath
    Write-Ok "Disk2vhd: $disk2vhd"

    $stamp     = Get-Date -Format 'yyyyMMdd-HHmmss'
    $imageName = ('{0}-{1}.vhdx' -f $env:COMPUTERNAME, $stamp)
    $imagePath = Join-Path $OutputPath $imageName

    # ------------------------------------------------------------------ capture --

        if ($blVolumes.Count -gt 0 -and -not $SkipBitLockerSuspend) {
            Write-Step 'Suspending BitLocker'
            foreach ($bl in $blVolumes) {
                # RebootCount 0 = stay suspended until explicitly resumed. Still no reboot.
                Suspend-BitLocker -MountPoint $bl.MountPoint -RebootCount 0 | Out-Null
                $script:SuspendedBitLocker += $bl.MountPoint
                Write-Ok "Suspended on $($bl.MountPoint)"
            }
        }

        Write-Step 'Writing manifest'
        $manifest = [ordered]@{
            schema           = 'p2v-windows/1'
            capturedUtc      = (Get-Date).ToUniversalTime().ToString('o')
            sourceComputer   = $env:COMPUTERNAME
            image            = $imageName
            firmware         = $firmware
            requiresVtpm     = [bool]$isWin11
            requiresSecureBoot = [bool]$isWin11
            osCaption        = $os.Caption
            osBuild          = $build
            architecture     = $env:PROCESSOR_ARCHITECTURE
            sourceCpuCount   = $cs.NumberOfLogicalProcessors
            sourceMemoryGB   = [math]::Round($cs.TotalPhysicalMemory / 1GB)
            volumes          = $captureList
            estimatedSizeGB  = $neededGB
            activationChannel = $activation
            bitlockerSuspended = $script:SuspendedBitLocker
        }
        $manifestPath = Join-Path $OutputPath ('manifest-{0}.json' -f $stamp)
        $manifest | ConvertTo-Json -Depth 4 | Set-Content -Path $manifestPath -Encoding UTF8
        Write-Ok "manifest -> $manifestPath"

        if ($DryRun) {
            Write-Step 'Dry run - stopping before capture'
            Write-Info "Would run: `"$disk2vhd`" -accepteula -x $($captureList -join ' ') `"$imagePath`""
            return
        }

        Write-Step "Capturing to $imagePath"
        Write-Info 'The PC stays usable. Expect roughly 1-3 GB/min depending on the destination.'

        # -x selects VHDX. Older Disk2vhd builds infer format from the extension instead, so
        # fall back to the positional form if the switch is rejected.
        $argsWithX = @('-accepteula', '-x') + $captureList + @($imagePath)
        $argsPlain = @('-accepteula')      + $captureList + @($imagePath)

        $proc = Start-Process -FilePath $disk2vhd -ArgumentList $argsWithX -NoNewWindow -Wait -PassThru
        if ($proc.ExitCode -ne 0) {
            Write-Warn "Disk2vhd exited $($proc.ExitCode) with -x; retrying without it."
            $proc = Start-Process -FilePath $disk2vhd -ArgumentList $argsPlain -NoNewWindow -Wait -PassThru
        }
        if ($proc.ExitCode -ne 0) {
            throw ("Disk2vhd failed with exit code {0}. Run it interactively (GUI) to see the error; " +
                   "tick 'Use Vhdx' and 'Use Volume Shadow Copy'." -f $proc.ExitCode)
        }

        if (-not (Test-Path $imagePath)) {
            $produced = Get-ChildItem $OutputPath -Filter "$($env:COMPUTERNAME)-$stamp*" |
                        Select-Object -ExpandProperty Name
            throw ("Disk2vhd reported success but $imageName is missing. Files present: " +
                   ($produced -join ', '))
        }

        $sizeGB = [math]::Round((Get-Item $imagePath).Length / 1GB, 1)
        Write-Step 'Capture complete'
        Write-Ok "$imagePath (${sizeGB} GB)"
        Write-Info ''
        Write-Info 'Next: copy the image + manifest to the machine that will host the VM, then run'
        Write-Info '  ./convert-image.sh <image.vhdx> --format qcow2|vmdk'
        Write-Info 'See README.md for the per-hypervisor VM settings and the Apple Silicon caveat.'
    }
finally {
    Write-Step 'Cleanup'
    Dismount-EfiPartition
    Restore-BitLocker
}
