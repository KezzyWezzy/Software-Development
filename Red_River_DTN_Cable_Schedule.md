# Red River DTN & PLC Upgrade - Cable Schedule

**Project:** Red River DTN & PLC Upgrade
**Date:** November 11, 2025
**Document:** Cable Schedule and Routing Plan

---

## Cable Naming Conventions

- **Power Cables (24 VDC):** P-xxxx
- **Ethernet Cables (CAT6):** E-xxxx

---

## 1. NORTH TERMINAL - Cable Schedule

### Junction Box Location
- **Location:** North Pipe Rack (top of structure)
- **Equipment:** Network Switch, Fiber Termination Panel
- **Function:** Central aggregation point for all North Terminal kiosks

### Power Cables (24 VDC) - North Terminal

| Cable ID | Cable Type | From | To | Est. Length | Conduit Route | Notes |
|----------|-----------|------|-----|-------------|---------------|-------|
| P-0101 | 24 VDC Power | North Terminal PLC Panel | Terminal Kiosk #1 | 180' | Junction Box → 40' vertical + 20' horizontal to wire tray → Kiosk #1 | First kiosk from junction box |
| P-0102 | 24 VDC Power | North Terminal PLC Panel | Terminal Kiosk #2 | 195' | Junction Box → 40' vertical + 20' horizontal to wire tray → Kiosk #2 | ~16' from Kiosk #1 |
| P-0103 | 24 VDC Power | North Terminal PLC Panel | Terminal Kiosk #3 | 210' | Junction Box → 40' vertical + 20' horizontal to wire tray → Kiosk #3 | ~32' from Kiosk #1 |
| P-0104 | 24 VDC Power | North Terminal PLC Panel | Terminal Kiosk #4 | 225' | Junction Box → 40' vertical + 20' horizontal to wire tray → Kiosk #4 | ~48' from Kiosk #1 |
| P-0105 | 24 VDC Power | North Terminal PLC Panel | Terminal Kiosk #5 | 240' | Junction Box → 40' vertical + 20' horizontal to wire tray → Kiosk #5 | ~64' from Kiosk #1 (113' total span) |
| P-0106 | 24 VDC Power | North Terminal PLC Panel | Terminal Kiosk #6 | 255' | Junction Box → 40' vertical + 20' horizontal to wire tray → Kiosk #6 | Last kiosk, ~49' from Kiosk #5 |
| P-0107 | 24 VDC Power | North Terminal PLC Panel | Junction Box Switch | 80' | Direct run from PLC panel to junction box | Power for network switch |

### Ethernet Cables (CAT6) - North Terminal

| Cable ID | Cable Type | From | To | Est. Length | Conduit Route | Notes |
|----------|-----------|------|-----|-------------|---------------|-------|
| E-0101 | CAT6 Ethernet | Junction Box Switch | Terminal Kiosk #1 | 80' | Junction box → 40' vertical + 20' horizontal to wire tray → Kiosk #1 | First kiosk connection |
| E-0102 | CAT6 Ethernet | Junction Box Switch | Terminal Kiosk #2 | 95' | Junction box → 40' vertical + 20' horizontal to wire tray → Kiosk #2 | ~16' from Kiosk #1 |
| E-0103 | CAT6 Ethernet | Junction Box Switch | Terminal Kiosk #3 | 110' | Junction box → 40' vertical + 20' horizontal to wire tray → Kiosk #3 | ~32' from Kiosk #1 |
| E-0104 | CAT6 Ethernet | Junction Box Switch | Terminal Kiosk #4 | 125' | Junction box → 40' vertical + 20' horizontal to wire tray → Kiosk #4 | ~48' from Kiosk #1 |
| E-0105 | CAT6 Ethernet | Junction Box Switch | Terminal Kiosk #5 | 140' | Junction box → 40' vertical + 20' horizontal to wire tray → Kiosk #5 | ~64' from Kiosk #1 |
| E-0106 | CAT6 Ethernet | Junction Box Switch | Terminal Kiosk #6 | 155' | Junction box → 40' vertical + 20' horizontal to wire tray → Kiosk #6 | Last kiosk, total span 113' |
| E-0107 | CAT6 Fiber/Ethernet | North Terminal PLC Panel | Junction Box Switch | 80' | Direct fiber run from PLC panel to junction box switch | Fiber uplink to main network |

