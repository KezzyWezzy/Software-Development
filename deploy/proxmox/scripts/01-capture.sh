# Runs ON any Proxmox host. Read-only. Emits a normalised, deterministic
# snapshot of everything that has to match between servers, on stdout.
#
# Run it against a known-good server to produce the baseline; run it against a
# new server to diff. Output is ordered and host-specific values are tagged so
# that a plain `diff` shows real configuration drift rather than noise.
#
# SECRETS ARE REDACTED. storage.cfg can carry passwords, and /etc/pve/priv is
# never read at all. Check any captured file before sharing it -- it still
# contains plant addressing.
set -uo pipefail
# Remote scripts arrive via `ssh host "bash -s"`, a non-login shell whose PATH
# is not guaranteed to include sbin -- where ip, pvecm, pvesm and pvesh all live.
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
export LC_ALL=C

sec() { printf '\n##### %s\n' "$1"; }
# Strip anything that looks like a credential before it reaches a file.
redact() {
  sed -E 's/(password|passwd|secret|token|key)[[:space:]]*[:=][[:space:]]*.*/\1 <REDACTED>/Ig'
}

printf '# ctm-capture v1\n'

sec "identity (expected to differ between hosts)"
printf 'hostname %s\n' "$(hostname -s)"
printf 'fqdn %s\n'     "$(hostname -f 2>/dev/null || echo '?')"
printf 'machine-id-present %s\n' "$([[ -s /etc/machine-id ]] && echo yes || echo no)"

sec "proxmox version"
pveversion 2>/dev/null || echo "MISSING pveversion"
sec "package versions (pve + cluster critical)"
dpkg-query -W -f='${Package} ${Version}\n' 2>/dev/null \
  | grep -E '^(pve-manager|proxmox-ve|pve-kernel|proxmox-kernel|corosync|corosync-qdevice|libknet1|pve-cluster|pve-ha-manager|ifupdown2|chrony|nfs-common|lvm2) ' \
  | sort

sec "kernel"
uname -r

sec "enabled apt repositories"
grep -rhE '^[[:space:]]*deb ' /etc/apt/sources.list /etc/apt/sources.list.d/ 2>/dev/null | sort -u

sec "timezone and ntp"
printf 'timezone %s\n' "$(timedatectl show -p Timezone --value 2>/dev/null)"
printf 'ntp-synchronized %s\n' "$(timedatectl show -p NTPSynchronized --value 2>/dev/null)"
if command -v chronyc >/dev/null 2>&1; then
  chronyc sources 2>/dev/null | awk 'NR>2{print $1, $2}' | sort
fi

sec "network interfaces (physical, by name and speed -- MACs omitted)"
for i in /sys/class/net/*; do
  n=$(basename "$i")
  [[ "$n" == "lo" || "$n" =~ ^(veth|tap|fwbr|fwln|fwpr|ifb) ]] && continue
  [[ -e "$i/device" ]] || continue
  printf '%s driver=%s speed=%s mtu=%s\n' "$n" \
    "$(basename "$(readlink -f "$i/device/driver" 2>/dev/null)" 2>/dev/null || echo '?')" \
    "$(cat "$i/speed" 2>/dev/null || echo '?')" \
    "$(cat "$i/mtu" 2>/dev/null || echo '?')"
done | sort

sec "bridges and their ports"
for b in /sys/class/net/*/bridge; do
  [[ -d "$b" ]] || continue
  br=$(basename "$(dirname "$b")")
  printf '%s ports=%s\n' "$br" \
    "$(ls "$(dirname "$b")/brif" 2>/dev/null | sort | paste -sd, -)"
done | sort

sec "/etc/network/interfaces (comments and blank lines stripped)"
grep -vE '^[[:space:]]*(#|$)' /etc/network/interfaces 2>/dev/null

sec "storage configuration"
grep -vE '^[[:space:]]*(#|$)' /etc/pve/storage.cfg 2>/dev/null | redact

sec "storage status (content types and availability)"
pvesm status 2>/dev/null | awk 'NR>1{print $1, $2, $3}' | sort

sec "cluster"
if [[ -f /etc/pve/corosync.conf ]]; then
  # Keep structure and addressing, drop the version counter that bumps on
  # every edit and would otherwise show as a false difference.
  grep -vE '^[[:space:]]*(#|$)' /etc/pve/corosync.conf | grep -vE 'config_version'
else
  echo "STANDALONE (no corosync.conf)"
fi

sec "quorum"
pvecm status 2>/dev/null | grep -E 'Quorate|Expected votes|Total votes|Qdevice|Membership' || echo "not clustered"

sec "qdevice"
if command -v corosync-qdevice-tool >/dev/null 2>&1; then
  corosync-qdevice-tool -s 2>/dev/null | grep -E 'Model|State|Algorithm|Tie-breaker' || echo "qdevice not running"
else
  echo "corosync-qdevice-tool absent"
fi

sec "ha configuration"
ha-manager groupconfig 2>/dev/null || echo "no ha groups"
ha-manager config 2>/dev/null || echo "no ha resources"

sec "guests defined"
{ ls /etc/pve/qemu-server/*.conf 2>/dev/null; ls /etc/pve/lxc/*.conf 2>/dev/null; } \
  | xargs -r -n1 basename 2>/dev/null | sort || echo "none"

sec "enabled services (pve + cluster critical)"
for s in pve-cluster corosync corosync-qdevice pveproxy pvedaemon pvestatd pve-ha-lrm pve-ha-crm chrony chronyd nfs-client.target; do
  printf '%s %s\n' "$s" "$(systemctl is-enabled "$s" 2>/dev/null || echo 'n/a')"
done

sec "sysctl (non-default, network and memory)"
sysctl -a 2>/dev/null | grep -E '^(net\.ipv4\.ip_forward|net\.bridge|vm\.swappiness|net\.core\.(r|w)mem_max)' | sort

sec "cpu and memory class (expected to differ if hardware differs)"
printf 'cpu-model %s\n' "$(awk -F': ' '/model name/{print $2; exit}' /proc/cpuinfo)"
printf 'cpu-threads %s\n' "$(nproc)"
printf 'mem-total-gb %s\n' "$(awk '/MemTotal/{printf "%.0f", $2/1048576}' /proc/meminfo)"

sec "block devices and pools"
lsblk -dno NAME,SIZE,TYPE 2>/dev/null | sort
vgs --noheadings -o vg_name,vg_size 2>/dev/null | awk '{$1=$1;print}' | sort
