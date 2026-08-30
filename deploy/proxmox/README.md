# CTM Proxmox provisioning kit — Line 2 and Nash

Brings two freshly, manually installed Proxmox VE hosts per site up to the
point where the Continuum Terminal Manager server guest can be placed on them:
repos and time sorted for an air-gapped network, a panel-VLAN bridge, a
two-node cluster with an external QDevice on the NAS, NAS storage, and an HA
group.

## Where this runs

**On a control machine that is already on the plant network** — your laptop or
a jump box — not on the Proxmox hosts. It drives them over SSH.

Nothing here can run from a cloud session; the OT network is not routable from
outside. That is also why every stage is idempotent: you will be re-running
these at the terminal, on a laptop, probably twice.


## Matching two new servers to the existing pair

This is the common case: two servers are already running and correct, and two
new ones have to end up identical to them. Treat that as a cloning problem —
read the golden config off the working pair, then diff the new hosts against
it — rather than re-deriving values by hand into the inventory.

```bash
# 1. Snapshot the known-good servers. Read-only; writes nothing to them.
./bin/ctm-provision line2 capture

# 2. Snapshot the new servers and diff them against that baseline.
./bin/ctm-provision line2 parity
```

Set `*_REFERENCE_NODES` in the inventory to the existing pair, most
authoritative first. If the two references disagree with each other, `parity`
says so before cloning either — an ambiguous baseline is worth knowing about
before you copy it onto two more machines.

`parity` classifies every section three ways, so the report is about real
divergence rather than noise:

| Marker | Meaning |
|---|---|
| `[ ok ]` | matches |
| `~ differs (expected)` | hostname, CPU/RAM, disks, live vote counts — never counted as drift |
| `[DRIFT]` | a real difference, with a unified diff of exactly what |

Sections that carry identifiers — `/etc/network/interfaces`, `corosync.conf`,
`storage.cfg`, the HA config — are compared with IPs, node names, cluster name
and HA group name masked. This matters because a new site forms its **own**
cluster: its cluster name, node names and group name are all legitimately
different from the reference, while the shape must match exactly. So a new
two-node cluster with a QDevice and a `nofailback` group passes clean no matter
what it is called, but a missing QDevice, a missing `nofailback`, a single-node
cluster, a changed bridge port or a missing storage definition are all still
reported as drift.

Then close each `[DRIFT]` with the stage that owns it (`postinstall` for repos,
time and packages; `network` for bridges; `storage` for the NAS) and re-run
`parity` until it comes back clean.

### Capturing without filling in the inventory

The capture scripts are self-contained and take no arguments, so you can pipe
one over SSH directly — no inventory, no baseline directory, nothing to set up:

```bash
# a Proxmox host
ssh root@<existing-server> "bash -s" < scripts/01-capture.sh > existing-1.capture

# the NAS / QDevice host
ssh root@<nas> "bash -s" < scripts/02-capture-nas.sh > nas.capture
```

Both are read-only and write nothing to the host. This is the fastest way to
get a full picture of a running system.

`02-capture-nas.sh` covers the NAS side specifically: platform and package
manager (which decides whether `corosync-qnetd` can be installed natively or
needs a Debian container), qnetd service state, the clusters qnetd is actually
arbitrating for, NFS exports, listening ports (5403/2049/111), pools, and
whether root SSH is set up — `pvecm qdevice setup` drives the NAS over SSH as
root, so that last one is a prerequisite, not a detail.

### Captured files hold plant addressing

`baseline/` is gitignored. Capture redacts anything matching
`password|secret|token|key`, and never reads `/etc/pve/priv`, but the snapshots
still contain your addressing and topology. Check one before sharing it.

## Prerequisites

- Proxmox VE installed manually on both hosts at each site, reachable by IP.
- An SSH keypair authorised for `root` on every host **before you start** —
  the post-install stage disables password authentication, so seed the key
  first or you will lock yourself out:
  ```bash
  ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519_ctm
  ssh-copy-id -i ~/.ssh/id_ed25519_ctm root@<host>   # while passwords still work
  ```
