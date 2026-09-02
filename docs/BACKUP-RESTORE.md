# Backing up Red River and deploying to the new units

Short answer: **yes for the guests, partly for the Proxmox hosts, and no for
the NAS identity.** Those three are different problems and treating them the
same is how a clone takes down the terminal it was copied from.

## The restore matrix

| Layer | Backup | Restore to a new unit |
|---|---|---|
| **Guests** (CTM server, ContinuumHost) | `vzdump` → NAS | **Yes, restore as-is.** This is the good path. |
| Cluster-wide config (`storage.cfg`, users, HA groups) | captured for reading | **No — comes free.** A node that joins the cluster receives it. |
| Per-host config (`interfaces`, hostname, NTP) | captured for reading | **Reference only.** Addresses and `enx*` names are machine-specific. |
| Cluster identity (`/etc/pve/priv`, `config.db`, corosync authkey) | **never captured** | **Never.** See below. |
| NAS shares, exports, iSCSI target | recreated by the storage stage | **Recreate, don't restore.** |
| DSM system configuration (`.dss`) | Synology Configuration Backup | **Reference only.** Carries identity. |

## Guests — restore them, don't rebuild them

The CTM server is the one thing genuinely worth cloning. It carries the
application, the database, the nginx listeners and years of accumulated
configuration that nobody has written down.

```bash
# On kjv1 — snapshot mode keeps the guests running
./bin/ctm-provision rrsouth backup

# On the new cluster
ssh root@rrs-pve1 "bash -s" < scripts/71-restore-guest.sh \
  ARCHIVE=/mnt/pve/ds923-backups/dump/vzdump-qemu-101-....vma.zst \
  NEW_VMID=101 TARGET_STORAGE=<south-storage>
```

### The restored guest must not be started as-is

**This is the trap.** A restored guest carries the original host's network
configuration *inside its own OS*. The CTM server comes back believing it is
`192.168.50.129`.

North and South share a Layer 2 domain. Booting that guest unmodified puts a
second machine on the wire claiming an address that already exists and is in
production at North — an ARP conflict on a live loading system, at the moment
you are least expecting it.

`71-restore-guest.sh` therefore **never starts the guest** and prints its
baked-in addressing so you can see exactly what it would have claimed. Before
starting it:

1. Check each `netN` bridge exists on the new host and is the intended one.
2. Change the address inside the guest OS — `192.168.50.129` → `192.168.51.129`.
3. Confirm nothing answers there: `arping -D -I vmbr1 -c 2 192.168.51.129`.
4. Update the `kiosk_devices` rows to the new `192.168.51.x` addresses, or the
   server returns 404 to `/kiosk.json` and the panels never identify themselves.

## Proxmox hosts — rebuild, don't image

It is tempting to image kjv1 and lay it down on the new hardware. Don't.

**`/etc/pve` is identity, not configuration.** It is a FUSE filesystem backed by
`/var/lib/pve-cluster/config.db`, and it holds the node's name, its cluster
membership, its certificates and its CA. Copy it and the new machine believes it
*is* `kjv1` — same node name, same certs, same cluster — while the real `kjv1`
is still running on the same segment. Proxmox has no way to reconcile that; you
get a split cluster and two hosts fighting over one identity.

Same reasoning for `/etc/corosync/authkey` and `/etc/pve/priv`. `70-backup.sh`
deliberately does not collect any of them.

What the config archive is *for*: reading. It tells you the package versions to
match in the offline bundle, the sysctls, the repo layout, the chrony sources,
and what the bridges actually looked like — so the provisioning stages reproduce
them on a clean install. That is what `parity` then verifies.

The one file worth copying by hand is nothing at all: `/etc/network/interfaces`
cannot be reused either, because `enx*` names are MAC-derived and differ on
every machine.

## The NAS

**Shares and exports: recreate.** The storage stage already does this from the
spec — three NFS exports plus the iSCSI LUN. Recreating is a few `pvesm add`
lines and leaves you with a documented, repeatable definition instead of an
opaque restore.

**DSM configuration backup: take one, treat it as a record.** Control Panel →
Update & Restore → Configuration Backup produces a `.dss`. It is worth having,
and worth reading to confirm export options, user mappings and permissions. But
restoring it onto the South NAS would carry the North NAS's hostname, network
settings and service configuration — the same duplicate-identity problem as
`/etc/pve`, on the same shared segment.

**Data is a separate question.** A DSM config backup contains no share data. If
anything on the North NAS needs to exist at South, copy it explicitly (`rsync`,
Snapshot Replication, or Hyper Backup), decide direction deliberately, and know
that on a shared L2 both NASes are reachable from both terminals — which makes
an accidental overwrite easy.

## What to run, in order

```bash
./bin/ctm-provision rrsouth backup      # kjv1: guests -> NAS, config archive
# ... build the new pair: preflight, postinstall, network, cluster, qdevice, storage
./bin/ctm-provision rrsouth parity      # confirm the hosts match
# then restore the CTM server guest, renumber it, and only then start it
```

Backups first. If anything about the new build goes wrong, the fallback is the
existing terminal — which must still be running and untouched.
