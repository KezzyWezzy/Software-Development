# Address plan — Red River South Terminal

Derived from the existing kjv cluster at Red River. The new pair is being built
for **Red River South Terminal**. The rule is deliberately boring: **keep the
host octet, change only the third octet.** Everything already written down about
Red River then transfers by inspection, and there is nothing to re-derive under
time pressure at the terminal.

## Networks

| Network | Existing | New site | Why |
|---|---|---|---|
| mgmt + corosync | `192.168.100.0/24` | `192.168.100.0/24` — **unchanged** | as directed |
| panel VLAN | `192.168.50.0/24` | **`192.168.51.0/24`** | avoids collision with the existing panel network |
| third network | `192.168.12.0/24` | confirm | purpose not yet established |

## Panel VLAN — host octets carry over

Known allocations, from the verified kiosk runbook:

| What | Existing | New site |
|---|---|---|
| Gateway | `192.168.50.1` | `192.168.51.1` |
| `bay-1` kiosk | `192.168.50.57` | `192.168.51.57` |
| Proxmox host (kjv1) | `192.168.50.110` | `192.168.51.110` |
| **CTM server** (`ContinuumTMSRV01`) | `192.168.50.129` | **`192.168.51.129`** |
| `test-kiosk-01` | `192.168.50.217` | `192.168.51.217` |

Second Proxmox host: `192.168.51.111` (existing cluster's second host address was
not visible, so this is an allocation, not a carried-over value).

**Ports do not change.** `serve_port` stays `7001 + bay index`, gates from 7010 —
those are server-side nginx listeners and have nothing to do with addressing.

## What the renumber touches beyond the hosts

The panel network is half of the "three identities that must agree", so moving it
is not only a host-config change. For every kiosk at the new site:

1. **Static IP on the panel** (LAN1) — set to the `192.168.51.x` address.
2. **`kiosk_devices` row** — the registered IP must match. The server resolves
   which kiosk is asking from the **source IP** of the request; an unregistered
   or stale address returns 404 to `/kiosk.json` and the screen never identifies
   itself.
3. **HMI name** — unchanged by the renumber, but still has to match `kiosk_id`,
   because the panel publishes to `ctm/kiosk/%0/rfid` and the server takes
   `kiosk_id` from the topic segment.

A wrong address here fails *silently* — which is exactly the class of fault that
has already cost days on this system.

## 192.168.100.0/24 is ONE network, not two copies

South reaches North at **Layer 2**. That settles it: the two terminals are not
two isolated segments that happen to use the same numbers — they share a single
broadcast domain. `192.168.100.0/24` is one network with hosts at both ends.

South still gets its own NAS. That is a separate box on the same segment, at its
own address — not a second `.20`.

**The consequence.** Every address must be unique across both terminals. Two
NASes both at `.20`, or `kjv1` and `rrs-pve1` both at `.2`, is an ARP conflict:
intermittent unreachability, traffic landing on the wrong host, and a fault that
looks like failing hardware. This is now the highest-risk mistake in the build,
which is why the network stage refuses to assign an address that already answers
(see below).

### Allocation

Split the host range so the two terminals cannot collide. Proposed:

| Range | Terminal | Notes |
|---|---|---|
| `.1` – `.99` | North (existing) | `kjv1` is `.2` *(observed)* |
| `.100` – `.199` | **Red River South** | new hosts and South's NAS |
| `.200` – `.254` | reserved | shared services, future |

Suggested South allocation, mirroring North's ordering:

| Host | Address |
|---|---|
| `rrs-pve1` | `192.168.100.111` |
| `rrs-pve2` | `192.168.100.112` |
| South NAS / QDevice | `192.168.100.120` |

These are proposals, not observed values. **North's actual usage is not fully
known** — only `kjv1` at `.2` was visible. A capture of `kjv1` (`pvesm status`,
`corosync.conf`) plus a scan of the segment confirms what is really taken before
anything is committed.

### The kit enforces this

`20-network.sh` runs `arping -D` on the physical NIC before assigning any
address, and **refuses to continue if something already answers**. Three
outcomes:

- address answers → abort, naming the address and why
- nothing answers → proceed, logging that it is free
- `arping` missing or link unavailable → warn and proceed, explicitly saying the
  check could not run rather than implying the address is free

A false "free" is the dangerous answer, so the unknown case is never reported as
a pass.

### Corosync on a shared segment

Both clusters' corosync traffic now shares one broadcast domain. PVE 9 uses knet
with unicast, so there is no multicast collision, and the cluster names already
differ (`ContinuumTMN` vs `ctm-rrsouth`). Workable — but it does mean North's
cluster heartbeat and South's share a wire. If that segment ever gets congested,
it affects quorum at **both** terminals simultaneously, and a fencing event
becomes a two-terminal event rather than a one-terminal one. Worth knowing when
sizing the switch and deciding what else is allowed onto it.

## How parity handles the renumber

`*_SUBNET_REMAP="192.168.50=192.168.51"` in the inventory tells the parity check
that this difference is intentional. It rewrites the baseline before diffing, so:

- the intended `50 → 51` move reads **clean**
- a host **left on the old** `192.168.50.x` is reported as drift
- `192.168.100.x` renumbered by mistake (e.g. to `.101.x`) is reported as drift
- the rule is prefix-anchored, so `192.168.5.x` is never caught by it
