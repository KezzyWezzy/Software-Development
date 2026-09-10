# Red River DTN & PLC Upgrade — Network Cutover Plan

**Document:** RR-NET-002 rev A **Status:** ISSUED FOR REVIEW
**Prerequisite:** all cable test documentation from
`Red_River_DTN_Cable_Schedule.md` §7 complete and submitted.

---

## Stage 0 — Bench build (shop, before mobilization)

No site access required. Everything here is reversible.

| # | Step | Done when |
|---|------|-----------|
| 0.1 | Confirm every assumption in `Network_Design.md` §0 with the project engineer. Update `site_inventory.yaml` for anything that differs and regenerate. | Assumption table signed |
| 0.2 | Verify switch model and IOS-XE version against §8 of the design | `show version` recorded per switch |
| 0.3 | Upgrade all four switches to the same IOS-XE release | Versions identical |
| 0.4 | Pull credentials from the project vault, replace the four `<<REPLACE-BEFORE-DEPLOY>>` markers in each config | `grep -c REPLACE` returns 0 |
| 0.5 | Load each config over console, save, reload, confirm it survives | `show run` matches intent after reload |
| 0.6 | Bench-test: laptop on a kiosk port gets a link and reaches the mgmt SVI gateway; laptop on a parking port gets nothing | Both results observed |
| 0.7 | Label each switch with hostname + mgmt IP; record serials into `port_map.csv` follow-up | Labels applied |

**Do not skip 0.5.** A pipe-rack switch that refuses its config after a power
cycle is a 40-foot climb to discover.

## Stage 1 — North Terminal (no existing service to disturb)

North is new-build, so it carries no cutover risk and goes first — it proves
the config set before anything live is touched.

| # | Step | Rollback |
|---|------|----------|
| 1.1 | Mount SW-NT-PLC-01 in CTMPLCP-NT, land 24 VDC | Power off |
| 1.2 | Mount SW-NT-JB-01 in the pipe rack junction box, land P-0107 | Power off |
| 1.3 | Terminate E-0107 fiber, SFP both ends | Unplug |
| 1.4 | Confirm the fiber trunk: `show interface status`, `show spanning-tree vlan 10` — SW-NT-PLC-01 must be root, JB uplink must be forwarding | Unplug fiber |
| 1.5 | Land kiosk drops E-0101…E-0106 on Gi1/3…Gi1/8 | Unplug, port reverts to link-down |
| 1.6 | Energize kiosks one at a time, confirm each learns exactly one MAC and pings its gateway | Shut the port |
| 1.7 | Land CTMPLCP-NT PLC on Gi1/3 of SW-NT-PLC-01, confirm the PLC is reachable and RSLinx browses it | Shut the port |
| 1.8 | Uplink Gi1/1 to the plant core, confirm the trunk negotiates VLANs 10/20/30 and mgmt is reachable from the core | Unplug uplink |

**Gate:** do not proceed to Stage 2 until every North kiosk holds a stable
link for 24 h with no errdisable, no port-security violation and no STP
topology change. `show logging | include %` should be quiet.

## Stage 2 — South Terminal (LIVE — outage required)

The existing South Terminal PLC panel is being replaced. This stage stops
loading at South Terminal.

| # | Step | Rollback |
|---|------|----------|
| 2.1 | **Outage window agreed with Operations in writing.** Loading suspended at South Terminal. | — |
| 2.2 | Photograph and record the existing panel's network connections before anything is removed | — |
| 2.3 | Remove the existing PLC panel per cable schedule §8 | Re-install old panel (keep it on site, intact, until Stage 4 sign-off) |
| 2.4 | Install CTMPLCP-ST, mount SW-ST-PLC-01, land power | Power off |
| 2.5 | Land uplink Gi1/1, confirm trunk and mgmt reachability | Unplug |
| 2.6 | Confirm STP: SW-ST-PLC-01 is backup root, not root. If it wins root, stop — the core priority is wrong. | Unplug uplink |
| 2.7 | Land E-0201 / E-0202 on Gi1/4 / Gi1/5, energize kiosks one at a time | Shut the port |
| 2.8 | Land CTMPLCP-ST PLC on Gi1/6, HMI on Gi1/7, confirm both reachable | Shut the port |
| 2.9 | Functional test: both kiosks complete a full CTM transaction against CTMPLCP-ST | Roll back to 2.3 |
| 2.10 | Operations releases South Terminal back to service | — |

**Rollback trigger:** if the terminal is not loading by the agreed end of the
outage window, reinstate the old panel. Do not extend the window to debug.

## Stage 3 — South Shop / MCC wireless link

| # | Step | Rollback |
|---|------|----------|
| 3.1 | Confirm the BSU location (design assumption A6 — South Terminal) and that a clear Fresnel path exists | Stop; re-survey |
| 3.2 | Mount and align radios per `proxim/QB-8200_link_parameters.md`; record RSSI and SNR both directions | Power off |
| 3.3 | Land the BSU on SW-ST-PLC-01 Gi1/3; land the SU on SW-MCC-01 Gi1/3 via E-0301 | Unplug |
| 3.4 | Confirm the trunk carries VLAN 20 and 30 **only** — VLAN 10 must not pass | Unplug |
| 3.5 | Mount SW-MCC-01 in the MCC panel, land the MCC PLC on Gi1/4 | Power off |
| 3.6 | Confirm the MCC PLC is reachable from the terminal and that **only explicit messaging / Modbus TCP** is configured across the link — no CIP class 1 implicit I/O | Shut the port |
| 3.7 | Soak the link 72 h; record RSSI/SNR min-max and any STP topology change | Unplug the radio trunk; MCC reverts to isolated |

**Do not** commission a CIP implicit connection over this link even if it
appears to work on a clear day. See `Network_Design.md` §4.

## Stage 4 — Documentation and turnover

| # | Step |
|---|------|
| 4.1 | Complete `Verification_Checklist.md` for all four switches, signed and dated |
| 4.2 | Capture `show run` from every switch, diff against the generated `.cfg`, and commit any accepted field changes **back into `site_inventory.yaml`** — not into the `.cfg` |
| 4.3 | Update `port_map.csv` with as-installed serials and MAC addresses |
| 4.4 | Record radio RSSI/SNR baseline for future troubleshooting |
| 4.5 | Hand over credentials to the customer's vault; remove any local copies |
| 4.6 | Release the old South Terminal panel for disposal |

## Standing rules

- **One change at a time.** Land a port, verify it, then land the next. The
  entire value of the staging above is destroyed by landing six kiosks at once.
- **Config drift goes upstream.** Any change made in the field is entered into
  `site_inventory.yaml` and regenerated. A hand-edited `.cfg` is lost work.
- **No config loads without cable test documentation complete** — cable
  schedule §7 is explicit that test docs precede cutover.
- **Console access before remote access.** Never make a management-VLAN or
  trunk change on a remote switch without a console path or a scheduled
  auto-reload safety net.
