#!/usr/bin/env bash
#
# Convert a Disk2vhd VHDX capture into a disk format a hypervisor on this machine can boot,
# and print the VM settings that the capture's manifest says are required.
#
#   ./convert-image.sh DESKTOP-20260830-141230.vhdx --format qcow2
#
# Formats:
#   qcow2  - UTM, QEMU, virt-manager, Proxmox            (default on macOS/Linux)
#   vmdk   - VMware Fusion / Workstation / Player, VirtualBox
#   vdi    - VirtualBox native
#   raw    - anything, but consumes the full provisioned size on disk
#
set -euo pipefail

FORMAT=qcow2
OUT=""
IMAGE=""

die()  { printf '\033[31merror:\033[0m %s\n' "$*" >&2; exit 1; }
warn() { printf '\033[33mwarn:\033[0m  %s\n' "$*" >&2; }
ok()   { printf '\033[32mok:\033[0m    %s\n' "$*"; }
info() { printf '       %s\n' "$*"; }

usage() {
  awk 'NR>1 { if ($0 !~ /^#/) exit; sub(/^# ?/, ""); print }' "$0"
  exit "${1:-0}"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --format|-f) FORMAT="${2:?--format needs a value}"; shift 2 ;;
    --out|-o)    OUT="${2:?--out needs a value}"; shift 2 ;;
    --help|-h)   usage 0 ;;
    -*)          die "unknown option: $1" ;;
    *)           IMAGE="$1"; shift ;;
  esac
done

[[ -n "$IMAGE" ]] || usage 1
[[ -f "$IMAGE" ]] || die "no such file: $IMAGE"

case "$FORMAT" in
  qcow2|vmdk|vdi|raw) ;;
  *) die "unsupported format '$FORMAT' (use qcow2, vmdk, vdi, or raw)" ;;
esac

command -v qemu-img >/dev/null 2>&1 || die \
  "qemu-img not found. macOS: brew install qemu   Debian/Ubuntu: sudo apt install qemu-utils"

[[ -n "$OUT" ]] || OUT="${IMAGE%.*}.${FORMAT}"

# ------------------------------------------------------------------ manifest --

MANIFEST=""
for candidate in "$(dirname "$IMAGE")"/manifest-*.json; do
  [[ -f "$candidate" ]] && MANIFEST="$candidate"
done

# Flat-JSON reader. Deliberately dependency-free: jq is not present on a stock macOS,
# and a manifest key that silently falls back to a default can hand you the wrong
# firmware line, which means a VM that will not boot.
mf() { # mf <key> <default>
  local key="$1" default="${2-}" value
  if [[ -z "$MANIFEST" ]]; then printf '%s' "$default"; return 0; fi
  value=$(sed -n "s/.*\"$key\"[[:space:]]*:[[:space:]]*\(.*\)/\\1/p" "$MANIFEST" |
          head -1 | sed 's/,[[:space:]]*$//; s/^"//; s/"$//')
  if [[ -z "$value" ]]; then
    warn "manifest has no readable '$key'; using '$default'"
    printf '%s' "$default"
  else
    printf '%s' "$value"
  fi
}

FIRMWARE=$(mf firmware UEFI)
VTPM=$(mf requiresVtpm false)
GUEST_ARCH=$(mf architecture AMD64)
CPUS=$(mf sourceCpuCount 4)
MEM=$(mf sourceMemoryGB 8)
OSNAME=$(mf osCaption Windows)
ACTIVATION=$(mf activationChannel unknown)

if [[ -n "$MANIFEST" ]]; then ok "manifest: $MANIFEST"; else warn "no manifest-*.json beside the image; assuming UEFI x86-64"; fi

# ------------------------------------------------------------ host sanity ----

HOST_ARCH=$(uname -m)
HOST_OS=$(uname -s)

if [[ "$HOST_ARCH" == "arm64" || "$HOST_ARCH" == "aarch64" ]] && [[ "$GUEST_ARCH" == AMD64 || "$GUEST_ARCH" == x86* ]]; then
  cat >&2 <<'ARM'

  ------------------------------------------------------------------------
  This host is ARM. The captured PC is x86-64.

  There is no hardware virtualisation path for an x86 guest on an ARM host.
  On an Apple Silicon Mac this image can only run under full CPU emulation
  (UTM/QEMU with TCG), which typically lands somewhere between 5x and 20x
  slower than the original machine. It boots; it is not pleasant to use.

  If you need this VM to feel like the real PC, run it on x86-64 hardware
  (any Intel/AMD Windows or Linux box, or a cloud VM) and reach it from the
  Mac over RDP. See "Running it from a Mac" in README.md.
  ------------------------------------------------------------------------

ARM
fi

# --------------------------------------------------------------- convert -----

VIRTUAL_SIZE=$(qemu-img info --output=json "$IMAGE" 2>/dev/null |
               grep -o '"virtual-size":[[:space:]]*[0-9]*' | head -1 | grep -o '[0-9]*' || echo 0)
if [[ "$VIRTUAL_SIZE" -gt 0 ]]; then
  info "source virtual size: $(( VIRTUAL_SIZE / 1024 / 1024 / 1024 )) GB"
fi
info "converting $IMAGE -> $OUT ($FORMAT)"
info "this rewrites the whole image; allow disk space and time for it"

CONVERT_OPTS=()
case "$FORMAT" in
  qcow2) CONVERT_OPTS=(-o cluster_size=65536) ;;
  vmdk)  CONVERT_OPTS=(-o adapter_type=lsilogic,subformat=monolithicSparse) ;;
esac

qemu-img convert -p -f vhdx -O "$FORMAT" "${CONVERT_OPTS[@]}" "$IMAGE" "$OUT"
ok "wrote $OUT"

# ------------------------------------------------------------ VM settings ----

TPM_LINE="not required"
[[ "$VTPM" == "true" ]] && TPM_LINE="REQUIRED (TPM 2.0) - Windows 11 will not boot without it"

cat <<SETTINGS

Configure the VM with exactly these, or it will not boot:

  Guest OS          $OSNAME
  Firmware          $FIRMWARE            <- must match the source, no exceptions
  vTPM              $TPM_LINE
  Disk              $OUT
  Disk controller   SATA/AHCI (not NVMe, not paravirtual, on first boot)
  CPUs              $CPUS or fewer
  Memory            ${MEM} GB or less, at least 4 GB
  Network           NAT to start with
  Licence           $ACTIVATION

First boot:
  1. Expect one slow boot while Windows swaps in generic storage/display drivers.
  2. Install the guest tools (VMware Tools / VirtualBox Guest Additions / SPICE
     guest tools) before judging performance - graphics are software-rendered
     until you do.
  3. Reactivate Windows, and sign in to Claude Desktop again; its session token
     does not survive the hardware change.
  4. Do not run the VM and the original PC on the network at the same time -
     same hostname, same machine SID, same domain/AD identity.

SETTINGS
