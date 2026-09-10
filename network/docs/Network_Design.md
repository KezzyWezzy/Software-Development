# Red River DTN & PLC Upgrade — Network Design Basis

**Document:** RR-NET-001 rev A **Status:** ISSUED FOR REVIEW
**Companion to:** `Red_River_DTN_Cable_Schedule.md`, `Work Plan.html`

---

## 0. Read this first — open assumptions

Nothing in this package has been validated against site hardware. Every item
below is an engineering assumption made to produce a complete, reviewable
design. Confirm each one before any config is loaded onto a switch.

| # | Assumption | Impact if wrong |
|---|-----------|-----------------|
| A1 | **CTMPLCP** = CTM PLC Panel (Continuum Terminal Manager PLC panel) at North and South Terminal | Naming only — port descriptions and hostnames |
| A2 | **Proxim** radio = Proxim Wireless Tsunami **QB-8200** point-to-point bridge | Radio parameters in §7 and `proxim/` change per model |
| A3 | Switch platform = **Cisco IE-3300-8T2S**, IOS-XE 17.x | Port numbering (`Gi1/1-1/2` uplink, `Gi1/3-1/10` downlink) and a handful of commands — see §8 |
| A4 | Addressing is greenfield `10.14.0.0/16` (VLANs 10/20/30) | Whole address plan is regenerated from `site_inventory.yaml` |
| A5 | Inter-VLAN routing is done by an **existing plant core / firewall**; these four switches are pure Layer 2 with one management SVI | If no core exists, one switch must become L3 and gain SVIs + ACLs |
| A6 | The **far end** of the wireless link (the BSU) lives at South Terminal | Cable schedule only lists the MCC-side radio (E-0301); the peer location is unconfirmed |
| A7 | Kiosks, PLCs and HMIs are **statically addressed** (no DHCP on the process network) | DHCP snooping + relay config would need to be added |
| A8 | The North Terminal fiber run E-0107 terminates on **SFP** at both ends | If it lands on copper media converters, drop `udld port aggressive` |

---

## 1. Topology

```
                        ┌───────────────────────────┐
                        │  Plant Core / DTN WAN     │
                        │  10.14.10.1 / .20.1 /.30.1│
                        └────────────┬──────────────┘
                     fiber trunk     │            fiber trunk
              ┌───────────────────────┴───────────────────────┐
              │                                               │
   ┌──────────┴──────────┐                        ┌───────────┴───────────┐
   │  SW-NT-PLC-01       │  STP ROOT (4096)       │  SW-ST-PLC-01         │ STP backup (8192)
   │  CTMPLCP-NT panel   │                        │  CTMPLCP-ST panel     │
   │  North Terminal     │                        │  South Terminal office│
   └──────────┬──────────┘                        └───┬───────────────┬───┘
              │ E-0107 fiber trunk                    │ Gi1/4-1/5     │ Gi1/3 trunk
              │                                       │ 2 kiosks      │
   ┌──────────┴──────────┐                            │        ┌──────┴──────┐
   │  SW-NT-JB-01        │                            │        │ RADIO-BSU-01│
   │  Junction box,      │                            │        │ Proxim QB-  │
   │  North Pipe Rack    │                            │        │ 8200 master │
   │  Gi1/3-1/8          │                            │        └──────┬──────┘
   │  → 6 kiosks         │                            │               ╎ 5 GHz PTP
   │  (E-0101..E-0106)   │                            │               ╎
   └─────────────────────┘                            │        ┌──────┴──────┐
                                                      │        │ RADIO-SU-01 │
                                                      │        │ South Shop  │
                                                      │        └──────┬──────┘
                                                      │               │ E-0301
                                                      │        ┌──────┴──────┐
                                                      │        │  SW-MCC-01  │
                                                      │        │  MCC panel  │
                                                      │        └─────────────┘
```

## 2. VLAN plan

| VLAN | Name | Subnet | Gateway | Carries |
|------|------|--------|---------|---------|
| 10 | `CTM_KIOSK` | 10.14.10.0/24 | 10.14.10.1 | 8 terminal kiosks + CTM edge gateway |
| 20 | `PLC_CTRL` | 10.14.20.0/24 | 10.14.20.1 | CTMPLCP PLCs, panel HMIs, EtherNet/IP |
| 30 | `NET_MGMT` | 10.14.30.0/24 | 10.14.30.1 | Switch and radio management only |
| 99 | `NATIVE_UNUSED` | — | — | Trunk native VLAN, carries no hosts |
| 999 | `PARKING` | — | — | All unused access ports, admin-down |

VLAN 99 as the trunk native and VLAN 999 for spare ports are deliberate:
neither VLAN 1 nor any live VLAN is reachable from an unpatched port.

## 3. Address plan

| Device | VLAN | Address |
|--------|------|---------|
| SW-NT-PLC-01 (mgmt) | 30 | 10.14.30.11 |
| SW-NT-JB-01 (mgmt) | 30 | 10.14.30.12 |
| SW-ST-PLC-01 (mgmt) | 30 | 10.14.30.21 |
| SW-MCC-01 (mgmt) | 30 | 10.14.30.31 |
| RADIO-BSU-01 (mgmt) | 30 | 10.14.30.41 |
| RADIO-SU-01 (mgmt) | 30 | 10.14.30.42 |
| Kiosks NT-01 … NT-06 | 10 | 10.14.10.11 … .16 |
| Kiosks ST-01 … ST-02 | 10 | 10.14.10.21 … .22 |
| CTM edge gateway | 10 | 10.14.10.5 |
| CTMPLCP-NT PLC / HMI | 20 | 10.14.20.11 / .12 |
| CTMPLCP-ST PLC / HMI | 20 | 10.14.20.21 / .22 |
| South Shop MCC PLC | 20 | 10.14.20.31 |

