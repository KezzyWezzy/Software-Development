#!/usr/bin/env python3
"""
Red River DTN & PLC Upgrade - Cisco switch configuration generator.

Reads network/site_inventory.yaml (the single source of truth) and emits:

  network/configs/<SWITCH>.cfg   one paste-ready IOS-XE config per switch
  network/configs/port_map.csv   port <-> cable-ID <-> device cross reference

The generator is deterministic: same inventory in, byte-identical configs out.
Never hand-edit a generated .cfg - edit the inventory and re-run.

Usage:
    python3 network/tools/gen_switch_configs.py [--check] [--out DIR]

    --check   validate the inventory only (no files written); non-zero exit
              on any duplicate IP, duplicate port, unknown VLAN or bad role.

Target platform: Cisco IE-3300-8T2S, IOS-XE 17.x.
Catalyst 9200/C1000 deltas are listed in network/docs/Network_Design.md.
"""

from __future__ import annotations

import argparse
import csv
import ipaddress
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.exit("PyYAML is required:  pip install pyyaml")

REPO = Path(__file__).resolve().parents[2]
INVENTORY = REPO / "network" / "site_inventory.yaml"
DEFAULT_OUT = REPO / "network" / "configs"

VALID_ROLES = {
    "uplink_trunk",
    "downlink_trunk",
    "radio_trunk",
    "kiosk",
    "plc",
    "server",
    "parking",
}
TRUNK_ROLES = {"uplink_trunk", "downlink_trunk", "radio_trunk"}
ACCESS_ROLES = {"kiosk", "plc", "server"}

# Ports that carry EtherNet/IP CIP traffic must NOT have multicast storm
# control applied - CIP class 1 implicit I/O is multicast and would be policed.
CIP_ROLES = {"plc"}

PLACEHOLDER = "<<REPLACE-BEFORE-DEPLOY>>"


# --------------------------------------------------------------------------
# validation
# --------------------------------------------------------------------------
def validate(inv: dict) -> list[str]:
    """Return a list of human-readable problems. Empty list == inventory is sane."""
    problems: list[str] = []

    vlan_ids = {v["id"] for v in inv["vlans"]}
    for vid in inv["trunk_allowed_vlans"] + [
        inv["native_vlan"],
        inv["parking_vlan"],
        inv["mgmt_vlan"],
    ]:
        if vid not in vlan_ids:
            problems.append(f"VLAN {vid} is referenced but not defined in vlans:")

    if inv["native_vlan"] in inv["trunk_allowed_vlans"]:
        problems.append(
            f"native VLAN {inv['native_vlan']} must not appear in trunk_allowed_vlans"
        )

    subnets = {
        v["id"]: ipaddress.ip_network(v["subnet"])
        for v in inv["vlans"]
        if v.get("subnet")
    }

    seen_ips: dict[str, str] = {}
    seen_names: set[str] = set()

    def claim_ip(ip: str, owner: str, vlan_hint: int | None = None) -> None:
        if ip in seen_ips:
            problems.append(f"duplicate IP {ip}: {seen_ips[ip]} and {owner}")
            return
        seen_ips[ip] = owner
        addr = ipaddress.ip_address(ip)
        if vlan_hint is not None and vlan_hint in subnets:
            if addr not in subnets[vlan_hint]:
                problems.append(
                    f"{owner}: {ip} is outside VLAN {vlan_hint} "
                    f"({subnets[vlan_hint]})"
                )
        elif not any(addr in net for net in subnets.values()):
            problems.append(f"{owner}: {ip} does not fall inside any defined VLAN subnet")

    for sw in inv["switches"]:
        name = sw["name"]
        if name in seen_names:
            problems.append(f"duplicate switch name {name}")
        seen_names.add(name)

        claim_ip(sw["mgmt_ip"], f"{name} mgmt", inv["mgmt_vlan"])

        seen_ports: set[str] = set()
        for port in sw["ports"]:
            pid = port["id"]
            if pid in seen_ports:
                problems.append(f"{name}: port {pid} defined more than once")
            seen_ports.add(pid)

            role = port["role"]
            if role not in VALID_ROLES:
                problems.append(f"{name} {pid}: unknown role '{role}'")
                continue

            if role in ACCESS_ROLES and not port.get("ip"):
                problems.append(f"{name} {pid}: role '{role}' has no ip: assigned")

            if port.get("ip"):
                claim_ip(port["ip"], f"{name} {pid}", access_vlan(inv, role))

            if role == "radio_trunk":
                for vid in port.get("radio_vlans", []):
                    if vid not in vlan_ids:
                        problems.append(f"{name} {pid}: radio VLAN {vid} not defined")

    stp = inv["spanning_tree"]
    for key in ("root_primary", "root_secondary"):
        if stp[key] not in seen_names:
            problems.append(f"spanning_tree.{key} '{stp[key]}' is not a defined switch")

    for radio in inv.get("radios", []):
        claim_ip(radio["mgmt_ip"], f"{radio['name']} mgmt", inv["mgmt_vlan"])

    return problems


