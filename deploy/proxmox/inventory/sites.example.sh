#!/usr/bin/env bash
# CTM Proxmox site inventory  --  COPY TO sites.sh AND FILL IN, DO NOT COMMIT sites.sh
#
# Sourced by bin/ctm-provision on the CONTROL machine (your laptop / jump box on
# the plant network). Never copied to the Proxmox hosts.
#
# Conventions come from the verified Red River build (see docs/CTM-SITE-CONVENTIONS.md):
#   panel VLAN            192.168.50.0/24
#   CTM server            .129
#   per-kiosk nginx port  7001 + bay index
#
# Every value marked TODO must be replaced before any script will run; preflight
# refuses to continue while a TODO remains.


# ---------------------------------------------------------------------------
# Reference servers -- the EXISTING, known-good pair the new servers must match.
# The 'capture' stage reads their config; 'parity' diffs the new hosts against
# it. Both are read-only on these boxes; nothing is ever written to them.
#
# List the working pair, most-authoritative first. If the two disagree, parity
# says so rather than silently cloning whichever came first.
# ---------------------------------------------------------------------------
LINE2_REFERENCE_NODES="TODO TODO"   # e.g. "10.20.30.11 10.20.30.12"
NASH_REFERENCE_NODES="TODO TODO"

# ---------------------------------------------------------------------------
# Sites. Add one block per site. SITES lists which blocks are active.
# ---------------------------------------------------------------------------
SITES=(line2 nash)

# ---- Line 2 ---------------------------------------------------------------
# Two Proxmox hosts in one cluster + a QDevice on the NAS for the third vote.
LINE2_CLUSTER_NAME="ctm-line2"
LINE2_NODES=(line2-pve1 line2-pve2)

LINE2_PVE1_ADDR="TODO"          # mgmt IP of node 1, e.g. 10.20.30.11
LINE2_PVE2_ADDR="TODO"          # mgmt IP of node 2
LINE2_PVE1_RING0="TODO"         # corosync ring0 IP on node 1 (dedicated NIC if you have one)
LINE2_PVE2_RING0="TODO"

LINE2_QDEVICE_ADDR="TODO"       # NAS IP running corosync-qnetd
LINE2_QDEVICE_USER="root"       # qnetd host login used once during setup

LINE2_MGMT_CIDR="TODO"          # e.g. 10.20.30.0/24
LINE2_MGMT_GW="TODO"
LINE2_MGMT_IFACE="TODO"         # physical NIC for vmbr0, e.g. eno1  (preflight prints candidates)

LINE2_PANEL_CIDR="192.168.50.0/24"
LINE2_PANEL_IFACE="TODO"        # physical NIC for vmbr1 (panel VLAN), e.g. eno2
LINE2_PANEL_VLAN=""             # VLAN tag, or "" if the panel NIC is untagged/access

LINE2_CTM_SERVER_IP="192.168.50.129"
LINE2_NTP_SERVERS="TODO"        # air-gapped: your local NTP/PTP source, space separated
LINE2_TIMEZONE="America/Chicago"

LINE2_NAS_STORAGE_HOST="TODO"   # NAS IP serving NFS to the cluster
LINE2_NAS_STORAGE_EXPORT="TODO" # e.g. /mnt/pool0/ctm-line2
LINE2_NAS_STORAGE_ID="nas-line2"

# ---- Nash -----------------------------------------------------------------
NASH_CLUSTER_NAME="ctm-nash"
NASH_NODES=(nash-pve1 nash-pve2)

NASH_PVE1_ADDR="TODO"
NASH_PVE2_ADDR="TODO"
NASH_PVE1_RING0="TODO"
NASH_PVE2_RING0="TODO"

NASH_QDEVICE_ADDR="TODO"
NASH_QDEVICE_USER="root"

NASH_MGMT_CIDR="TODO"
NASH_MGMT_GW="TODO"
NASH_MGMT_IFACE="TODO"

NASH_PANEL_CIDR="192.168.50.0/24"
NASH_PANEL_IFACE="TODO"
NASH_PANEL_VLAN=""

NASH_CTM_SERVER_IP="192.168.50.129"
NASH_NTP_SERVERS="TODO"
NASH_TIMEZONE="America/Chicago"

NASH_NAS_STORAGE_HOST="TODO"
NASH_NAS_STORAGE_EXPORT="TODO"
NASH_NAS_STORAGE_ID="nas-nash"

# ---------------------------------------------------------------------------
# Air-gap staging. See offline/STAGING.md.
# ---------------------------------------------------------------------------
# Path ON EACH PVE HOST where the offline bundle has been unpacked. The
# post-install script builds a local apt repo from here instead of reaching
# out to enterprise.proxmox.com.
OFFLINE_BUNDLE_PATH="/opt/ctm-offline"

# SSH identity used to reach every host. Key auth only -- password auth is
# rejected by preflight, because these runs are unattended.
SSH_KEY="${HOME}/.ssh/id_ed25519_ctm"
SSH_USER="root"
