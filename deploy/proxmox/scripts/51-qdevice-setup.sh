# Runs ON node 1, after both nodes are in the cluster and qnetd is up.
# Registers the external QDevice so the two-node cluster has three votes.
#
# Without this, a two-node cluster loses quorum the moment either node drops:
# expected_votes=2, so one survivor holds 1 vote and cannot act. The QDevice
# gives the survivor a second vote, which is what makes HA failover possible.
#
# env in: QDEVICE_ADDR
set -euo pipefail

# Remote scripts arrive via `ssh host "bash -s"`, a non-login shell whose PATH
# is not guaranteed to include sbin -- where ip, pvecm, pvesm and pvesh all live.
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
say() { printf '  %s\n' "$*"; }

[[ -f /etc/pve/corosync.conf ]] || { say "ERROR: not in a cluster yet"; exit 1; }

if pvecm status 2>/dev/null | grep -qi 'Qdevice'; then
  say "QDevice already configured"
  pvecm status | sed 's/^/    /'
  exit 0
fi

# All nodes must be online, or the QDevice registration writes a corosync.conf
# that the absent node never receives.
if ! pvecm status | grep -qi 'Quorate: *Yes'; then
  say "ERROR: cluster is not quorate; bring both nodes up before adding a QDevice"
  exit 1
fi

pvecm qdevice setup "$QDEVICE_ADDR" -f
sleep 3
pvecm status | sed 's/^/    /'

if pvecm status | grep -qi 'Qdevice'; then
  say "QDevice registered at ${QDEVICE_ADDR}"
else
  say "ERROR: QDevice did not appear in pvecm status"
  exit 1
fi