def access_vlan(inv: dict, role: str) -> int | None:
    """Map an access-port role onto its VLAN id."""
    by_name = {v["name"]: v["id"] for v in inv["vlans"]}
    return {
        "kiosk": by_name.get("CTM_KIOSK"),
        "server": by_name.get("CTM_KIOSK"),
        "plc": by_name.get("PLC_CTRL"),
    }.get(role)


# --------------------------------------------------------------------------
# rendering helpers
# --------------------------------------------------------------------------
def vlan_list(ids) -> str:
    return ",".join(str(i) for i in sorted(ids))


def header(inv: dict, sw: dict) -> list[str]:
    p = inv["project"]
    return [
        "! " + "=" * 74,
        f"! {p['name']} - {sw['name']}",
        "! " + "=" * 74,
        f"! Document      : {p['doc_id']} rev {p['revision']}  ({p['status']})",
        f"! Site          : {sw['site']}",
        f"! Location      : {sw['location']}",
        f"! Platform      : {sw['platform']} (IOS-XE 17.x)",
        f"! Management    : {sw['mgmt_ip']}/{mask_to_prefix(sw['mgmt_mask'])} "
        f"on VLAN {inv['mgmt_vlan']}",
        f"! Cable ref     : {p['cable_schedule_ref']}",
        "!",
        "! GENERATED FILE - do not hand-edit.",
        "!   source   : network/site_inventory.yaml",
        "!   generator: network/tools/gen_switch_configs.py",
        "!",
        f"! Every {PLACEHOLDER} must be filled in before this config is loaded.",
        "! " + "=" * 74,
        "!",
    ]


def mask_to_prefix(mask: str) -> int:
    return ipaddress.IPv4Network(f"0.0.0.0/{mask}").prefixlen


def base_services(inv: dict, sw: dict) -> list[str]:
    g = inv["globals"]
    tz, dst = g["timezone"], g["dst"]
    out = [
        "! --- base services ---------------------------------------------------",
        f"hostname {sw['name']}",
        "!",
        "service timestamps debug datetime msec localtime show-timezone",
        "service timestamps log datetime msec localtime show-timezone",
        "service password-encryption",
        "no service pad",
        "!",
        f"clock timezone {tz['name']} {tz['offset_hours']} 0",
        f"clock summer-time {dst['name']} recurring",
        "!",
        f"ip domain name {g['domain_name']}",
        "no ip domain lookup",
        "!",
        "! --- authentication ---------------------------------------------------",
        "aaa new-model",
        "aaa authentication login default local",
        "aaa authorization exec default local",
        "!",
        f"enable algorithm-type scrypt secret {PLACEHOLDER}",
        f"username rradmin privilege 15 algorithm-type scrypt secret {PLACEHOLDER}",
        "!",
        "crypto key generate rsa modulus 2048 label SSH-KEY",
        "ip ssh version 2",
        "ip ssh time-out 60",
        "ip ssh authentication-retries 3",
        "no ip http server",
        "no ip http secure-server",
        "!",
        "! --- logging / time ---------------------------------------------------",
        "logging buffered 65536 informational",
        "logging trap informational",
    ]
    for host in g["syslog_servers"]:
        out.append(f"logging host {host}")
    out.append(f"logging source-interface Vlan{inv['mgmt_vlan']}")
    out.append("!")
    for srv in g["ntp_servers"]:
        out.append(f"ntp server {srv}")
    out.append(f"ntp source Vlan{inv['mgmt_vlan']}")
    out += [
        "!",
        "! --- SNMPv3 (read-only monitoring) -------------------------------------",
        f"snmp-server group {g['snmp']['v3_group']} v3 priv",
        f"snmp-server user {g['snmp']['v3_user']} {g['snmp']['v3_group']} v3 "
        f"auth sha {PLACEHOLDER} priv aes 128 {PLACEHOLDER}",
        f"snmp-server location {sw['site']} - {sw['location']}",
        "snmp-server contact KJV Solutions - Controls",
        f"snmp-server trap-source Vlan{inv['mgmt_vlan']}",
        "!",
        "! --- errdisable auto-recovery ------------------------------------------",
        "errdisable recovery cause bpduguard",
        "errdisable recovery cause psecure-violation",
        "errdisable recovery cause link-flap",
        "errdisable recovery cause storm-control",
        "errdisable recovery cause udld",
        "errdisable recovery interval 300",
        "!",
    ]
    banner = g["banner"].rstrip("\n")
    out.append("banner motd ^C")
    out += banner.splitlines()
    out += ["^C", "!"]
    return out


