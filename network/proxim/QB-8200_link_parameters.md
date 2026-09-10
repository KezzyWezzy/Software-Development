# Proxim Tsunami QB-8200 — Link Parameters (South Terminal ↔ South Shop/MCC)

**Document:** RR-NET-004 rev A **Status:** ISSUED FOR REVIEW
**Assumption A2:** model is a Proxim Tsunami QB-8200 point-to-point bridge.
Confirm the actual model before ordering or configuring — parameter names
differ across the QB-8100 / QB-8200 / MP-8200 families.

The radios are **not** Cisco devices and are not produced by the config
generator. This page records the settings the switch configuration depends on,
so the two sides stay consistent.

---

## Roles and addressing

| Item | BSU (master) | SU (slave) |
|------|--------------|------------|
| Name | `RADIO-BSU-01` | `RADIO-SU-01` |
| Site | South Terminal | South Shop / MCC |
| Management IP | 10.14.30.41/24 | 10.14.30.42/24 |
| Management VLAN | 30 (tagged) | 30 (tagged) |
| Gateway | 10.14.30.1 | 10.14.30.1 |
| Switch port | SW-ST-PLC-01 `Gi1/3` | SW-MCC-01 `Gi1/3` (cable E-0301) |

## Bridging and VLAN

| Parameter | Setting | Why |
|-----------|---------|-----|
| Mode | Transparent bridge | The link is Layer 2; all routing stays at the plant core |
| VLAN mode | Trunk / 802.1Q pass-through | Must carry tagged frames end to end |
| Allowed VLANs | **20, 30 only** | Matches `switchport trunk allowed vlan 20,30` on both switch ports |
| Management VLAN | 30, tagged | Radio management shares the switch management VLAN |
| Native / untagged VLAN | 99 | Matches the switch trunk native VLAN; carries no hosts |
| VLAN 10 (kiosks) | **Not carried** | No kiosk may depend on the wireless link |

If the radios are left in their default untagged/transparent mode, the switch
trunks will not pass tagged traffic and the link will appear up but dead.
This is the single most common failure on this kind of installation.

## RF

| Parameter | Setting | Notes |
|-----------|---------|-------|
| Band | 5 GHz | Confirm local channel availability and any site RF survey |
| Channel | Fixed, not auto | A fixed channel avoids a DFS-triggered outage mid-load |
| Channel width | Narrowest that meets throughput need | Narrower channel = better link budget and fade margin |
| TX power | Lowest that meets the fade-margin target | Do not run at maximum "for headroom" — it costs dynamic range |
| Encryption | AES enabled, unique key | Key goes in the project vault, not this repository |
| Link distance / ACK timeout | Set to actual path length | Leaving this at default is a common cause of low throughput on short links |

Record the as-commissioned values in `Verification_Checklist.md` §G.

## Traffic policy

The controlling constraint from `Network_Design.md` §4:

> **No CIP class 1 implicit I/O across this link.** Explicit messaging (MSG
> instructions) or Modbus TCP only.

A 5 GHz PTP link's jitter and rain-fade behaviour will eventually exceed an
implicit connection's RPI watchdog. The failure mode is an intermittent
controller I/O fault during weather — which will be blamed on the PLC, not the
radio. Design the MCC integration around a polled/explicit pattern with a
tolerant timeout from the start.

## Commissioning notes

1. Align for best RSSI **and** SNR, not RSSI alone — a strong noisy link
   performs worse than a weaker clean one.
2. Record RSSI and SNR in both directions at commissioning. Without a
   baseline, "the radio seems worse than it used to be" is unfalsifiable.
3. Soak 72 h before the link is relied on (cutover plan Stage 3.7).
4. Confirm the far-end BSU location (assumption A6) before mobilizing — the
   cable schedule only documents the MCC-side radio, cable E-0301.
