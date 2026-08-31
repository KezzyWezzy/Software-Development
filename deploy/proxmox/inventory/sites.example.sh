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
SITES=(rrsouth)

RRSOUTH_REFERENCE_NODES="TODO"      # e.g. "192.168.50.110"  (kjv1)

# ---------------------------------------------------------------------------
# Red River South Terminal
# ---------------------------------------------------------------------------
RRSOUTH_CLUSTER_NAME="ctm-rrsouth"
RRSOUTH_NODES=(rrs-pve1 rrs-pve2)

RRSOUTH_PVE1_ADDR="TODO"            # mgmt IP of node 1 (reachable from here now)
RRSOUTH_PVE2_ADDR="TODO"
RRSOUTH_PVE1_RING0="TODO"           # corosync ring0. kjv uses the 192.168.100.0/24
RRSOUTH_PVE2_RING0="TODO"           # bridge for this -- keep it off the panel VLAN.

RRSOUTH_QDEVICE_ADDR="TODO"         # host running corosync-qnetd (see STAGING.md --
RRSOUTH_QDEVICE_USER="root"         # on a Synology this is a Debian container, not DSM)

# Subnets deliberately renumbered at this site, as "from=to" prefixes.
# The panel VLAN moves 192.168.50.x -> 192.168.51.x; 192.168.100.x is kept
# identical to the existing cluster. Parity applies this to the baseline so
# the intended change does not read as drift, while still catching a host
# left on the old subnet or renumbered to the wrong one.
RRSOUTH_SUBNET_REMAP="192.168.50=192.168.51"

RRSOUTH_TIMEZONE="America/Chicago"
RRSOUTH_NTP_SERVERS="TODO"          # air-gapped: your local time source

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
RRSOUTH_PVE1_BRIDGES="
vmbr0|TODO|TODO|
|mgmt + corosync -- 192.168.100.0/24, SAME as existing, no gateway
vmbr1|TODO|TODO|TODO|panel VLAN -- NEW SITE USES 192.168.51.0/24, gw .51.1
vmbr2|TODO|TODO|
|third network (kjv1: 192.168.12.0/24, no gateway)
"

RRSOUTH_PVE2_BRIDGES="
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
RRSOUTH_STORAGE="
nfs|ds923-backups|TODO|TODO|backup|--options vers=4.1
nfs|ds923-iso|TODO|TODO|iso,vztmpl|--options vers=4.1
nfs|ds923-vm-disks|TODO|TODO|images,rootdir|--options vers=4.1
iscsi|ContinuumTMLUN01|TODO|TODO|none|
"

# To add another site: copy the block above, change the prefix, and add the
# lowercase key to SITES.

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