- The offline package bundle staged on each host — see
  [`offline/STAGING.md`](offline/STAGING.md).

## Setup

```bash
cp inventory/sites.example.sh inventory/sites.sh
$EDITOR inventory/sites.sh        # replace every TODO
```

`inventory/sites.sh` holds plant addressing and is git-ignored. Keep it out of
the repo.

## Running it

```bash
cd deploy/proxmox

./bin/ctm-provision line2 preflight            # read-only, run this first
./bin/ctm-provision line2 all --dry-run        # print every command, change nothing
./bin/ctm-provision line2 all
```

Or stage by stage, which is what you want the first time through:

| Stage | What it does | Risk |
|---|---|---|
| `capture` | Snapshots the reference servers into `baseline/`. Read-only. | none |
| `parity` | Snapshots the new servers and diffs against the baseline. Read-only. | none |
| `preflight` | Reads versions, NICs, storage, clock, bundle. Changes nothing. | none |
| `postinstall` | Disables enterprise/internet repos, builds the local apt repo, sets timezone + NTP, installs baseline packages, enforces key-only SSH. | low |
| `network` | Adds `vmbr1` for the panel VLAN. Never touches `vmbr0`. | medium — see below |
| `cluster` | Creates the cluster on node 1, joins node 2. | **destructive on node 2** |
| `qdevice` | Installs `corosync-qnetd` on the NAS, registers it. | low |
| `storage` | Adds every storage in the spec (nfs/cifs/iscsi/lvm). | low |
| `ha` | Creates the HA group. Refuses to run without a QDevice. | low |

`--dry-run` prints every remote command without executing. `--yes` skips the
confirmation prompts on `network` and `cluster` — only for a re-run you have
already done interactively.

## The three things most likely to bite

**Node 2 loses its config when it joins.** `pvecm add` replaces `/etc/pve` with
the cluster's copy. Both join scripts abort if the node has any guest defined,
but if you configured storage or users on node 2 first, that is gone. Do the
cluster stage before anything else that writes to `/etc/pve`.

**The network stage can strand a host.** It only ever *adds* bridges that do
not exist — an existing `vmbr0` is skipped, never edited — and it refuses a NIC
already enslaved elsewhere. It restores the previous `/etc/network/interfaces`
if `ifreload` fails.

**Bridge specs are per node, not per site.** Each host has its own address on
every bridge, and `enx*` names are MAC-derived so they differ even between
identical machines. `*_PVE1_BRIDGES` and `*_PVE2_BRIDGES` are separate for that
reason — sharing one spec would hand node 2 node 1's addresses and collide on
the panel VLAN. Run `preflight` on each host to read its real NIC names. But if `ifupdown2` is
not installed it writes the config without applying it and tells you to apply it
at the physical console — do that, do not reboot and hope.

**HA fences by watchdog.** A node that goes non-quorate for ~60s hard-resets
itself. On a loading terminal that drops whatever bay the node was serving. The
QDevice is what keeps a single link blip from causing it, which is why
`60-ha.sh` refuses to configure HA until `pvecm status` shows a Qdevice line.
Check that line before you rely on failover.

## Verifying a site

```bash
ssh root@<node1> pvecm status      # Quorate: Yes, Expected votes: 3, Qdevice line present
ssh root@<node1> ha-manager status
ssh root@<node1> pvesm status
ssh root@<node1> ip -br addr show vmbr1
```

Three votes with both nodes and the QDevice online is the shape you want. Two
means the QDevice did not register.

## What this kit does not do yet

Creating the CTM server guest and configuring the application itself —
PostgreSQL, Redis, the MQTT broker, and the per-kiosk nginx listeners — is not
covered here. See [`../../docs/CTM-SITE-CONVENTIONS.md`](../../docs/CTM-SITE-CONVENTIONS.md)
for the addressing and port conventions those stages must follow, taken from
the verified Red River build.