def vlan_block(inv: dict) -> list[str]:
    out = [
        "! --- VLANs -------------------------------------------------------------",
        "vtp mode transparent",
        "!",
    ]
    for v in inv["vlans"]:
        out.append(f"vlan {v['id']}")
        out.append(f" name {v['name']}")
        out.append(f" ! {v['desc']}")
    out.append("!")
    return out


def stp_block(inv: dict, sw: dict) -> list[str]:
    stp = inv["spanning_tree"]
    all_vlans = vlan_list([v["id"] for v in inv["vlans"]])
    out = [
        "! --- spanning tree -----------------------------------------------------",
        f"spanning-tree mode {stp['mode']}",
        "spanning-tree extend system-id",
        "spanning-tree portfast bpduguard default",
        "spanning-tree loopguard default",
        f"spanning-tree vlan {all_vlans} priority {sw['stp_priority']}",
    ]
    if sw["name"] == stp["root_primary"]:
        out.append("! ^ this switch is the intended STP ROOT for all VLANs")
    elif sw["name"] == stp["root_secondary"]:
        out.append("! ^ this switch is the intended STP BACKUP root")
    out.append("!")
    out.append("udld enable")
    out.append("!")
    return out


def mgmt_block(inv: dict, sw: dict) -> list[str]:
    gw = next(v["gateway"] for v in inv["vlans"] if v["id"] == inv["mgmt_vlan"])
    return [
        "! --- management interface ----------------------------------------------",
        f"interface Vlan{inv['mgmt_vlan']}",
        f" description NET_MGMT - in-band management for {sw['name']}",
        f" ip address {sw['mgmt_ip']} {sw['mgmt_mask']}",
        " no shutdown",
        "!",
        f"ip default-gateway {gw}",
        f"ip route 0.0.0.0 0.0.0.0 {gw}",
        "!",
        "! --- multicast (EtherNet/IP CIP class 1 I/O) ---------------------------",
        "! Snooping must stay ON. The IGMP querier is the plant core router on",
        "! each VLAN's gateway address. If the core cannot query the PLC VLAN,",
        "! promote SW-NT-PLC-01 by un-commenting the two lines below (ONE switch",
        "! on the network only - never two queriers on the same VLAN).",
        "ip igmp snooping",
        f"ip igmp snooping vlan {inv['mgmt_vlan']}",
        "! ip igmp snooping querier",
        "! ip igmp snooping vlan 20 querier address 10.14.20.2",
        "!",
    ]


def access_port(inv: dict, sw: dict, port: dict) -> list[str]:
    role = port["role"]
    vid = access_vlan(inv, role)
    cable = port.get("cable", "-")
    ip = port.get("ip", "-")
    out = [
        f"interface {port['id']}",
        f" description {role.upper()} | {port['desc']} | cable {cable} | {ip}",
        " switchport mode access",
        f" switchport access vlan {vid}",
        " switchport nonegotiate",
        " spanning-tree portfast",
        " spanning-tree bpduguard enable",
        " storm-control broadcast level pps 100 50",
        " storm-control unicast level pps 5k 4k",
    ]
    if role in CIP_ROLES:
        out.append(" ! NO multicast storm-control: CIP class 1 implicit I/O is")
        out.append(" ! multicast and would be policed off this port.")
    else:
        out.append(" storm-control multicast level pps 500 250")
    out += [
        " storm-control action trap",
        " switchport port-security",
        " switchport port-security maximum 1",
        " switchport port-security violation restrict",
        " switchport port-security aging time 0",
        " switchport port-security mac-address sticky",
    ]
    if role == "kiosk":
        out.append(" no cdp enable")
        out.append(" no lldp transmit")
        out.append(" no lldp receive")
    out += [
        " load-interval 30",
        " no shutdown",
        "!",
    ]
    return out


