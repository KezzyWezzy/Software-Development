# Red River DTN & PLC Upgrade — Network Configuration Package

Cisco switch configuration for the Red River terminal upgrade: 4 switches,
3 sites, 8 CTM kiosks, 3 PLCs and one wireless link to the South Shop/MCC.

> **Status: ISSUED FOR REVIEW — not deployed.** Nothing here has been loaded
> onto hardware or validated against the site. Every design assumption is
> listed in `docs/Network_Design.md` §0 and must be confirmed first.

## Execution plan

| Phase | What | Where |
|-------|------|-------|
| 1 | Confirm assumptions (switch model, IP scheme, Proxim model, CTMPLCP scope, BSU location) | `docs/Network_Design.md` §0 |
| 2 | Update `site_inventory.yaml` for anything that differs, regenerate | this file, below |
| 3 | Bench build and load in the shop | `docs/Cutover_Plan.md` Stage 0 |
| 4 | North Terminal — new build, no service impact | Stage 1 |
| 5 | South Terminal — live, outage required | Stage 2 |
| 6 | South Shop/MCC wireless link | Stage 3 |
| 7 | Verify, document, turn over | Stage 4 + `docs/Verification_Checklist.md` |

## How this package works

`site_inventory.yaml` is the single source of truth. The generator reads it and
emits one paste-ready IOS-XE config per switch plus a port/cable cross
reference. The `.cfg` files are **build output** — hand-edit them and your
change is silently reverted on the next run.

```bash
# validate the inventory (duplicate IPs, unknown VLANs, bad roles) - writes nothing
python3 network/tools/gen_switch_configs.py --check

# regenerate all configs + port_map.csv
python3 network/tools/gen_switch_configs.py
```

Change a VLAN, an address or a port assignment → edit the YAML → regenerate →
commit the inventory and the configs together.

## Layout

```
network/
├── site_inventory.yaml            source of truth
├── tools/gen_switch_configs.py    generator + validator
├── configs/
│   ├── SW-NT-PLC-01.cfg           North Terminal CTM PLC panel  (STP root)
│   ├── SW-NT-JB-01.cfg            North pipe rack junction box  (6 kiosks)
│   ├── SW-ST-PLC-01.cfg           South Terminal CTM PLC panel  (2 kiosks + radio)
│   ├── SW-MCC-01.cfg              South Shop / MCC              (radio + MCC PLC)
│   └── port_map.csv               port ↔ cable ID ↔ device ↔ IP
├── docs/
│   ├── Network_Design.md          topology, VLAN/IP plan, design decisions
│   ├── Cutover_Plan.md            staged runbook with rollback per step
│   └── Verification_Checklist.md  sign-off test sheet, one per switch
└── proxim/
    └── QB-8200_link_parameters.md radio-side settings
```

## Before anything is loaded

Each config contains four `<<REPLACE-BEFORE-DEPLOY>>` markers — enable secret,
admin secret, SNMPv3 auth and priv. Credentials are deliberately not stored in
this repository; pull them from the project vault at load time.

```bash
grep -c "REPLACE-BEFORE-DEPLOY" network/configs/*.cfg   # 4 per switch until filled
```

Related: `../Red_River_DTN_Cable_Schedule.md` (cable IDs referenced throughout),
`../Work Plan.html`.
