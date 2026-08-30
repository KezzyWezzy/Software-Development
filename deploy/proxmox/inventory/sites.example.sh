#!/usr/bin/env bash
# CTM Proxmox site inventory  --  COPY TO sites.sh AND FILL IN, DO NOT COMMIT sites.sh
#
# Sourced by bin/ctm-provision on the CONTROL machine (your laptop or a jump box
# on the plant network). Never copied to the Proxmox hosts.
#
# Prefilled to mirror the existing kjv1/kjv2 build (see docs/EXISTING-CLUSTER-kjv.md):
# three bridges, a Synology serving three NFS stores plus an iSCSI LUN, and a
# two-node cluster with a QDevice for the third vote.
#
# Every TODO must be replaced. Preflight refuses to run while one remains.

# ---------------------------------------------------------------------------
# Reference servers -- the EXISTING known-good pair the new servers must match.
# 'capture' reads their config; 'parity' diffs the new hosts against it. Both
# are read-only; nothing is ever written to these boxes.
#
# kjv2 is currently down. Capture whatever is reachable -- one healthy
# reference is enough to clone from, and parity will simply skip the absent one.
# ---------------------------------------------------------------------------
SITES=(line2 nash)

LINE2_REFERENCE_NODES="TODO"      # e.g. "192.168.50.110"  (kjv1)
NASH_REFERENCE_NODES="TODO"

# ---------------------------------------------------------------------------
# Line 2
# ---------------------------------------------------------------------------
LINE2_CLUSTER_NAME="ctm-line2"
LINE2_NODES=(line2-pve1 line2-pve2)

LINE2_PVE1_ADDR="TODO"            # mgmt IP of node 1 (reachable from here now)
LINE2_PVE2_ADDR="TODO"
LINE2_PVE1_RING0="TODO"           # corosync ring0. kjv uses the 192.168.100.0/24
LINE2_PVE2_RING0="TODO"           # bridge for this -- keep it off the panel VLAN.

LINE2_QDEVICE_ADDR="TODO"         # host running corosync-qnetd (see STAGING.md --
LINE2_QDEVICE_USER="root"         # on a Synology this is a Debian container, not DSM)

LINE2_TIMEZONE="America/Chicago"
LINE2_NTP_SERVERS="TODO"          # air-gapped: your local time source

# --- Bridges: bridge|iface|cidr|gateway|comment ------------------------------
# Mirrors kjv1's layout. Interface names are MAC-derived (enx*) and therefore
# DIFFERENT on every machine -- run preflight on each host to get its real
# names, then fill them in per node. Leave cidr empty for an unnumbered bridge.
#
# vmbr0 already exists from the PVE installer; it is listed for documentation
# and deliberately skipped rather than edited.
# Bridge specs are PER NODE. Each host has its own address on every bridge,
# and enx* NIC names are MAC-derived so they differ even between identical
# machines -- run preflight on each host to read its real names.
LINE2_PVE1_BRIDGES="
vmbr0|TODO|TODO|
|mgmt + corosync (kjv1: 192.168.100.0/24, no gateway)
vmbr1|TODO|TODO|TODO|panel VLAN -- kiosks live here (kjv1: 192.168.50.0/24, gw .1)
vmbr2|TODO|TODO|
|third network (kjv1: 192.168.12.0/24, no gateway)
"

LINE2_PVE2_BRIDGES="
vmbr0|TODO|TODO|
|mgmt + corosync
vmbr1|TODO|TODO|TODO|panel VLAN
vmbr2|TODO|TODO|
|third network
"

# --- Storage: type|id|server|path|content|extra ------------------------------
# type  nfs | cifs | iscsi | lvm
# path  nfs: export   cifs: share   iscsi: target IQN   lvm: vgname
#
# Mirrors the kjv cluster: three Synology NFS stores plus one iSCSI LUN.
# Confirm the real export paths, target IQN and content types from a capture of
# kjv1 before running -- the values below are the shape, not verified strings.
LINE2_STORAGE="
nfs|ds923-backups|TODO|TODO|backup|--options vers=4.1
nfs|ds923-iso|TODO|TODO|iso,vztmpl|--options vers=4.1
nfs|ds923-vm-disks|TODO|TODO|images,rootdir|--options vers=4.1
iscsi|ContinuumTMLUN01|TODO|TODO|none|
"

# ---------------------------------------------------------------------------
# Nash
# ---------------------------------------------------------------------------
NASH_CLUSTER_NAME="ctm-nash"
NASH_NODES=(nash-pve1 nash-pve2)

NASH_PVE1_ADDR="TODO"
NASH_PVE2_ADDR="TODO"
NASH_PVE1_RING0="TODO"
NASH_PVE2_RING0="TODO"

NASH_QDEVICE_ADDR="TODO"
NASH_QDEVICE_USER="root"

NASH_TIMEZONE="America/Chicago"
NASH_NTP_SERVERS="TODO"

# Bridge specs are PER NODE. Each host has its own address on every bridge,
# and enx* NIC names are MAC-derived so they differ even between identical
# machines -- run preflight on each host to read its real names.
NASH_PVE1_BRIDGES="
vmbr0|TODO|TODO|
|mgmt + corosync (kjv1: 192.168.100.0/24, no gateway)
vmbr1|TODO|TODO|TODO|panel VLAN -- kiosks live here (kjv1: 192.168.50.0/24, gw .1)
vmbr2|TODO|TODO|
|third network (kjv1: 192.168.12.0/24, no gateway)
"

NASH_PVE2_BRIDGES="
vmbr0|TODO|TODO|
|mgmt + corosync
vmbr1|TODO|TODO|TODO|panel VLAN
vmbr2|TODO|TODO|
|third network
"

NASH_STORAGE="
nfs|ds923-backups|TODO|TODO|backup|--options vers=4.1
nfs|ds923-iso|TODO|TODO|iso,vztmpl|--options vers=4.1
nfs|ds923-vm-disks|TODO|TODO|images,rootdir|--options vers=4.1
iscsi|ContinuumTMLUN01|TODO|TODO|none|
"

# ---------------------------------------------------------------------------
# Air-gap staging -- see offline/STAGING.md.
# Build the bundle on a host running the SAME PVE version as the targets.
# The existing cluster runs PVE 9.1.1 (Debian 13 base).
# ---------------------------------------------------------------------------
OFFLINE_BUNDLE_PATH="/opt/ctm-offline"

# SSH identity for every host. Key auth only -- password auth is rejected,
# because postinstall disables it and these runs are unattended. Seed the key
# on each host BEFORE the first postinstall run.
SSH_KEY="${HOME}/.ssh/id_ed25519_ctm"
SSH_USER="root"
