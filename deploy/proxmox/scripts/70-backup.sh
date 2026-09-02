# Runs ON a Proxmox host. Produces the artifacts needed to rebuild this node's
# workload somewhere else: guest backups, plus a config archive.
#
# READ docs/BACKUP-RESTORE.md BEFORE RESTORING ANY OF THIS.
# The two halves have completely different restore rules:
#
#   guests      restorable as-is onto another cluster. This is the good path --
#               it clones the CTM server rather than rebuilding it.
#   host config REFERENCE ONLY for most of it. /etc/pve carries this node's
#               identity: node name, cluster membership, certificates. Copying
#               it onto a new host makes that host believe it IS this one.
#
# Deliberately NOT collected: /etc/pve/priv (cluster private keys and CA),
# /etc/corosync/authkey, /var/lib/pve-cluster/config.db. Those are identity, not
# configuration -- carrying them to another machine is how you get two nodes
# claiming the same name on one segment.
#
# env in: BACKUP_STORAGE   pvesm storage id with 'backup' content
#         VMIDS            space-separated guest ids, or "all"
#         MODE             snapshot | suspend | stop   (default snapshot)
#         CONFIG_ONLY      1 to skip guest backups
set -euo pipefail
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
say() { printf '  %s\n' "$*"; }

STAMP="$(date +%Y%m%d-%H%M%S)"
HOST="$(hostname -s)"

# --- 1. Guest backups -------------------------------------------------------
if [[ "${CONFIG_ONLY:-0}" != "1" ]]; then
  [[ -n "${BACKUP_STORAGE:-}" ]] || { say "ERROR: BACKUP_STORAGE unset"; exit 1; }
  pvesm status --storage "$BACKUP_STORAGE" >/dev/null 2>&1 \
    || { say "ERROR: storage '$BACKUP_STORAGE' not defined on this node"; exit 1; }

  # The storage must accept backups, or vzdump fails only after doing the work.
  if ! pvesm status --content backup 2>/dev/null | awk 'NR>1{print $1}' | grep -qx "$BACKUP_STORAGE"; then
    say "ERROR: storage '$BACKUP_STORAGE' does not carry 'backup' content"
    exit 1
  fi

  mode="${MODE:-snapshot}"
  case "$mode" in
    snapshot|suspend|stop) ;;
    *) say "ERROR: MODE must be snapshot, suspend or stop"; exit 1 ;;
  esac
  # snapshot keeps guests running; the others interrupt service. On a terminal
  # that is a loading outage, so it must be a deliberate choice.
  [[ "$mode" != "snapshot" ]] && say "NOTE: mode '${mode}' will interrupt the guests"

  if [[ "${VMIDS:-all}" == "all" ]]; then
    say "backing up ALL guests on ${HOST} (mode=${mode})"
    vzdump --all --storage "$BACKUP_STORAGE" --mode "$mode" --compress zstd --quiet 1
  else
    for id in ${VMIDS}; do
      if [[ ! -f "/etc/pve/qemu-server/${id}.conf" && ! -f "/etc/pve/lxc/${id}.conf" ]]; then
        say "ERROR: no guest ${id} on this node"; exit 1
      fi
    done
    say "backing up guests: ${VMIDS} (mode=${mode})"
    # shellcheck disable=SC2086
    vzdump ${VMIDS} --storage "$BACKUP_STORAGE" --mode "$mode" --compress zstd --quiet 1
  fi
  say "guest backups written to storage '${BACKUP_STORAGE}'"
fi

# --- 2. Host and cluster configuration --------------------------------------
# Everything here is for reading and for selective, deliberate reuse. See the
# restore matrix in docs/BACKUP-RESTORE.md for what may be copied verbatim.
OUT="/var/tmp/ctm-config-${HOST}-${STAMP}"
mkdir -p "$OUT"/{host,cluster,reference}

