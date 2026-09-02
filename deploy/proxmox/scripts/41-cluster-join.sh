# Runs ON node 2. Joins the cluster founded on node 1.
# Uses --use_ssh because password auth is disabled by the post-install stage;
# the driver has already exchanged root SSH keys between the two nodes.
# env in: PEER_RING0 RING0_ADDR
set -euo pipefail

# Remote scripts arrive via `ssh host "bash -s"`, a non-login shell whose PATH
# is not guaranteed to include sbin -- where ip, pvecm, pvesm and pvesh all live.
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
say() { printf '  %s\n' "$*"; }

if [[ -f /etc/pve/corosync.conf ]]; then
  say "already clustered -- nothing to do"
  exit 0
fi

if [[ -n "$(ls -A /etc/pve/qemu-server 2>/dev/null)$(ls -A /etc/pve/lxc 2>/dev/null)" ]]; then
  say "ERROR: this node has guests defined; joining would discard its config."
  exit 1
fi

# Joining REPLACES this node's /etc/pve with the cluster's copy.
pvecm add "$PEER_RING0" --link0 "$RING0_ADDR" --use_ssh
say "joined cluster via ${PEER_RING0}"
sleep 5
pvecm status | sed 's/^/    /'
