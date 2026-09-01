# Live Windows P2V — capture a running PC into a portable VM

Turn the Windows machine you are sitting at right now into a bootable virtual machine,
**without rebooting it and without taking it offline**, then run that VM elsewhere.

The capture uses the Volume Shadow Copy Service, so the OS keeps running while its own
system volume is read. You stay logged in the whole time.

---

## The one thing to decide before you start

**What CPU architecture will host the VM?**

| Host | Result |
|---|---|
| Any Intel/AMD PC, Linux box, server, or **Intel** Mac | Near-native. This is the normal path. |
| **Apple Silicon Mac** (M1–M4) | The x86-64 image only runs under full CPU *emulation* (UTM/QEMU TCG). Roughly 5–20× slower than the original PC. It boots. It is not a machine you would want to work in. |

There is no fix for the second row. Apple Silicon has hardware virtualisation, but only for
**ARM** guests — VMware Fusion, Parallels, and UTM's fast path all require the guest to be
the same architecture as the host. An image of an x86 PC is an x86 guest, permanently.

If a Mac is the machine you actually want to use, the practical answer is not "run the VM on
the Mac". It is **run the VM on x86-64 hardware and reach it from the Mac** — see
[Running it from a Mac](#running-it-from-a-mac).

---

## What you need

- The Windows PC, running, with an administrator account.
- A destination with room for roughly **the used space on C:, plus 10%** — an external USB
  drive (USB 3.0+, exFAT or NTFS) or a network share. Not a drive being captured.
- `qemu-img` on whatever machine converts the image (`brew install qemu` on macOS,
  `sudo apt install qemu-utils` on Debian/Ubuntu). Not needed if the VM will run under
  Hyper-V or Windows-hosted VirtualBox, both of which boot VHDX directly.

## Step 1 — capture the live PC

From an **elevated** PowerShell prompt on the Windows machine:

```powershell
cd tools\p2v-windows
.\Capture-WindowsVM.ps1 -OutputPath E:\p2v
```

Add `-DryRun` first if you want to see every preflight result and the manifest without
committing to the copy.

The script downloads [Sysinternals Disk2vhd](https://learn.microsoft.com/sysinternals/downloads/disk2vhd)
if it isn't already present, and around it does the parts Disk2vhd leaves to you:

- refuses to run unelevated, or to write the image onto a volume it is capturing
- detects **UEFI vs legacy BIOS** — the VM's firmware must match the source or Windows will
  not boot, and this is the single most common reason a P2V image fails
- detects **BitLocker** and suspends it for the duration (`-RebootCount 0`, so no reboot),
  resuming it in a `finally` block. A capture of an encrypted volume is unbootable anywhere
  but the original TPM, so this is not optional
- temporarily letters the **EFI System Partition** with `mountvol S: /S` so the bootloader is
  actually inside the image, then unmounts it afterwards
- writes `manifest-<timestamp>.json` recording firmware mode, Windows build, whether a vTPM
  is required, CPU/RAM, and the licence channel — step 2 reads this

Expect roughly 1–3 GB/min, dominated by the destination drive. A 300 GB capture over USB 3
is a couple of hours. **Keep using the PC while it runs.**

> VSS gives a *crash-consistent* image — the guest boots as if it had lost power at the
> snapshot instant. Windows handles this fine. Databases and VMs running *inside* the source
> PC may not; shut those down first if you have any.

### Volume selection

`-Volumes auto` (the default) captures the EFI System Partition plus `C:` — the smallest
bootable result. Use `-Volumes '*'` for every volume on every disk (only sane when writing to
a network share), or name letters explicitly: `-Volumes 'C: D:'`.

If the script reports it could not letter the EFI/System Reserved partition, run
`disk2vhd64.exe` interactively instead and tick the unlettered volume by hand, with
**Use Vhdx** and **Use Volume Shadow Copy** both checked.

## Step 2 — convert for the target hypervisor

Copy the `.vhdx` **and its `manifest-*.json`** to the host machine, then:

```bash
./convert-image.sh KEZZY-PC-20260830-141230.vhdx --format qcow2   # UTM, QEMU, Proxmox
./convert-image.sh KEZZY-PC-20260830-141230.vhdx --format vmdk    # VMware, VirtualBox
```

It converts the disk and prints the exact VM settings the manifest says this image needs. It
also refuses to be quiet about an ARM host with an x86 image.

Skip this step entirely for **Hyper-V** or **VirtualBox on Windows** — attach the `.vhdx` as-is.

## Step 3 — build the VM

Match these or it will not boot:

| Setting | Value |
|---|---|
| Firmware | **Exactly what the manifest says** — UEFI or BIOS |
| vTPM | Required for a Windows 11 source (VMware Fusion: encrypt the VM, add TPM. VirtualBox 7+: TPM 2.0. UTM: enable) |
| Secure Boot | Enable for Windows 11 |
| Disk controller | SATA/AHCI for the first boot — a virtual NVMe or paravirtual controller the running Windows has no driver for gives an `INACCESSIBLE_BOOT_DEVICE` stop |
| CPU / RAM | At or below the source; at least 2 vCPU / 4 GB |

First boot is slow while Windows swaps the real machine's storage and GPU drivers for generic
ones. Once up, install the guest tools (VMware Tools, Guest Additions, SPICE) before you judge
performance — graphics are software-rendered until then.

## Building a Proxmox host

Proxmox VE is the recommended x86-64 host for this image: `qm disk import` reads VHDX directly
via `qemu-img`, so **you can skip step 2 entirely** and import the raw Disk2vhd output.

### Make the installer USB

`New-ProxmoxInstallUsb.ps1` downloads the ISO, verifies its SHA256, and writes it to a stick in
DD (raw) mode. Elevated PowerShell, 8 GB stick or larger:

```powershell
.\New-ProxmoxInstallUsb.ps1 -DriveLetter D -WhatIf   # every check, writes nothing
.\New-ProxmoxInstallUsb.ps1 -DriveLetter D
```

The ISO is a hybrid image and must be written sector for sector. Copying the files onto a FAT32
stick does not boot, and **Rufus's default "ISO mode" rewrites the boot layout in a way the PVE
installer does not survive** — that one setting is the most common cause of a Proxmox stick that
won't boot. If you use Rufus instead of this script, pick **DD Image mode**.

The script destroys the target disk, so it resolves the disk number *before* wiping the partition
table, and refuses any disk that is not on the USB bus, is larger than 512 GB, is under 4 GB, or is
the boot/system disk. `-Force` overrides the first two. Nothing overrides the boot-disk refusal.
You then type the disk's model name to confirm.

### Install and import

Boot the installer in **UEFI** mode with VT-x/AMD-V enabled. At the filesystem prompt: ZFS RAID1 if
you have two SSDs and ≥32 GB RAM (snapshots, checksums, and ARC will use the RAM); otherwise
ext4 + LVM-thin, which is simpler and still does thin snapshots. Don't install onto the drive
holding your capture. Afterwards, fix the subscription-repo error under
**Datacenter → *node* → Updates → Repositories**: disable `pve-enterprise`, add `pve-no-subscription`.

```bash
qm create 100 --name kezzy-p2v --ostype win11 \
  --machine q35 --bios ovmf --cpu host --cores 8 --memory 16384 \
  --efidisk0 local-lvm:0,efitype=4m,pre-enrolled-keys=1 \
  --tpmstate0 local-lvm:1,version=v2 \
  --net0 virtio,bridge=vmbr0 --scsihw virtio-scsi-single

qm disk import 100 /var/lib/vz/dump/KEZZY-PC-20260831-052724.vhdx local-lvm
qm set 100 --sata0 local-lvm:vm-100-disk-2
qm set 100 --boot order=sata0
```

`efidisk0` takes `disk-0` and `tpmstate0` takes `disk-1`, so the imported disk is usually `disk-2` —
read the `unused0:` line from `qm config 100` rather than assuming. Attach it as SATA for the first
boot, then install the VirtIO guest drivers and move it to `scsi0` on `virtio-scsi-single`; that's
where the performance is. `--ostype win11` matters (it enables the Hyper-V enlightenments), the
imported disk carries its own ESP so `efidisk0` is only NVRAM, and if the VM won't boot, retry with
`pre-enrolled-keys=0` before assuming the image is bad.

## Running it from a Mac

Ranked by how good the result actually is:

1. **Host the VM on x86-64, use the Mac as a screen.** Any Intel/AMD box, home server,
   Proxmox node, or a cloud VM (Azure and AWS both import VHDs directly). Connect with
   Microsoft Remote Desktop from the Mac — or from an iPad, or another Windows PC. This is
   the only option that is both fast *and* reachable from any machine, which is what you
   asked for.
2. **Intel Mac + VMware Fusion.** Full speed, runs locally, free for personal use.
3. **Apple Silicon + UTM/QEMU emulation.** Works, and it is genuinely slow. Fine for
   occasionally reaching a file or an old app; not fine as a daily driver.

## Things that will bite you

**Windows licensing.** A change of "hardware" this total deactivates Windows. An OEM licence
— the kind preinstalled on a prebuilt PC — is tied to the original motherboard and will not
transfer; you would need a new licence for the VM. A retail licence can move, sometimes via
phone activation. The script reports which one you have. Also: running the VM *and* the
original PC at the same time needs two licences.

**Never run both on the same network at once.** Identical hostname, machine SID, and any
domain/Entra join. They will fight. If you need both live, rename the clone and rejoin it.

**Claude Desktop specifically.** The app and its config come across in the image — including
`claude_desktop_config.json` and your MCP server definitions. Two things won't just work:

- You will have to **sign in again**. The session doesn't survive the hardware change, and MFA
  may trigger.
- Any **MCP server pointing at a local path or a local service** needs that path to exist in
  the VM too. Ones referencing network drives (`N:\...`) need the drive remapped and the VM on
  a network that can reach it.

**Encrypted or DRM'd applications** keyed to the hardware (some VPN clients, licensed
engineering software, hardware dongles) will ask to be reactivated.

**Antivirus/EDR** may block Disk2vhd's snapshot driver. Whitelist it or pause protection for
the capture.

## Alternatives to Disk2vhd

- **StarWind V2V Converter** — free, converts live to VMDK/QCOW2/VHDX directly, skipping step 2.
- **Clonezilla / Macrium Reflect** — image to a file, restore into a VM. Requires boot media,
  so it fails your "without rebooting" requirement.
- **VMware vCenter Converter Standalone** — the classic hot-clone P2V straight into a VMware VM.

## Status

### `Capture-WindowsVM.ps1`

Written against Disk2vhd 2.02. **Never executed on a Windows host** — no Windows machine was
available where it was authored. What *has* been done is a mocked dry run: `tests/Invoke-DryRunHarness.ps1`
substitutes the Windows-only calls (`Get-CimInstance`, `Get-BitLockerVolume`, `bcdedit`,
`mountvol`, `Get-Command`, the elevation check) and runs the real script under PowerShell 7 with
`-DryRun` across ten scenario combinations — UEFI and BIOS, with and without BitLocker, EFI
lettering succeeding and failing, `auto` and `*` volume modes, and an out-of-space failure.

```bash
pwsh -File tests/Invoke-DryRunHarness.ps1 -Scenario uefi-win11+bl
pwsh -File tests/Invoke-DryRunHarness.ps1 -Scenario bios-plain -Star
```

That found and fixed three real defects:

| Defect | Effect |
|---|---|
| `try`/`finally` opened after the EFI partition was lettered | A preflight failure (out of space, bad destination) left the EFI System Partition mounted as `S:` on the live machine |
| `Measure-Object -Property @{Expression=…}` | `-Volumes '*'` crashed on every run — a hashtable calculated property is not a valid `-Property` argument |
| `Get-BitLockerVolume \| Where-Object` yields `$null`, not `@()`, when nothing matches | `$null.Count` is a terminating error under `Set-StrictMode -Version Latest`, so the script died on any PC **without** BitLocker — the common case |

The harness proves control flow, arithmetic, StrictMode compliance, manifest contents, and that
cleanup runs on every exit path. It proves **nothing about Windows behaviour**: VSS, the real
`mountvol`/`bcdedit`/Disk2vhd, and Windows path semantics are all mocked. The
destination-on-a-captured-volume check specifically cannot be exercised there, because a Linux
path root is `/` and never a drive letter.

So: still run it with `-DryRun` on the real machine first. The dry run performs every preflight
check and writes the manifest without reading or writing a single disk block.

### `New-ProxmoxInstallUsb.ps1`

Also **never executed on Windows**. `tests/Invoke-UsbGuardTests.ps1` mocks `Get-Disk` and friends
and drives the script with `-WhatIf` across seven fake disks, asserting that each is accepted or
refused *for the right reason*: a genuine 32 GB stick proceeds, internal NVMe and SATA disks are
refused as non-USB, an 8 TB USB drive is refused by the size sanity limit but proceeds under
`-Force`, a 2 GB stick is refused as too small, and the boot disk is refused even with `-Force`.

```bash
pwsh -File tests/Invoke-UsbGuardTests.ps1
```

That covers target selection — the part where a defect destroys a disk. **The raw write path is
not covered at all**: `-WhatIf` returns before it, and it cannot be exercised without a real USB
stick on a real Windows host. Run `-WhatIf` first and read back the disk it names. If the raw
write fails on your machine, use Rufus in DD Image mode.

### `convert-image.sh`

Argument handling, manifest parsing, per-key missing-value warnings, the no-manifest fallback and
the ARM-host guard were all exercised, with `qemu-img` stubbed. The conversion itself has not been
run against a real VHDX — `qemu-img` was not installable in the authoring environment.
