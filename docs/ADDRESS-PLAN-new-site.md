# Address plan — new site

Derived from the existing kjv build. The rule is deliberately boring: **keep the
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

## Keeping 192.168.100.0/24 identical — the one thing to confirm

Two clusters using the same corosync/mgmt subnet is fine **only while those
segments never route to each other.** Worth settling explicitly before build:

- **Separate NAS per site** — fine. Each site's `192.168.100.20` is its own box,
  and nothing crosses.
- **New site must reach the *existing* NAS** — broken. A host cannot route to
  `192.168.100.20` at another site while its own interface owns
  `192.168.100.0/24`; the traffic never leaves the local segment. If backups,
  replication, or a shared ISO store are meant to cross sites, the mgmt network
  has to be renumbered too, exactly like the panel VLAN.

Nothing in the kit depends on the answer — but if the second case is what's
intended, it is much cheaper to find out now than after both nodes are built.

## How parity handles the renumber

`*_SUBNET_REMAP="192.168.50=192.168.51"` in the inventory tells the parity check
that this difference is intentional. It rewrites the baseline before diffing, so:

- the intended `50 → 51` move reads **clean**
- a host **left on the old** `192.168.50.x` is reported as drift
- `192.168.100.x` renumbered by mistake (e.g. to `.101.x`) is reported as drift
- the rule is prefix-anchored, so `192.168.5.x` is never caught by it