def trunk_port(inv: dict, port: dict) -> list[str]:
    role = port["role"]
    allowed = (
        port["radio_vlans"] if role == "radio_trunk" else inv["trunk_allowed_vlans"]
    )
    cable = port.get("cable", "-")
    out = [
        f"interface {port['id']}",
        f" description {role.upper()} | {port['desc']} | cable {cable}",
        " switchport mode trunk",
        f" switchport trunk native vlan {inv['native_vlan']}",
        f" switchport trunk allowed vlan {vlan_list(allowed)}",
        " switchport nonegotiate",
        " no spanning-tree portfast",
    ]
    if port.get("root_guard"):
        out.append(" spanning-tree guard root")
    if port.get("loop_guard"):
        out.append(" spanning-tree guard loop")
    if port.get("media") == "fiber":
        out.append(" udld port aggressive")
    if role == "radio_trunk":
        out.append(" ! Wireless bridge: VLAN 10 (kiosks) is deliberately NOT carried,")
        out.append(" ! and no CIP class 1 implicit I/O may cross this link. Explicit")
        out.append(" ! messaging / Modbus TCP only - see docs/Network_Design.md.")
        out.append(" storm-control broadcast level pps 100 50")
        out.append(" storm-control action trap")
    out += [
        " load-interval 30",
        " no shutdown",
        "!",
    ]
    return out


def parking_port(inv: dict, port: dict) -> list[str]:
    return [
        f"interface {port['id']}",
        f" description PARKING | {port['desc']}",
        " switchport mode access",
        f" switchport access vlan {inv['parking_vlan']}",
        " switchport nonegotiate",
        " spanning-tree portfast",
        " spanning-tree bpduguard enable",
        " shutdown",
        "!",
    ]


def lines_block() -> list[str]:
    return [
        "! --- console / vty -----------------------------------------------------",
        "line con 0",
        " exec-timeout 15 0",
        " logging synchronous",
        " login authentication default",
        "line vty 0 15",
        " exec-timeout 15 0",
        " logging synchronous",
        " transport input ssh",
        " transport output ssh",
        " login authentication default",
        "!",
        "end",
        "",
    ]


def render(inv: dict, sw: dict) -> str:
    out: list[str] = []
    out += header(inv, sw)
    out += base_services(inv, sw)
    out += vlan_block(inv)
    out += stp_block(inv, sw)
    out += mgmt_block(inv, sw)
    out += ["! --- interfaces ---------------------------------------------------------"]
    for port in sw["ports"]:
        role = port["role"]
        if role in TRUNK_ROLES:
            out += trunk_port(inv, port)
        elif role in ACCESS_ROLES:
            out += access_port(inv, sw, port)
        else:
            out += parking_port(inv, port)
    out += lines_block()
    return "\n".join(out)


def write_port_map(inv: dict, out_dir: Path) -> Path:
    path = out_dir / "port_map.csv"
    with path.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(
            ["switch", "site", "port", "role", "vlan", "cable_id", "device", "ip"]
        )
        for sw in inv["switches"]:
            for port in sw["ports"]:
                role = port["role"]
                if role in TRUNK_ROLES:
                    vlan = (
                        vlan_list(port["radio_vlans"])
                        if role == "radio_trunk"
                        else vlan_list(inv["trunk_allowed_vlans"])
                    )
                elif role in ACCESS_ROLES:
                    vlan = str(access_vlan(inv, role))
                else:
                    vlan = str(inv["parking_vlan"])
                w.writerow(
                    [
                        sw["name"],
                        sw["site"],
                        port["id"],
                        role,
                        vlan,
                        port.get("cable", ""),
                        port["desc"],
                        port.get("ip", ""),
                    ]
                )
    return path


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true", help="validate only, write nothing")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT, help="output directory")
    ap.add_argument("--inventory", type=Path, default=INVENTORY)
    args = ap.parse_args()

    inv = yaml.safe_load(args.inventory.read_text())

    problems = validate(inv)
    if problems:
        print(f"INVENTORY VALIDATION FAILED ({len(problems)} problem(s)):", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        return 1
    print(f"inventory OK: {len(inv['switches'])} switches, {len(inv['vlans'])} VLANs")

    if args.check:
        return 0

    args.out.mkdir(parents=True, exist_ok=True)
    for sw in inv["switches"]:
        path = args.out / f"{sw['name']}.cfg"
        path.write_text(render(inv, sw))
        print(f"  wrote {path.relative_to(REPO)} ({len(path.read_text().splitlines())} lines)")

    pm = write_port_map(inv, args.out)
    print(f"  wrote {pm.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
