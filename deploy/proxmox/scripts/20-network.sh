# Runs ON a Proxmox host. Creates the bridge layout that mirrors kjv1.
#
# Only ever ADDS bridges that do not exist. It never edits or removes an
# existing one -- vmbr0 is created by the PVE installer and carries this SSH
# session, and a bad edit there strands the host on an OT network with no
# remote console. Same reason it refuses a NIC already enslaved elsewhere.
#
# Before assigning any address it probes the segment with arping -D (duplicate
# address detection). On a shared Layer 2 domain -- which Red River South is,
# since it reaches North at L2 -- two terminals share one broadcast domain, so
# a planned address that another host already owns is an ARP conflict, not a
# routing problem. Cheaper to refuse here than to debug intermittent loss of a
# Proxmox node later.
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

# addr_in_use IFACE CIDR -- true if some other host already answers for it.
# Returns 2 when the check could not run, so the caller can warn rather than
# wrongly claim the address is free.
addr_in_use() {
  local iface="$1" addr="${2%%/*}" was_down=0 rc

  command -v arping >/dev/null 2>&1 || return 2

  # arping needs the link up to hear a reply. Bring it up if needed and put it
  # back afterwards -- the bridge is not configured yet, so this is harmless.
  if [[ "$(cat "/sys/class/net/${iface}/operstate" 2>/dev/null)" != "up" ]]; then
    ip link set "$iface" up 2>/dev/null || return 2
    was_down=1
    sleep 2
  fi

  # -D duplicate-address mode: exits non-zero if any host replies.
  arping -D -q -c 2 -w 3 -I "$iface" "$addr" >/dev/null 2>&1
  rc=$?

  [[ "$was_down" == "1" ]] && ip link set "$iface" down 2>/dev/null

  # arping -D: 0 = free, 1 = someone answered.
  [[ $rc -eq 1 ]] && return 0
  [[ $rc -eq 0 ]] && return 1
  return 2
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

  # Duplicate-address check before committing the address to config.
  if [[ -n "$cidr" ]]; then
    # Capture the status rather than testing $? inside elif, where an
    # intervening command would silently change what is being tested.
    # Under `set -e` a bare non-zero return aborts the script, so the status
    # must be collected with || rather than read from $? afterwards.
    dup_rc=0; addr_in_use "$iface" "$cidr" || dup_rc=$?
    if [[ $dup_rc -eq 0 ]]; then
      say "ERROR: ${br}: ${cidr%%/*} is ALREADY IN USE on the segment reachable"
      say "       from ${iface}. North and South share this Layer 2 domain, so"
      say "       every address must be unique across both terminals."
      say "       Pick an address outside the other terminal's range and re-run."
      exit 1
    elif [[ $dup_rc -eq 2 ]]; then
      say "${br}: WARNING -- could not verify ${cidr%%/*} is free (arping missing"
      say "       or link unavailable). Confirm by hand before trusting this host."
    else
      say "${br}: ${cidr%%/*} is free on the segment"
    fi
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