**North Terminal Summary:**
- **Total Power Cables:** 7 (6 kiosks + 1 switch)
- **Total Ethernet Cables:** 7 (6 kiosks + 1 fiber uplink)
- **Total CAT6 Runs:** 6 (serving 6 kiosks from junction box)

---

## 2. SOUTH TERMINAL - Cable Schedule

### PLC Panel Location
- **Location:** Office building adjacent to loading bays (Dorr Avenue/Conway Blvd corner)
- **Equipment:** New PLC Panel (replaces existing)
- **Function:** Control and network hub for South Terminal kiosks

### Power Cables (24 VDC) - South Terminal

| Cable ID | Cable Type | From | To | Est. Length | Conduit Route | Notes |
|----------|-----------|------|-----|-------------|---------------|-------|
| P-0201 | 24 VDC Power | South Terminal PLC Panel | Terminal Kiosk #1 | 190' | PLC Panel → conduit to wire tray → 40' vertical + 20' horizontal → Kiosk #1 | First kiosk (20' from second measurement point) |
| P-0202 | 24 VDC Power | South Terminal PLC Panel | Terminal Kiosk #2 | 210' | PLC Panel → conduit to wire tray → 40' vertical + 20' horizontal → Kiosk #2 | Second kiosk (40' from first point), can share conduit from outside |

### Ethernet Cables (CAT6) - South Terminal

| Cable ID | Cable Type | From | To | Est. Length | Conduit Route | Notes |
|----------|-----------|------|-----|-------------|---------------|-------|
| E-0201 | CAT6 Ethernet | South Terminal PLC Panel | Terminal Kiosk #1 | 190' | PLC Panel → conduit to wire tray → 40' vertical + 20' horizontal → Kiosk #1 | First kiosk connection |
| E-0202 | CAT6 Ethernet | South Terminal PLC Panel | Terminal Kiosk #2 | 210' | PLC Panel → conduit to wire tray → 40' vertical + 20' horizontal → Kiosk #2 | Can use direct conduit run from outside to Kiosk #2, then to office |

**South Terminal Summary:**
- **Total Power Cables:** 2 (serving 2 kiosks)
- **Total Ethernet Cables:** 2 (serving 2 kiosks)
- **Total CAT6 Runs:** 2

---

## 3. SOUTH SHOP/MCC - Radio Installation

### Radio Equipment

| Cable ID | Cable Type | From | To | Est. Length | Conduit Route | Notes |
|----------|-----------|------|-----|-------------|---------------|-------|
| P-0301 | 24 VDC Power | South Shop MCC Panel | Radio Equipment | TBD | TBD based on site survey | Radio power supply |
| E-0301 | CAT6 Ethernet | South Shop MCC Panel | Radio Equipment | TBD | TBD based on site survey | Radio network connection |

**South Shop/MCC Summary:**
- **Total Power Cables:** 1 (radio)
- **Total Ethernet Cables:** 1 (radio)

---

## 4. PROJECT CABLE SUMMARY

### Total Cable Count by Type

| Cable Type | North Terminal | South Terminal | South Shop/MCC | **TOTAL** |
|------------|----------------|----------------|----------------|-----------|
| 24 VDC Power (P-xxxx) | 7 | 2 | 1 | **10** |
| CAT6 Ethernet (E-xxxx) | 7 | 2 | 1 | **10** |
| **TOTAL CABLES** | **14** | **4** | **2** | **20** |

### CAT6 Cable Runs (Physical Pulls)