Full port-by-port mapping to cable IDs: `network/configs/port_map.csv`.

## 4. Design decisions that matter

**EtherNet/IP multicast.** CIP class 1 (implicit) I/O is multicast. Two rules
follow, and both are enforced in the generated configs:

1. `ip igmp snooping` is on globally, and the IGMP querier is the plant core
   on each VLAN gateway. Without a querier, snooping floods or starves CIP
   I/O. If the core cannot query VLAN 20, promote **exactly one** switch using
   the commented lines in the management block of `SW-NT-PLC-01.cfg`.
2. PLC ports get **no multicast storm control**. Broadcast and unknown-unicast
   storm control only. Applying a multicast pps limit to a CIP port polices
   production I/O and produces intermittent connection faults that are
   miserable to diagnose.

**Nothing latency-critical crosses the radio.** The Proxim trunk carries VLANs
20 and 30 only, and the design intent is explicit messaging (MSG instructions)
or Modbus TCP between the MCC PLC and the terminal — **not** CIP class 1
implicit I/O. A 5 GHz PTP link has jitter and fade characteristics that will
trip an implicit connection's RPI watchdog during weather. VLAN 10 is
deliberately not carried: no kiosk should ever depend on the radio.

**Kiosk ports are locked down.** Portfast + BPDU guard (a kiosk that starts
talking STP gets errdisabled), port-security sticky max-1 with `restrict`
(a swapped kiosk logs and drops the extra MAC rather than blacking out the
port), broadcast + multicast storm control, and CDP/LLDP off so the switch
advertises nothing to the public-facing side of a loading bay.

**Violation actions are recoverable.** `errdisable recovery` is on for
bpduguard, port-security, link-flap, storm-control and UDLD with a 300 s
interval — a transient event self-clears instead of requiring a truck roll to
a pipe rack.

**Spanning tree is deterministic.** Rapid-PVST, `SW-NT-PLC-01` hard-set to
priority 4096, `SW-ST-PLC-01` to 8192, everything else at default 32768. Root
guard faces the junction box; loop guard faces upstream from the leaf
switches. The topology is a tree today, but the junction box has a spare SFP
reserved for a future redundant ring and this makes that addition safe.

## 5. Files in this package

| File | What it is |
|------|-----------|
| `network/site_inventory.yaml` | Source of truth — VLANs, addresses, every port |
| `network/tools/gen_switch_configs.py` | Generator + validator (`--check`) |
| `network/configs/*.cfg` | Generated, paste-ready IOS-XE configs |
| `network/configs/port_map.csv` | Port ↔ cable ID ↔ device ↔ IP cross reference |
| `network/docs/Network_Design.md` | This document |
| `network/docs/Cutover_Plan.md` | Staged execution runbook with rollback |
| `network/docs/Verification_Checklist.md` | Sign-off test sheet |
| `network/proxim/QB-8200_link_parameters.md` | Radio-side settings |

To change anything: edit the YAML, run
`python3 network/tools/gen_switch_configs.py`, commit both the inventory and
the regenerated configs. The `.cfg` files are build output — never hand-edit
them, or the next run silently reverts the edit.

## 6. Placeholders that must be filled before deployment

Every generated config contains `<<REPLACE-BEFORE-DEPLOY>>` markers:

- `enable` secret
- `rradmin` user secret
- SNMPv3 auth (SHA) and priv (AES-128) passphrases

Credentials are deliberately **not** stored in this repository. Pull them from
the project password vault at load time.

```
grep -c "REPLACE-BEFORE-DEPLOY" network/configs/*.cfg   # expect 4 per switch
```

## 7. Wireless link summary

See `network/proxim/QB-8200_link_parameters.md` for the full radio-side
parameter set. Switch side, both radio ports are 802.1Q trunks with native
VLAN 99 and an allowed list of **20,30 only**.

## 8. Platform deltas

Written for IE-3300 / IOS-XE 17.x. If the delivered hardware differs:

| Platform | Change required |
|----------|-----------------|
| **Catalyst 9200 / C1000** | Port names become `GigabitEthernet1/0/1…`; update `id:` in the inventory. `udld enable` is global-only on some trains. Everything else parses unchanged. |
| **IE-3200** | 8 fixed copper ports, no SFP uplinks — the fiber run E-0107 needs media converters, and `udld port aggressive` must be dropped. |
| **IE-2000 (classic IOS)** | `algorithm-type scrypt` → `algorithm-type sha256`; `storm-control … level pps` syntax differs; QoS uses `mls qos`. Treat as a re-write, not a port. |

QoS is intentionally left at platform default. IOS-XE trusts DSCP on all ports
by default, which is the correct behaviour for a network this small with a
dedicated PLC VLAN. Adding priority queueing here would be complexity without
a measured problem to solve.
