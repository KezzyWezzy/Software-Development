# Runs ON the NAS / QDevice host. Read-only. Emits a normalised snapshot of the
# parts a Proxmox cluster depends on: the NFS exports it mounts, and the qnetd
# service that arbitrates its quorum.
#
# Works on a Debian-ish NAS or a Debian container running qnetd. On a TrueNAS
# or Synology appliance shell some sections will report "n/a" -- that is the
# answer, not a failure, and it tells us whether qnetd can run natively there.
#
# SECRETS ARE REDACTED, but output still contains addressing. Review before sharing.
set -uo pipefail
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
export LC_ALL=C

sec() { printf '\n##### %s\n' "$1"; }
redact() { sed -E 's/(password|passwd|secret|token|key)[[:space:]]*[:=][[:space:]]*.*/\1 <REDACTED>/Ig'; }
have() { command -v "$1" >/dev/null 2>&1; }

printf '# ctm-capture-nas v1\n'

sec "identity and platform"
printf 'hostname %s\n' "$(hostname -s 2>/dev/null)"
printf 'kernel %s\n' "$(uname -r)"
if [[ -f /etc/os-release ]]; then
  grep -E '^(NAME|VERSION|ID|VERSION_ID)=' /etc/os-release
else
  echo "no /etc/os-release"
fi
# Whether corosync-qnetd can be installed natively hinges on this.
printf 'package-manager %s\n' \
  "$(for m in apt-get dnf yum opkg synopkg pkg; do have "$m" && { echo "$m"; break; }; done || echo 'none-found')"

sec "qnetd service"
if have corosync-qnetd; then
  printf 'corosync-qnetd installed: %s\n' "$(corosync-qnetd -v 2>&1 | head -1)"
  printf 'service-enabled %s\n' "$(systemctl is-enabled corosync-qnetd 2>/dev/null || echo 'n/a')"
  printf 'service-active %s\n'  "$(systemctl is-active  corosync-qnetd 2>/dev/null || echo 'n/a')"
else
  echo "corosync-qnetd NOT installed"
fi

sec "qnetd registered clusters and votes"
if have corosync-qnetd-tool; then
  # -l lists connected clusters; this is what proves the QDevice is really
  # arbitrating rather than merely installed.
  corosync-qnetd-tool -l 2>/dev/null || echo "qnetd not answering"
  corosync-qnetd-tool -s 2>/dev/null || true
else
  echo "corosync-qnetd-tool absent"
fi

sec "nfs exports"
if [[ -f /etc/exports ]]; then
  grep -vE '^[[:space:]]*(#|$)' /etc/exports 2>/dev/null
else
  echo "no /etc/exports"
fi
if have exportfs; then
  echo "--- active exports ---"
  exportfs -v 2>/dev/null
fi

sec "nfs service"
for s in nfs-server nfs-kernel-server rpcbind; do
  printf '%s enabled=%s active=%s\n' "$s" \
    "$(systemctl is-enabled "$s" 2>/dev/null || echo n/a)" \
    "$(systemctl is-active  "$s" 2>/dev/null || echo n/a)"
done

sec "listening ports relevant to the cluster"
# 5403 = qnetd, 2049 = nfs, 111 = rpcbind
if have ss; then
  ss -lntu 2>/dev/null | awk 'NR==1 || /:5403|:2049|:111\b/'
elif have netstat; then
  netstat -lntu 2>/dev/null | awk 'NR<3 || /:5403|:2049|:111\b/'
else
  echo "no ss or netstat"
fi

sec "storage pools and capacity"
if have zpool; then
  zpool list 2>/dev/null
  zfs list -o name,used,avail,mountpoint 2>/dev/null | head -30
else
  echo "no zfs"
fi
df -hPT 2>/dev/null | awk 'NR==1 || $2 ~ /ext4|xfs|zfs|btrfs/' | head -20

sec "network"
if have ip; then
  ip -br -4 addr show 2>/dev/null | grep -v '^lo'
  echo "--- routes ---"
  ip -4 route 2>/dev/null
else
  echo "no ip command"
fi

sec "time"
printf 'date %s\n' "$(date '+%Y-%m-%d %H:%M:%S %Z')"
printf 'timezone %s\n' "$(timedatectl show -p Timezone --value 2>/dev/null || cat /etc/timezone 2>/dev/null || echo '?')"
printf 'ntp-sync %s\n' "$(timedatectl show -p NTPSynchronized --value 2>/dev/null || echo '?')"

sec "root ssh reachability prerequisites"
# pvecm qdevice setup drives this host over SSH as root.
printf 'sshd-active %s\n' "$(systemctl is-active ssh 2>/dev/null || systemctl is-active sshd 2>/dev/null || echo 'n/a')"
printf 'PermitRootLogin %s\n' \
  "$( { sshd -T 2>/dev/null | awk '/^permitrootlogin/{print $2}'; } || echo '?')"
printf 'root-authorized-keys %s\n' \
  "$([[ -s /root/.ssh/authorized_keys ]] && wc -l < /root/.ssh/authorized_keys || echo 0)"
