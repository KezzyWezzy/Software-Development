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
| `preflight` | Reads versions, NICs, storage, clock, bundle. Changes nothing. | none |
| `postinstall` | Disables enterprise/internet repos, builds the local apt repo, sets timezone + NTP, installs baseline packages, enforces key-only SSH. | low |
| `network` | Adds `vmbr1` for the panel VLAN. Never touches `vmbr0`. | medium — see below |
| `cluster` | Creates the cluster on node 1, joins node 2. | **destructive on node 2** |
| `qdevice` | Installs `corosync-qnetd` on the NAS, registers it. | low |
| `storage` | Attaches the NAS over NFS. | low |
| `ha` | Creates the HA group. Refuses to run without a QDevice. | low |

`--dry-run` prints every remote command without executing. `--yes` skips the
confirmation prompts on `network` and `cluster` — only for a re-run you have
already done interactively.

## The three things most likely to bite

**Node 2 loses its config when it joins.** `pvecm add` replaces `/etc/pve` with
the cluster's copy. Both join scripts abort if the node has any guest defined,
but if you configured storage or users on node 2 first, that is gone. Do the
cluster stage before anything else that writes to `/etc/pve`.

**The network stage can strand a host.** It only ever appends `vmbr1` and
explicitly refuses to use a NIC already enslaved to `vmbr0`, and it restores the
previous `/etc/network/interfaces` if `ifreload` fails. But if `ifupdown2` is
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
