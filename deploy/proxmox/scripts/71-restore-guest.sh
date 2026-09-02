# Runs ON a Proxmox host in the TARGET cluster. Restores a guest from a vzdump
# archive -- the supported way to clone the CTM server rather than rebuild it.
#
# THE GUEST IS NEVER AUTO-STARTED.
#
# A restored guest carries the ORIGINAL host's network configuration inside its
# own OS: the CTM server comes back believing it is 192.168.50.129. North and
# South share a Layer 2 domain, so booting it unmodified puts a second host on
# the wire claiming an address that already exists at North. That is an ARP
# conflict on a live loading system, caused by us, at the worst moment.
#
# So: restore stopped, fix the address inside the guest, then start it.
#
# env in: ARCHIVE     path to the vzdump file, or STORAGE:backup/<file>
#         NEW_VMID    VMID to restore as (must be free on this cluster)
#         TARGET_STORAGE  storage for the restored disks
#         FORCE       1 to overwrite an existing VMID (refuses by default)
set -euo pipefail
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
say() { printf '  %s\n' "$*"; }

for v in ARCHIVE NEW_VMID TARGET_STORAGE; do
  [[ -n "${!v:-}" ]] || { say "ERROR: $v unset"; exit 1; }
done
[[ "$NEW_VMID" =~ ^[0-9]+$ ]] || { say "ERROR: NEW_VMID must be numeric"; exit 1; }

if [[ -f "/etc/pve/qemu-server/${NEW_VMID}.conf" || -f "/etc/pve/lxc/${NEW_VMID}.conf" ]]; then
  if [[ "${FORCE:-0}" != "1" ]]; then
    say "ERROR: VMID ${NEW_VMID} already exists on this cluster."
    say "       Pick a free id, or set FORCE=1 to DESTROY and replace it."
    exit 1
  fi
  say "WARNING: overwriting existing guest ${NEW_VMID} (FORCE=1)"
fi

pvesm status --storage "$TARGET_STORAGE" >/dev/null 2>&1 \
  || { say "ERROR: storage '${TARGET_STORAGE}' not defined here"; exit 1; }

# Container archives and VM archives take different restore commands.
case "$ARCHIVE" in
  *vzdump-lxc-*)  RESTORE="pct restore";  KIND="container" ;;
  *vzdump-qemu-*) RESTORE="qmrestore";    KIND="vm" ;;
  *) say "ERROR: cannot tell guest type from archive name: ${ARCHIVE}"; exit 1 ;;
esac

say "restoring ${KIND} from ${ARCHIVE} as VMID ${NEW_VMID} on ${TARGET_STORAGE}"

# --start is never passed. pct/qmrestore leave the guest stopped by default and
# that default is load-bearing here, so it is asserted rather than assumed.
if [[ "$KIND" == "container" ]]; then
  pct restore "$NEW_VMID" "$ARCHIVE" --storage "$TARGET_STORAGE" \
    ${FORCE:+--force 1}
else
  qmrestore "$ARCHIVE" "$NEW_VMID" --storage "$TARGET_STORAGE" \
    ${FORCE:+--force 1}
fi

say "restored, and left STOPPED."

# Show what the guest will try to be when it boots.
CONF="/etc/pve/qemu-server/${NEW_VMID}.conf"
[[ -f "$CONF" ]] || CONF="/etc/pve/lxc/${NEW_VMID}.conf"
say ""
say "network configuration it was restored with:"
grep -E '^(net[0-9]+|ipconfig[0-9]+|hostname|name):' "$CONF" 2>/dev/null | sed 's/^/    /' \
  || say "    (none found in the guest config)"

say ""
say "BEFORE STARTING IT:"
say "  1. Check the bridge in each netN line exists here and is the intended one."
say "  2. Change the address INSIDE the guest OS -- for the CTM server that is"
say "     192.168.50.129 -> 192.168.51.129. A container can be edited from the"
say "     host (pct set / its rootfs); a VM needs a console session."
say "  3. Confirm nothing already answers on the new address:"
say "       arping -D -I <bridge> -c 2 <new-address>"
say "  4. Update the kiosk_devices rows to the new addresses, or the server"
say "     returns 404 to /kiosk.json and the panels never identify themselves."
say ""
say "Start it only after all four:  qm start ${NEW_VMID}   (or pct start)"
