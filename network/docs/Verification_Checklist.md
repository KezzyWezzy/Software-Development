# Red River DTN & PLC Upgrade — Network Verification Checklist

**Document:** RR-NET-003 rev A
Complete one copy per switch. Attach to the turnover package.

Switch: ______________________ Serial: ______________________
Tech: ________________________ Date: ________________________

---

## A. Base configuration

| # | Check | Command | Pass criteria | ✓ |
|---|-------|---------|---------------|---|
| A1 | Hostname and version | `show version` | Hostname matches label; IOS-XE release matches the other three switches | ☐ |
| A2 | No placeholders remain | `show run \| include REPLACE` | **Zero** lines returned | ☐ |
| A3 | Config saved | `show run \| compare startup-config` (or `show archive config differences`) | No differences | ☐ |
| A4 | Survives reload | `reload` then re-check A1–A3 | Config intact | ☐ |
| A5 | Clock synced | `show ntp status` | Clock is synchronized, stratum < 6 | ☐ |
| A6 | Telnet disabled | `show run \| section line vty` | `transport input ssh` only | ☐ |
| A7 | HTTP disabled | `show run \| include http` | `no ip http server` and `no ip http secure-server` | ☐ |
| A8 | Syslog reaching server | `show logging` | Server listed, no send failures | ☐ |

## B. VLANs and management

| # | Check | Command | Pass criteria | ✓ |
|---|-------|---------|---------------|---|
| B1 | VLANs present | `show vlan brief` | 10, 20, 30, 99, 999 all defined with correct names | ☐ |
| B2 | VTP safe | `show vtp status` | Mode: **Transparent** | ☐ |
| B3 | Mgmt SVI up | `show ip interface brief \| include Vlan` | Vlan30 up/up with the address from the design §3 | ☐ |
| B4 | Gateway reachable | `ping 10.14.30.1` | 5/5 | ☐ |
| B5 | SSH works | from a mgmt host: `ssh rradmin@<mgmt-ip>` | Login succeeds, privilege 15 | ☐ |

## C. Spanning tree

| # | Check | Command | Pass criteria | ✓ |
|---|-------|---------|---------------|---|
| C1 | Mode | `show spanning-tree summary` | Rapid-PVST, loopguard default enabled, portfast bpduguard default enabled | ☐ |
| C2 | Root is correct | `show spanning-tree vlan 10 \| include Root ID` | Root bridge is **SW-NT-PLC-01** on every switch, every VLAN | ☐ |
| C3 | No unexpected blocking | `show spanning-tree blockedports` | Only intentionally redundant links, if any | ☐ |
| C4 | Topology is stable | `show spanning-tree detail \| include changes` | Change counter static over a 15 min observation | ☐ |

## D. Trunks

| # | Check | Command | Pass criteria | ✓ |
|---|-------|---------|---------------|---|
| D1 | Trunk up | `show interface trunk` | Native VLAN 99; allowed list 10,20,30 (radio ports: **20,30 only**) | ☐ |
| D2 | Native mismatch | `show logging \| include NATIVE_VLAN` | No CDP native VLAN mismatch messages | ☐ |
| D3 | UDLD on fiber | `show udld <fiber port>` | Bidirectional | ☐ |
| D4 | Radio trunk excludes VLAN 10 | `show interface trunk` on Gi1/3 | VLAN 10 **absent** — this is a design requirement, not an oversight | ☐ |

## E. Access ports

| # | Check | Command | Pass criteria | ✓ |
|---|-------|---------|---------------|---|
| E1 | Port ↔ cable correct | `show interface status` vs `configs/port_map.csv` | Every description matches the pulled cable ID | ☐ |
| E2 | Correct VLAN | `show interface status` | Kiosks VLAN 10, PLC/HMI VLAN 20, spares VLAN 999 | ☐ |
| E3 | Spares are down | `show interface status \| include 999` | All parking ports `disabled` | ☐ |
| E4 | Port security learned | `show port-security address` | Exactly one sticky MAC per live access port | ☐ |
| E5 | No violations | `show port-security \| include Restrict` | Violation counters at 0 | ☐ |
| E6 | No errdisable | `show interfaces status err-disabled` | Empty | ☐ |
| E7 | Clean error counters | `show interface counters errors` | CRC/input errors at 0 after 24 h — a non-zero CRC count on a kiosk drop means re-terminate, do not accept | ☐ |
| E8 | PLC ports have no multicast policer | `show run interface <plc port>` | **No** `storm-control multicast` line present | ☐ |

## F. Multicast / EtherNet/IP

| # | Check | Command | Pass criteria | ✓ |
|---|-------|---------|---------------|---|
| F1 | Snooping on | `show ip igmp snooping` | Globally enabled | ☐ |
| F2 | Querier present on VLAN 20 | `show ip igmp snooping querier vlan 20` | Exactly **one** querier, and it is the intended device | ☐ |
| F3 | Groups learned | `show ip igmp snooping groups vlan 20` | CIP groups present once the PLC is producing | ☐ |
| F4 | PLC reachable | `ping <PLC ip>` and browse in RSLinx | Device appears with correct identity | ☐ |
| F5 | No connection faults | Controller diagnostics | No I/O connection timeouts over a 24 h soak | ☐ |

## G. Wireless link (SW-ST-PLC-01 and SW-MCC-01 only)

| # | Check | Pass criteria | ✓ |
|---|-------|---------------|---|
| G1 | RSSI both directions recorded | Within the vendor's margin for the path length; record actual values below | ☐ |
| G2 | SNR both directions recorded | Stable, recorded | ☐ |
| G3 | Link soak | 72 h with no drop | ☐ |
| G4 | Latency | Ping across the link stable; no sustained spikes | ☐ |
| G5 | No CIP class 1 implicit I/O configured across the link | Confirmed in the controller project | ☐ |

RSSI BSU→SU: ________ SU→BSU: ________ SNR: ________ / ________

## H. Sign-off

| Role | Name | Signature | Date |
|------|------|-----------|------|
| Installing technician | | | |
| Controls engineer | | | |
| Customer representative | | | |

**Any FAIL above blocks turnover for that switch.**
