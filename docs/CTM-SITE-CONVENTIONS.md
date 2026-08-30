# CTM site conventions

Addressing, naming and port conventions that a new CTM site must follow, so
Line 2 and Nash come out matching the build that is already known to work.

**Source.** Everything marked *verified* was confirmed against the live Red
River bay‑1 unit and CTM server on 2026‑08‑28 and is recorded in the CTM Kiosk
Runbook artifact. Items marked *open* are not yet decided for the new sites.

## Network

| | Red River (verified) | Line 2 | Nash |
|---|---|---|---|
| Panel VLAN | `192.168.50.0/24` | open | open |
| CTM server | `192.168.50.129` | open | open |
| Kiosk range | `192.168.50.x` static | open | open |

Kiosks take **static** addresses. The server resolves which kiosk is asking
from the source IP of the request, so DHCP would break identification.

## The three identities that must agree

A kiosk works only when all three line up, and fails *silently* when they do
not — which is why past failures looked like dead hardware. *(verified)*

1. **HMI name** — panel system settings, e.g. `bay-1`
2. **`kiosk_id` / `node_name`** — the `kiosk_devices` table, e.g. `bay-1`
3. **Static IP** — panel LAN1 *and* the `kiosk_devices` row, e.g. `192.168.50.57`

Why each matters:

- The panel publishes to `ctm/kiosk/%0/rfid`, where `%0` is the HMI name. The
  server takes `kiosk_id` from the topic segment and **overrides whatever the
  payload says**. A wrong HMI name means scans arrive for a kiosk that does not
  exist and are dropped.
- The panel SPA fetches `/kiosk.json`, and the server resolves which kiosk that
  is from the source IP. A wrong or unregistered IP returns 404 and the screen
  never identifies itself.

## Port allocation

One nginx listener per kiosk. *(verified)*

| kiosk_id | serve_port |
|---|---|
| `test-kiosk-01` | 7001 |
| `bay-1` … `bay-6` | 7002 … 7007 |
| `gate-01` | 7010 |

Rule: `serve_port = 7001 + bay index`, gates from 7010 up. **Provision the
listener server-side before deploying the panel** — a panel pointed at a port
nginx is not listening on looks identical to a dead panel. This blocked
`gate-01` at Red River.

## Hardware

- Panels: Weintek **cMT3102X**, 1024 × 600, with RFID reader *(verified)*
- EasyBuilder **V6.10.02.231** *(verified)*

## Traps carried over from Red River

These cost days at Red River. They are panel-configuration traps, not
Proxmox ones, but they apply to every new site. Full detail is in the CTM Kiosk
Runbook artifact.

- Panel time zone defaults to **UTC+08:00**. Set it explicitly.
- UTC−05:00 is a **fixed offset**, not a time zone — it will not follow DST.
- Data Transfer "No. of tags" counts **words, not tags**.
- The RFID reader is a **Device**, not a ribbon object.
- "Reset recipe (RW, RW_A)" **wipes RW on every download**.
- The **Generate** button in the MQTT topic dialog **overwrites your topic**.
- An open modal dialog **silently eats every click**.
- The reader emits **decimal**; enrollment stores **hex**.

## Open for Line 2 and Nash

Decide and record here before provisioning:

- ~~Panel VLAN at each site~~ — **decided.** The new site uses
  `192.168.51.0/24`, keeping host octets (CTM server `.129`, gateway `.1`).
  `192.168.100.0/24` stays identical to the existing cluster. See
  [ADDRESS-PLAN-new-site.md](ADDRESS-PLAN-new-site.md).
- Bay count and therefore the kiosk/port allocation per site.
- Whether each site runs its own CTM server (site-independent, survives a WAN
  loss) or both point at one — this drives whether the Proxmox HA cluster is
  per-site or spans sites.