for f in /etc/network/interfaces /etc/hostname /etc/hosts /etc/resolv.conf \
         /etc/timezone /etc/fstab; do
  [[ -f "$f" ]] && cp -a "$f" "$OUT/host/" 2>/dev/null || true
done
for d in /etc/chrony /etc/apt/sources.list.d /etc/ssh/sshd_config.d /etc/systemd/network; do
  [[ -d "$d" ]] && cp -a "$d" "$OUT/host/" 2>/dev/null || true
done
[[ -f /etc/apt/sources.list ]] && cp -a /etc/apt/sources.list "$OUT/host/"

# Cluster-wide files. These are shared across the cluster and come to a new node
# automatically when it JOINS -- they are captured for reading, not for copying.
for f in storage.cfg datacenter.cfg user.cfg vzdump.cron jobs.cfg corosync.conf; do
  [[ -f "/etc/pve/$f" ]] && cp -a "/etc/pve/$f" "$OUT/cluster/" 2>/dev/null || true
done
[[ -d /etc/pve/ha ]] && cp -a /etc/pve/ha "$OUT/cluster/" 2>/dev/null || true
[[ -d /etc/pve/firewall ]] && cp -a /etc/pve/firewall "$OUT/cluster/" 2>/dev/null || true

# Guest definitions, so a config can be read even without unpacking a backup.
mkdir -p "$OUT/cluster/guests"
cp -a /etc/pve/qemu-server/*.conf "$OUT/cluster/guests/" 2>/dev/null || true
cp -a /etc/pve/lxc/*.conf         "$OUT/cluster/guests/" 2>/dev/null || true

# Human-readable state that no file captures.
{
  echo "# ctm host state  ${HOST}  ${STAMP}"
  echo; echo "## pveversion"; pveversion 2>/dev/null
  echo; echo "## pvecm status"; pvecm status 2>/dev/null
  echo; echo "## pvesm status"; pvesm status 2>/dev/null
  echo; echo "## ha-manager"; ha-manager status 2>/dev/null; ha-manager groupconfig 2>/dev/null
  echo; echo "## addresses"; ip -br -4 addr 2>/dev/null
  echo; echo "## bridges"
  for b in /sys/class/net/*/bridge; do [[ -d "$b" ]] || continue
    br=$(basename "$(dirname "$b")")
    echo "$br ports=$(ls "$(dirname "$b")/brif" 2>/dev/null | paste -sd, -)"
  done
  echo; echo "## installed pve packages"
  dpkg-query -W -f='${Package} ${Version}\n' 2>/dev/null | grep -E '^(pve|proxmox|corosync)' | sort
} > "$OUT/reference/state.txt" 2>&1

# Redact anything credential-shaped before the archive leaves the host.
grep -rlE '(password|secret|token)' "$OUT" 2>/dev/null | while read -r f; do
  sed -i -E 's/(password|passwd|secret|token)[[:space:]]*[:=][[:space:]]*.*/\1 <REDACTED>/Ig' "$f"
  say "redacted credentials in $(basename "$f")"
done

cat > "$OUT/README.txt" <<'NOTE'
CTM host configuration archive.

host/       this machine's own files. Addresses and NIC names are specific to
            it; enx* names are MAC-derived and will NOT match another machine.
cluster/    cluster-wide files. A node that JOINS the cluster receives these
            automatically. Do not copy them onto a node by hand.
reference/  captured runtime state. Read-only record.

NOT INCLUDED, deliberately: /etc/pve/priv, /etc/corosync/authkey,
/var/lib/pve-cluster/config.db. Those carry cluster identity and private keys.

See docs/BACKUP-RESTORE.md for what may be restored and what must be rebuilt.
NOTE

TAR="/var/tmp/ctm-config-${HOST}-${STAMP}.tar.gz"
tar -czf "$TAR" -C /var/tmp "$(basename "$OUT")"
rm -rf "$OUT"
say "config archive: ${TAR}  ($(du -h "$TAR" | cut -f1))"
say "copy it off this host, then delete it -- it contains plant addressing"
