# Existing cluster — as observed

Baseline for building the new pair. Read off the Proxmox UI on 2026-08-30.

**Confidence:** *observed* = read directly from the UI. *inferred* = deduced,
verify before relying on. Anything not listed here was not visible and is still
unknown — run `01-capture.sh` / `02-capture-nas.sh` to fill the gaps.

## Cluster

| | |
|---|---|
| Proxmox VE | **9.1.1** *(observed)* — Debian 13 base, matters for the offline bundle |
| Datacenter | `ContinuumTMN` *(observed)* |
| Nodes | `kjv1`, `kjv2` *(observed)* |

`kjv2` showed **red in the tree with no CPU, memory or uptime reported**, while
`kjv1` reported 2 days 06:19 uptime *(observed)*. Either it is genuinely down
or it was not responding when the screen was taken — worth confirming, because
it changes what "match the existing pair" means.

Note what that implies if it *is* down: a bare two-node cluster would have gone
non-quorate and dropped `/etc/pve` to read-only, yet `kjv1` is serving the UI
and running guests normally. That is consistent with the QDevice on the NAS
holding the third vote and doing exactly its job *(inferred — confirm with
`pvecm status`)*.

## Network — kjv1

| Bridge | Port | NIC name | Address | Gateway |
|---|---|---|---|---|
| `vmbr0` | nic2 | `enx38052535a74a` | `192.168.100.2/24` | — |
| `vmbr1` | nic1 | `enx38052535a74d` | `192.168.50.110/24` | `192.168.50.1` |
| `vmbr2` | nic0 | `enx38052535a74c` | `192.168.12.2/24` | — |

All three bridges autostart *(observed)*. Also present and **inactive**:
`nic3` (`enx38052535a74b`), `nic4`, and `wlp89s0` / `wlxbc09b9558044` — a
wireless adapter *(observed)*.

**`vmbr1` is the panel VLAN.** It carries `192.168.50.0/24` and the default
gateway, which reconciles with the kiosk runbook: the panel network is
`192.168.50.0/24` and the CTM server is `192.168.50.129`. So the host is `.110`
and `.129` is the `ContinuumTMSRV01` guest on that bridge *(inferred)*.

`vmbr0` (`192.168.100.0/24`) carries no gateway — consistent with a private
cluster/corosync or storage link. `vmbr2` (`192.168.12.0/24`) purpose unknown
*(both inferred)*.

### The NIC names are MAC-derived — config is NOT portable

`enx…` / `wlx…` are predictable names built from the adapter's MAC address,
used for USB and wireless NICs. **Two servers of the same model will have
different interface names.** `/etc/network/interfaces` therefore cannot be
copied verbatim to the new pair; each bridge's port must be remapped to that
host's own NIC names.

Run `00-preflight.sh` on each new server first — it prints the NIC names to
use. Parity masks these names so they do not read as false drift, while still
checking that each bridge carries the right subnet.

Two things worth deciding before cloning: whether USB Ethernet adapters are
the intended long-term wiring for a production control host (they can
renumber or drop on a bus reset), and whether the wireless adapter should be
disabled outright on an OT box.

## Guests

| VMID | Name | Node | State |
|---|---|---|---|
| 101 | `ContinuumTMSRV01` | kjv1 | running |
| 102 | `ContinuumHost` | kjv1 | running |
| 999 | `ContinuumHost` | kjv1 | stopped |
| 100 | — | kjv2 | stopped |
| 103 | — | kjv2 | stopped |

`101` is the CTM server *(inferred from the name and the runbook's `.129`)*.

## Storage

Visible on both nodes *(observed)*: `ContinuumTMLUN01`, `ds923-backups`,
`ds923-iso`, `ds923-vm-disks`, plus per-node `local` and `local-lvm`.

The `ds923-` prefix points at a **Synology DS923+** *(inferred)*. If so, one
consequence matters for the new site: DSM is not Debian, so `corosync-qnetd`
cannot be installed with `apt`. The DS923+ is x86_64, so Container Manager
(Docker) is available and qnetd can run in a Debian container there — see
`offline/STAGING.md`. `02-capture-nas.sh` reports the platform and package
manager, which settles this definitively.

**Known gap:** `30-storage.sh` currently adds a single NFS mount. The real
cluster has three NAS-backed stores plus `ContinuumTMLUN01`, which the name
suggests is an iSCSI LUN rather than a file share *(inferred)*. The capture
output will show the actual types; the storage stage needs extending to match
before it can reproduce this.

## Still unknown

Not visible on these screens — the capture scripts answer all of it:

- whether the QDevice is actually registered, and its algorithm
- HA groups and which guests are HA-managed
- corosync ring configuration and which subnet it runs on
- storage types and options behind each entry
- package versions, repo configuration, timezone and NTP sources