| Location | Quantity | Details |
|----------|----------|---------|
| North Terminal Kiosks | 6 | Junction Box → 6 kiosks |
| South Terminal Kiosks | 2 | PLC Panel → 2 kiosks |
| South Shop Radio | 1 | MCC Panel → Radio |
| **TOTAL CAT6 RUNS** | **9** | As specified in scope (7 + fiber uplink + switch power) |

---

## 5. CONDUIT REQUIREMENTS

### North Terminal Conduit

| Route | Quantity | Length per Run | Total Length | Notes |
|-------|----------|----------------|--------------|-------|
| Junction Box to Wire Tray (vertical) | 1 | 40' | 40' | Main vertical drop |
| Wire Tray to Each Kiosk (vertical) | 6 | 40' | 240' | 40' vertical per kiosk |
| Wire Tray to Each Kiosk (horizontal) | 6 | 20' | 120' | 20' horizontal per kiosk |
| **North Terminal Total** | - | - | **~400'** | Plus contingency |

### South Terminal Conduit

| Route | Quantity | Length per Run | Total Length | Notes |
|-------|----------|----------------|--------------|-------|
| PLC Panel to Wire Tray | 1 | 119' | 119' | Main run along loading bays |
| Wire Tray to Each Kiosk (vertical) | 2 | 40' | 80' | 40' vertical per kiosk |
| Wire Tray to Each Kiosk (horizontal) | 2 | 20' | 40' | 20' horizontal per kiosk |
| **South Terminal Total** | - | - | **~240'** | Plus contingency |

### Total Conduit Estimate
- **Total Conduit Required:** ~640' minimum
- **Recommended Order Quantity:** 750-800' (includes 15-20% contingency)

---

## 6. TERMINATION SUMMARY

### PLC Panel Terminations

| Panel Location | Power Terminations | Ethernet Terminations | Total |
|----------------|-------------------|----------------------|-------|
| North Terminal PLC Panel | 7 power feeds | 1 fiber uplink | 8 |
| South Terminal PLC Panel | 2 power feeds | 2 Ethernet | 4 |
| South Shop MCC Panel | 1 power feed | 1 Ethernet | 2 |
| Junction Box (North) | 7 power receives + 1 switch power | 7 Ethernet (6 kiosks + 1 uplink) | 15 |
| **TOTAL TERMINATIONS** | - | - | **~60-80** |

*Note: Total terminations include both source and destination ends, plus internal panel wiring per scope requirements*

---

## 7. TESTING REQUIREMENTS

### CAT6 Cable Testing (Per Scope)
- [ ] Continuity testing for all CAT6 runs
- [ ] Connectivity testing for all CAT6 runs
- [ ] Point-to-point continuity checks for all terminations
- [ ] Document all test results with:
  - Terminal identification
  - Wire numbers
  - Test results (Pass/Fail)
  - Date and technician signature

### Test Documentation Required
1. **Point-to-Point Test Sheets** - All terminations mapped and verified
2. **Fiber Test Documentation** - Fiber runs from PLC panels to junction box/switches
3. **Ethernet Cable Test Documentation** - All CAT6 runs certified
4. **Continuity Test Results** - All power and control wiring verified

**All test documentation must be completed and submitted prior to cut-over**

---

## 8. INSTALLATION NOTES

