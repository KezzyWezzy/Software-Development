# Runs ON node 1. Defines the HA group that CTM guests are placed into.
#
# READ THIS BEFORE ENABLING HA ON A LOADING TERMINAL
# --------------------------------------------------
# Proxmox HA is enforced by a hardware watchdog. A node that loses quorum for
# ~60s does not "fail over gracefully" -- it SELF-FENCES, i.e. hard-resets, so
# the surviving node can safely start the guest. That is correct behaviour for
# a datacentre and a loud one for a terminal: any bay mid-load on the fenced
# node drops when it reboots.
#
# The QDevice is what keeps that from happening on a routine link blip -- with
# three votes a single corosync path failure still leaves both nodes quorate.
# So: never enable HA on this cluster without the QDevice healthy, and check
# `pvecm status` shows the Qdevice line before relying on it.
#
# env in: NODE1 NODE2 SITE
set -euo pipefail

# Remote scripts arrive via `ssh host "bash -s"`, a non-login shell whose PATH
# is not guaranteed to include sbin -- where ip, pvecm, pvesm and pvesh all live.
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
say() { printf '  %s\n' "$*"; }

[[ -f /etc/pve/corosync.conf ]] || { say "ERROR: not in a cluster"; exit 1; }

if ! pvecm status 2>/dev/null | grep -qi 'Qdevice'; then
  say "ERROR: no QDevice registered. Refusing to configure HA on a bare two-node"
  say "       cluster -- a single node failure would leave the survivor without"
  say "       quorum, and it would fence itself instead of taking over."
  say "       Run the 'qdevice' stage first."
  exit 1
fi

GROUP="ctm-${SITE}"

# node1 preferred, node2 as fallback. nofailback keeps a recovered node from
# yanking the guest back mid-load; the move is then a deliberate operator action.
if ha-manager groupconfig 2>/dev/null | grep -q "^group: ${GROUP}\b"; then
  say "HA group '${GROUP}' already exists"
else
  ha-manager groupadd "$GROUP" \
    --nodes "${NODE1}:2,${NODE2}:1" \
    --nofailback 1 \
    --restricted 1
  say "created HA group '${GROUP}' (${NODE1} preferred, ${NODE2} fallback, nofailback)"
fi

ha-manager groupconfig | sed 's/^/    /'

say ""
say "To place the CTM server guest under HA once it exists:"
say "    ha-manager add vm:<VMID> --group ${GROUP} --max_restart 2 --max_relocate 1"
say "Then verify with: ha-manager status"
