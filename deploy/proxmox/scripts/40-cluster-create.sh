# Runs ON node 1. Creates the cluster. Refuses if the node is already clustered.
# env in: CLUSTER_NAME RING0_ADDR
set -euo pipefail

# Remote scripts arrive via `ssh host "bash -s"`, a non-login shell whose PATH
# is not guaranteed to include sbin -- where ip, pvecm, pvesm and pvesh all live.
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
say() { printf '  %s\n' "$*"; }

if [[ -f /etc/pve/corosync.conf ]]; then
  say "already clustered as '$(awk -F': *' '/cluster_name/{print $2}' /etc/pve/corosync.conf | tr -d ' ')' -- nothing to do"
  exit 0
fi

# A node with guests on it cannot join/found a cluster cleanly -- Proxmox
# requires an empty guest inventory, and VMIDs would collide anyway.
if [[ -n "$(ls -A /etc/pve/qemu-server 2>/dev/null)$(ls -A /etc/pve/lxc 2>/dev/null)" ]]; then
  say "ERROR: this node already has guests defined. Move or destroy them first."
  exit 1
fi

pvecm create "$CLUSTER_NAME" --link0 "$RING0_ADDR"
say "cluster '$CLUSTER_NAME' created on link0 ${RING0_ADDR}"
sleep 3
pvecm status | sed 's/^/    /'
