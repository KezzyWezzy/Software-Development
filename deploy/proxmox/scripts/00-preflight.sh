#!/usr/bin/env bash
# Runs ON a Proxmox host. Read-only: gathers facts and flags anything that would
# make a later stage fail. Safe to run at any time, as often as you like.
#
# env in: EXPECT_PANEL_CIDR OFFLINE_BUNDLE_PATH
set -uo pipefail

# Remote scripts arrive via `ssh host "bash -s"`, a non-login shell whose PATH
# is not guaranteed to include sbin -- where ip, pvecm, pvesm and pvesh all live.
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

fail=0
say()  { printf '  %s\n' "$*"; }
good() { printf '  [ ok ] %s\n' "$*"; }
bad()  { printf '  [FAIL] %s\n' "$*"; fail=1; }
note() { printf '  [note] %s\n' "$*"; }

printf '\n=== %s ===\n' "$(hostname -f 2>/dev/null || hostname)"

# --- Proxmox present and what version -------------------------------------
if command -v pveversion >/dev/null 2>&1; then
  good "Proxmox VE: $(pveversion | head -1)"
else
  bad "pveversion not found -- this host is not running Proxmox VE"
fi

# --- Is it already in a cluster? -------------------------------------------
if [[ -f /etc/pve/corosync.conf ]]; then
  cl=$(awk -F': *' '/cluster_name/{print $2}' /etc/pve/corosync.conf | tr -d ' ')
  note "already a cluster member: ${cl:-unknown}"
  note "  quorum: $(pvecm status 2>/dev/null | awk -F': *' '/Quorate/{print $2}')"
  note "  votes:  $(pvecm status 2>/dev/null | awk -F': *' '/Expected votes/{print $2}')"
  if pvecm status 2>/dev/null | grep -qi 'Qdevice'; then
    note "  qdevice: present"
  else
    note "  qdevice: NOT configured"
  fi
else
  note "standalone node (no corosync.conf) -- cluster stage has not run"
fi

# --- Network interfaces ----------------------------------------------------
say ""
say "network interfaces (use these names for *_MGMT_IFACE / *_PANEL_IFACE):"
for i in /sys/class/net/*; do
  n=$(basename "$i")
  [[ "$n" == "lo" ]] && continue
  st=$(cat "$i/operstate" 2>/dev/null || echo "?")
  mac=$(cat "$i/address" 2>/dev/null || echo "?")
  addr=$(ip -4 -o addr show "$n" 2>/dev/null | awk '{print $4}' | paste -sd, -)
  printf '    %-12s %-8s %-18s %s\n' "$n" "$st" "$mac" "${addr:--}"
done

# --- Bridges ---------------------------------------------------------------
say ""
if ip link show vmbr0 >/dev/null 2>&1; then
  good "vmbr0 exists: $(ip -4 -o addr show vmbr0 | awk '{print $4}' | paste -sd, -)"
else
  bad "vmbr0 missing -- the Proxmox installer normally creates it"
fi
if ip link show vmbr1 >/dev/null 2>&1; then
  good "vmbr1 (panel VLAN) exists: $(ip -4 -o addr show vmbr1 | awk '{print $4}' | paste -sd, -)"
else
  note "vmbr1 not present yet -- the network stage will create it"
fi

# --- Panel VLAN reachability ----------------------------------------------
if [[ -n "${EXPECT_PANEL_CIDR:-}" ]]; then
  if ip -4 route | grep -q "${EXPECT_PANEL_CIDR%%/*}"; then
    good "a route toward ${EXPECT_PANEL_CIDR} exists"
  else
    note "no route toward ${EXPECT_PANEL_CIDR} yet (expected before the network stage)"
  fi
fi

# --- Storage ---------------------------------------------------------------
say ""
say "storage:"
pvesm status 2>/dev/null | sed 's/^/    /' || note "pvesm unavailable"
root_avail=$(df -BG --output=avail / 2>/dev/null | tail -1 | tr -dc '0-9')
if [[ -n "$root_avail" && "$root_avail" -lt 8 ]]; then
  bad "/ has only ${root_avail}G free -- clear space before installing packages"
else
  good "/ free space: ${root_avail:-?}G"
fi

# --- Time ------------------------------------------------------------------
say ""
say "time: $(date '+%Y-%m-%d %H:%M:%S %Z')  tz=$(timedatectl show -p Timezone --value 2>/dev/null)"
if timedatectl show -p NTPSynchronized --value 2>/dev/null | grep -q yes; then
  good "clock is NTP-synchronised"
else
  bad "clock is NOT synchronised -- corosync and TLS both break on skewed clocks"
fi

# --- Air-gap: is the offline bundle staged? --------------------------------
say ""
if [[ -d "${OFFLINE_BUNDLE_PATH:-/nonexistent}" ]]; then
  n=$(find "$OFFLINE_BUNDLE_PATH" -name '*.deb' 2>/dev/null | wc -l)
  good "offline bundle at $OFFLINE_BUNDLE_PATH (${n} .deb files)"
  [[ "$n" -gt 0 ]] || bad "bundle directory exists but contains no .deb packages"
else
  bad "offline bundle missing at ${OFFLINE_BUNDLE_PATH:-unset} -- see offline/STAGING.md"
fi

# --- Enterprise repo will 401 on an air-gapped box -------------------------
if grep -rqs '^deb.*enterprise\.proxmox\.com' /etc/apt/sources.list.d/ /etc/apt/sources.list 2>/dev/null; then
  note "enterprise repo still enabled -- post-install will disable it (no subscription, no internet)"
fi

say ""
if [[ "$fail" -ne 0 ]]; then
  printf '  RESULT: NOT READY\n'
  exit 1
fi
printf '  RESULT: ready\n'