### North Terminal Installation Sequence
1. Install junction box on North Pipe Rack
2. Run fiber from North Terminal PLC Panel to junction box (~80')
3. Install and terminate switch in junction box
4. Run power cable P-0107 for junction box switch
5. Install conduit from junction box to wire tray (40' vertical)
6. Run horizontal conduit from wire tray to each kiosk location (20' ea.)
7. Run vertical conduit from wire tray to each kiosk (40' ea.)
8. Pull CAT6 cables E-0101 through E-0106 (6 kiosk runs)
9. Pull power cables P-0101 through P-0106 (6 kiosk runs)
10. Terminate all cables at junction box and PLC panel
11. Terminate all cables at kiosks
12. Test all connections
13. Label all cables per approved drawings

### South Terminal Installation Sequence
1. Remove existing PLC panel (coordinate with operations)
2. Install new PLC panel in office building
3. Run conduit from PLC panel to loading bay area
4. Install wire tray routing along loading bays
5. Run vertical/horizontal conduit to Kiosk #1 location
6. Run vertical/horizontal conduit to Kiosk #2 location (can use direct route from outside)
7. Pull CAT6 cables E-0201 and E-0202
8. Pull power cables P-0201 and P-0202
9. Terminate all cables at PLC panel
10. Terminate all cables at kiosks
11. Test all connections
12. Label all cables per approved drawings

### Critical Requirements
- **All drawings require Engineering approval before installation**
- **Wire labels must match approved drawings or authorized redlines**
- **No deviations without documented approval**
- **Progress updates via project tracker (weekly minimum)**

---

## 9. MATERIAL REQUIREMENTS CHECKLIST

### Cable Materials
- [ ] 24 VDC Power Cable - Approximately 2,000' total (10 runs, average 200')
- [ ] CAT6 Ethernet Cable - Approximately 1,800' total (9 runs, average 200')
- [ ] Fiber Optic Cable - Approximately 200' (junction box uplink + spare)

### Conduit Materials
- [ ] Conduit (Type: ___) - 750-800' total
- [ ] Conduit fittings, elbows, couplings
- [ ] Wire tray sections and supports
- [ ] Junction box mounting hardware

### Termination Materials
- [ ] Cable labels (P-xxxx and E-xxxx series)
- [ ] Terminal blocks for PLC panels
- [ ] RJ45 connectors and patch panels
- [ ] Fiber termination kits
- [ ] Cable ties, supports, strain reliefs

### Equipment
- [ ] Junction Box (North Terminal)
- [ ] Network Switch (for junction box)
- [ ] 6 Kiosks (North Terminal)
- [ ] 2 Kiosks (South Terminal)
- [ ] Radio equipment (South Shop/MCC)
- [ ] Fiber optic transceivers
- [ ] Power supplies (24 VDC as required)

---

## 10. COORDINATION REQUIREMENTS

### I&E Department Responsibilities
- Conduit installation (all locations)
- CAT6 cable pulling and terminations
- Cable testing (continuity and connectivity)
- North Terminal junction box installation
- Lift rental for installation
- Genesis Work Plan creation and review

### Automation Department Responsibilities
- Provide all project drawings (interconnect, cable schedules, panel terminations)
- PLC panels, switches, fiber kits, kiosks, radio hardware procurement
- Fiber terminations and testing
- CAT6 termination verification and testing
- Final documentation package
- Work Pack/PAC creation
- Genesis Work Plan creation and review

### Required Approvals Before Installation
- [ ] Engineering approval on all drawings
- [ ] Cable schedule approved (this document)
- [ ] Interconnect drawings approved
- [ ] Panel termination drawings approved
- [ ] Genesis Work Plans approved
- [ ] Work Packs/PACs approved

---

## 11. REVISION HISTORY

| Rev | Date | Description | Approved By |
|-----|------|-------------|-------------|
| 1.0 | 2025-11-11 | Initial cable schedule creation | Pending |
|     |            |                                  |          |
|     |            |                                  |          |

---

## APPENDIX A: Cable ID Quick Reference

### North Terminal (P-01xx / E-01xx)
- P-0101 / E-0101: Terminal Kiosk #1
- P-0102 / E-0102: Terminal Kiosk #2
- P-0103 / E-0103: Terminal Kiosk #3
- P-0104 / E-0104: Terminal Kiosk #4
- P-0105 / E-0105: Terminal Kiosk #5
- P-0106 / E-0106: Terminal Kiosk #6
- P-0107 / E-0107: Junction Box Switch/Uplink

### South Terminal (P-02xx / E-02xx)
- P-0201 / E-0201: Terminal Kiosk #1
- P-0202 / E-0202: Terminal Kiosk #2

### South Shop/MCC (P-03xx / E-03xx)
- P-0301 / E-0301: Radio Equipment

---

**END OF CABLE SCHEDULE**
