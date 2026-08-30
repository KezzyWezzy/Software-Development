# Runs ON the NAS / third host that provides the tie-breaking vote.
# Installs the corosync QNet daemon. This host is NOT a Proxmox node and never
# runs guests -- it only arbitrates quorum for the two-node cluster.
set -euo pipefail

# Remote scripts arrive via `ssh host "bash -s"`, a non-login shell whose PATH
# is not guaranteed to include sbin -- where ip, pvecm, pvesm and pvesh all live.
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
say() { printf '  %s\n' "$*"; }

if ! command -v corosync-qnetd >/dev/null 2>&1; then
  export DEBIAN_FRONTEND=noninteractive
  apt-get install -y --no-install-recommends corosync-qnetd \
    || { say "ERROR: corosync-qnetd unavailable. On a non-Debian NAS (TrueNAS,"
         say "       Synology) run qnetd in a Debian container instead -- see"
         say "       offline/STAGING.md."; exit 1; }
  say "installed corosync-qnetd"
fi

systemctl enable --now corosync-qnetd
systemctl is-active --quiet corosync-qnetd \
  && say "corosync-qnetd active" \
  || { say "ERROR: corosync-qnetd failed to start"; exit 1; }

# pvecm qdevice setup drives this host over SSH as root from a cluster node.
say "qnetd ready; cluster nodes must be able to SSH here as root"
