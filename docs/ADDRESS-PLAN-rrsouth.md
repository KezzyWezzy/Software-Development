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

## Keeping 192.168.100.0/24 identical — what has to be true

Both clusters are at Red River: the existing kjv pair, and the new pair for
South Terminal. Two clusters can carry the same subnet only if those segments
are genuinely separate wires. Two facts decide it.

**The evidence in favour.** On kjv1, `vmbr0` holds `192.168.100.2/24` with **no
gateway** *(observed)*. A segment with no gateway does not route anywhere, which
is exactly what a private cluster-interconnect and storage link looks like. If
South's `192.168.100.0/24` is likewise its own switch or VLAN with its own NAS
on it, duplicating the subnet is fine and nothing crosses.

**What would break it.** If South must reach a NAS that lives on the *existing*
`192.168.100.0/24` — a shared Synology, cross-site backups, one ISO store — it
cannot. A host will never route to another terminal's `192.168.100.20` while its
own interface owns that subnet; the traffic is delivered locally and never
leaves. Same if the two terminals' management networks are ever trunked onto
shared switching: duplicate subnets on one L2 domain is an address conflict, not
a topology.

So the question to answer before building is narrow:

> **Does Red River South get its own NAS on its own `192.168.100.0/24`, or does
> it use the existing one?**

Its own → keep the subnet identical as directed, nothing more to do. Shared →
the management network needs renumbering too, the same way the panel VLAN did
(`192.168.100` → `192.168.101` keeps the rule consistent).

Nothing in the kit depends on the answer — both are one inventory value — but it
is much cheaper to settle now than after both nodes are built and the NAS will
not mount.

## How parity handles the renumber

`*_SUBNET_REMAP="192.168.50=192.168.51"` in the inventory tells the parity check
that this difference is intentional. It rewrites the baseline before diffing, so:

- the intended `50 → 51` move reads **clean**
- a host **left on the old** `192.168.50.x` is reported as drift
- `192.168.100.x` renumbered by mistake (e.g. to `.101.x`) is reported as drift
- the rule is prefix-anchored, so `192.168.5.x` is never caught by it
