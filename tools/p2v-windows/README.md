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

`Capture-WindowsVM.ps1` was written against Disk2vhd 2.02 and has **not been executed on a
Windows host** — there was no Windows machine available in the environment it was authored in.
Run it with `-DryRun` first; the dry run exercises every preflight check and writes the
manifest without touching the disks. `convert-image.sh` was tested for argument handling,
manifest parsing, missing-key warnings, and the ARM-host guard, with `qemu-img` stubbed —
the conversion itself has not been run against a real VHDX.
