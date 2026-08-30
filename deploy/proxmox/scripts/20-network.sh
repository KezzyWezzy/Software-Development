# Runs ON a Proxmox host. Creates the bridge layout that mirrors kjv1.
#
# Only ever ADDS bridges that do not exist. It never edits or removes an
# existing one -- vmbr0 is created by the PVE installer and carries this SSH
# session, and a bad edit there strands the host on an OT network with no
# remote console. Same reason it refuses a NIC already enslaved elsewhere.
#
# env in: BRIDGES  -- newline-separated records, fields separated by |
#           bridge|iface|cidr|gateway|comment
#         gateway and comment may be empty. cidr may be empty for an
#         unnumbered bridge (host takes no address on that network).
set -euo pipefail
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
say() { printf '  %s\n' "$*"; }

IF=/etc/network/interfaces
[[ -n "${BRIDGES:-}" ]] || { say "BRIDGES unset -- nothing to do"; exit 0; }
[[ -f "$IF" ]] || { say "ERROR: $IF missing"; exit 1; }

# Which physical NICs are already bridge-ports of something?
enslaved() {
  local nic="$1" b
  for b in /sys/class/net/*/brif/"$nic"; do
    [[ -e "$b" ]] && { basename "$(dirname "$(dirname "$b")")"; return 0; }
  done
  grep -qE "^[[:space:]]*bridge-ports.*\b${nic}\b" "$IF" && { echo "(in $IF)"; return 0; }
  return 1
}

cp -n "$IF" "${IF}.pre-ctm" 2>/dev/null || true
added=0

while IFS='|' read -r br iface cidr gw comment; do
  [[ -z "${br// }" ]] && continue
  [[ "$br" == \#* ]] && continue

  if ip link show "$br" >/dev/null 2>&1 || grep -qE "^auto[[:space:]]+${br}\$" "$IF"; then
    say "${br}: already defined -- left untouched"
    continue
  fi

  [[ -n "$iface" ]] || { say "ERROR: ${br} has no interface specified"; exit 1; }

  # The physical NIC must exist on THIS host. Names are MAC-derived on these
  # boxes (enx*), so they differ per machine -- preflight prints the real ones.
  if [[ ! -e "/sys/class/net/${iface}" ]]; then
    say "ERROR: ${br}: interface '${iface}' does not exist on this host"
    say "       run preflight to list this machine's NIC names (they are"
    say "       MAC-derived and differ from the reference server)"
    exit 1
  fi

  if owner="$(enslaved "$iface")"; then
    say "ERROR: ${br}: ${iface} is already a bridge-port of ${owner} -- refusing"
    exit 1
  fi

  {
    echo ""
    echo "# ${comment:-added by ctm-provision}"
    echo "auto ${iface}"
    echo "iface ${iface} inet manual"
    echo ""
    echo "auto ${br}"
    if [[ -n "$cidr" ]]; then
      echo "iface ${br} inet static"
      echo "    address ${cidr}"
      [[ -n "$gw" ]] && echo "    gateway ${gw}"
    else
      echo "iface ${br} inet manual"
    fi
    echo "    bridge-ports ${iface}"
    echo "    bridge-stp off"
    echo "    bridge-fd 0"
  } >> "$IF"

  say "${br}: added on ${iface}${cidr:+ (${cidr})}${gw:+ gw ${gw}}"
  added=$((added+1))
done <<< "$BRIDGES"

if [[ "$added" -eq 0 ]]; then
  say "no new bridges needed"
  exit 0
fi

# ifupdown2 applies changes without dropping vmbr0. Without it, stop short of
# anything reboot-equivalent and make the operator apply it at the console.
if command -v ifreload >/dev/null 2>&1; then
  if ifreload -a; then
    say "network reloaded; ${added} bridge(s) up"
    ip -br -4 addr show type bridge 2>/dev/null | sed 's/^/    /'
  else
    say "ERROR: ifreload failed -- restoring previous config"
    cp "${IF}.pre-ctm" "$IF"
    ifreload -a || true
    exit 1
  fi
else
  say "NOTE: ifupdown2 absent. Config written but NOT applied."
  say "      Apply at the physical console: systemctl restart networking"
fi
