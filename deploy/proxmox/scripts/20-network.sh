#!/usr/bin/env bash
# Runs ON a Proxmox host. Adds the panel-VLAN bridge (vmbr1) that the kiosks
# live on. Deliberately NEVER touches vmbr0 -- that is the interface carrying
# this SSH session, and a bad edit there strands the host on an OT network with
# no remote console.
#
# env in: PANEL_IFACE PANEL_VLAN PANEL_CIDR
set -euo pipefail

# Remote scripts arrive via `ssh host "bash -s"`, a non-login shell whose PATH
# is not guaranteed to include sbin -- where ip, pvecm, pvesm and pvesh all live.
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
say() { printf '  %s\n' "$*"; }

IF=/etc/network/interfaces
[[ -n "${PANEL_IFACE:-}" ]] || { say "PANEL_IFACE unset -- skipping"; exit 0; }

# The physical NIC must exist and must not already be enslaved to vmbr0.
[[ -e "/sys/class/net/${PANEL_IFACE}" ]] \
  || { say "ERROR: ${PANEL_IFACE} is not a real interface on this host"; exit 1; }

if awk '/^iface vmbr0/,/^$/' "$IF" | grep -qw "${PANEL_IFACE}"; then
  say "ERROR: ${PANEL_IFACE} is a bridge-port of vmbr0 -- refusing to steal the mgmt NIC"
  exit 1
fi

if grep -q '^auto vmbr1' "$IF"; then
  say "vmbr1 already defined -- leaving it alone"
  exit 0
fi

cp -n "$IF" "${IF}.pre-ctm" 2>/dev/null || true

port="$PANEL_IFACE"
if [[ -n "${PANEL_VLAN:-}" ]]; then
  port="${PANEL_IFACE}.${PANEL_VLAN}"
  say "panel VLAN is tagged: bridge port ${port}"
fi

cat >> "$IF" <<EOF

# --- panel VLAN, added by ctm-provision -----------------------------------
# Bridge only: the Proxmox host takes no address on the panel network. Kiosk
# traffic is the guests' business, and an unnumbered host cannot be reached
# from the panel VLAN by anything that wanders onto it.
auto ${port}
iface ${port} inet manual

auto vmbr1
iface vmbr1 inet manual
    bridge-ports ${port}
    bridge-stp off
    bridge-fd 0
#   panel network: ${PANEL_CIDR:-unspecified}
EOF
say "appended vmbr1 (port ${port}) to ${IF}"

# ifupdown2 can apply changes without dropping vmbr0. If it is not present,
# stop short of a reboot-equivalent and make the operator do it at the console.
if command -v ifreload >/dev/null 2>&1; then
  if ifreload -a; then
    say "network reloaded; vmbr1 is up"
  else
    say "ERROR: ifreload failed -- restoring previous config"
    cp "${IF}.pre-ctm" "$IF"
    ifreload -a || true
    exit 1
  fi
else
  say "NOTE: ifupdown2 absent. Config written but NOT applied."
  say "      Apply it at the physical console with: systemctl restart networking"
fi
