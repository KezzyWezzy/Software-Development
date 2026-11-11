#!/usr/bin/env python3
"""Build a TX/LA pipeline-operator target list from PHMSA annual report data.

Input: PHMSA "Annual Report Mileage" files (hazardous liquid and/or gas
transmission), downloaded manually from
https://www.phmsa.dot.gov/data-and-statistics/pipeline/gas-distribution-gas-gathering-gas-transmission-hazardous-liquids
Pass the .zip files as downloaded, or the .xlsx files extracted from them.

Output: a CSV of every operator with mileage in the target states, plus a
markdown summary ranking the "sweet spot" prospects for an LDS + drone-dock
offering (10-100 miles in TX/LA, small total system).

PHMSA column names have shifted over the years, so columns are auto-detected
by pattern. Run with --list-columns to see what a file contains and override
any detection with the --*-col flags.
"""
from __future__ import annotations

import argparse
import math
import re
import sys
import zipfile
from pathlib import Path

import pandas as pd

MILES_PER_DOCK = 15  # linear miles one dock can patrol out-and-back

# Ordered regex candidates; first match wins.
PATTERNS = {
    "operator_id": [r"^OPERATOR_ID$", r"OPERATOR.?ID"],
    "operator_name": [r"NAMEOFCOMP", r"^OPERATOR_NAME$", r"PARTA2.*NAME", r"NAME"],
    "state": [r"^STATE_NAME$", r"^STATE$", r"STATE"],
    "commodity": [r"COMMODITY", r"COMM"],
    "total_miles": [r"^PARTBTOTAL$", r"PARTB.*TOTAL$", r"TOTAL.*MILES", r"MILES.*TOTAL",
                    r"^PARTLTOTAL$", r"PART[A-Z].*TOTAL$"],
    "hca_miles": [r"PARTBHCATOTAL", r"HCA.*TOTAL", r"TOTAL.*HCA"],
    "year": [r"REPORT_YEAR", r"YEAR"],
}


def find_col(cols: list[str], key: str, override: str | None) -> str | None:
    if override:
        if override not in cols:
            sys.exit(f"--{key.replace('_', '-')}-col '{override}' not in file columns")
        return override
    for pat in PATTERNS[key]:
        for c in cols:
            if re.search(pat, c, re.IGNORECASE):
                return c
    return None


def read_sheets(path: Path) -> list[tuple[str, pd.DataFrame]]:
    """Return (label, raw frame) for every sheet of every xlsx in path."""
    out = []
    if path.suffix.lower() == ".zip":
        with zipfile.ZipFile(path) as z:
            names = [n for n in z.namelist() if n.lower().endswith((".xlsx", ".xls"))]
            # Use only the newest report year found in the archive.
            names.sort(key=lambda n: max(re.findall(r"(20\d\d)", n) or ["0"]))
            for n in names[-1:]:
                with z.open(n) as fh:
                    for sheet, df in pd.read_excel(fh, sheet_name=None, header=None).items():
                        out.append((f"{path.name}:{n}:{sheet}", df))
    else:
        for sheet, df in pd.read_excel(path, sheet_name=None, header=None).items():
            out.append((f"{path.name}:{sheet}", df))
    return out


def promote_header(raw: pd.DataFrame) -> pd.DataFrame | None:
    """PHMSA sheets have title/note rows above the header. The header is the row
    with a cell that is exactly OPERATOR_ID (note rows merely mention it)."""
    for i in range(min(25, len(raw))):
        row = [str(v).strip().upper() for v in raw.iloc[i].tolist()]
        if "OPERATOR_ID" in row or "OPERATOR ID" in row:
            df = raw.iloc[i + 1:].copy()
            df.columns = [str(v).strip() for v in raw.iloc[i].tolist()]
            df = df.loc[:, [c for c in df.columns if c and c.lower() != "nan"]]
            return df.dropna(how="all")
    return None


def system_label(label: str) -> str:
    low = label.lower()
    if "liquid" in low:
        return "Hazardous liquid"
    if "gather" in low and "transmission" not in low:
        return "Gas gathering"
    if "gas" in low:
        return "Gas transmission/gathering"
    return "Unknown"


def total_col(cols: list[str]) -> str | None:
    """Grand-total mileage column of a breakdown sheet: a *TOTAL* column that is
    not an HCA subtotal; prefer names mentioning MILES, else the last one."""
    cands = [c for c in cols if "TOTAL" in c.upper() and "HCA" not in c.upper()]
    miles = [c for c in cands if "MILE" in c.upper()]
    return (miles or cands or [None])[-1]


def hca_col(cols: list[str]) -> str | None:
    """Total HCA miles column. Requires TOTAL in the name and skips non-HCA /
    outside-HCA columns (NON, NOT, NHCA, OUTSIDE)."""
    bad = ("NON", "NOT", "NHCA", "OUTSIDE")
    cands = [c for c in cols if "HCA" in c.upper() and "TOTAL" in c.upper()
             and not any(b in c.upper() for b in bad)]
    return (cands or [None])[-1]


def load(path: Path, args) -> pd.DataFrame:
    """PHMSA 2023+ annual files split each report across sheets ("Part A to E",
    "Part H", ...). Operator names live on a sheet without STATE_NAME; mileage
    lives on per-state breakdown sheets. Join them on OPERATOR_ID."""
    names: dict = {}
    op_hca: dict = {}
    hca_src = None
    state_sheets: list[tuple[str, pd.DataFrame, dict]] = []
    for label, raw in read_sheets(path):
        df = promote_header(raw)
        if df is None:
            continue
        cols = list(df.columns)
        if args.list_columns:
            print(f"\n== {label} ==\n" + "\n".join(cols))
            continue
        m = {k: find_col(cols, k, None) for k in ("operator_id", "operator_name", "state", "commodity")}
        m["operator_id"] = args.operator_id_col or m["operator_id"]
        # Only STATE_NAME marks a per-state breakdown sheet; other *STATE* columns
        # (e.g. the operator's office address on Part A) are not where pipe runs.
        m["state"] = args.state_col if args.state_col in cols else \
            next((c for c in cols if c.upper() in ("STATE_NAME", "STATE")), None)
        if not m["operator_id"]:
            continue
        name_col = args.operator_name_col if args.operator_name_col in cols else m["operator_name"]
        if name_col and name_col != m["state"]:
            for oid, nm in zip(df[m["operator_id"]], df[name_col]):
                if pd.notna(nm) and str(nm).strip():
                    names.setdefault(oid, str(nm).strip())
        if not m["state"]:
            hc = args.hca_miles_col if args.hca_miles_col in cols else \
                next((c for c in cols if c.upper() in ("PARTBHCATOTAL", "PARTB_HCA_TOTAL")), None) or \
                hca_col([c for c in cols if c.upper().startswith("PARTB")])
            if hc:
                vals = pd.to_numeric(df[hc], errors="coerce").fillna(0)
                for oid, v in zip(df[m["operator_id"]], vals):
                    op_hca[oid] = op_hca.get(oid, 0.0) + float(v)
                hca_src = f"{label.split(':')[-1]} / {hc}"
        if m["state"]:
            m["total"] = args.total_miles_col if args.total_miles_col in cols else total_col(cols)
            m["hca"] = args.hca_miles_col if args.hca_miles_col in cols else hca_col(cols)
            state_sheets.append((label, df, m))
    if args.list_columns or not state_sheets:
        return pd.DataFrame()

    def all_sum(df, mm):
        if not mm["total"]:
            return 0.0
        return float(pd.to_numeric(df[mm["total"]], errors="coerce").fillna(0).sum())

    # Pick the mileage sheet: several breakdown parts (by pipe size, decade,
    # SMYS, ...) each sum to the same system total, so take the total that the
    # most sheets agree on. --miles-sheet overrides.
    sums = [(lbl, d, mm, all_sum(d, mm)) for lbl, d, mm in state_sheets]
    print(f"\n{path.name}: candidate mileage columns (all-state sums):", file=sys.stderr)
    for lbl, _, mm, s in sums:
        print(f"  {lbl.split(':')[-1]:<28} total={mm['total']!s:<30} miles={s:,.1f}", file=sys.stderr)
    if args.miles_sheet:
        pick = next((x for x in sums if args.miles_sheet.lower() in x[0].lower()), None)
        if not pick:
            sys.exit(f"--miles-sheet '{args.miles_sheet}' matched no sheet")
    else:
        valid = [x for x in sums if x[3] > 0]
        if not valid:
            print(f"  no mileage found in {path.name}; use --list-columns", file=sys.stderr)
            return pd.DataFrame()
        agree = lambda x: sum(abs(y[3] - x[3]) <= 0.01 * max(x[3], 1) for y in valid)
        pick = max(valid, key=lambda x: (agree(x), x[3]))
    lbl, df, mm, _ = pick
    print(f"  -> mileage from {lbl.split(':')[-1]} / {mm['total']}", file=sys.stderr)

    out = pd.DataFrame({
        "operator_id": df[mm["operator_id"]],
        "state": df[mm["state"]].astype(str).str.strip().str.upper(),
        "commodity": df[mm["commodity"]].astype(str).str.strip() if mm["commodity"] else "",
        "total_miles": pd.to_numeric(df[mm["total"]], errors="coerce").fillna(0),
    })
    out = out.groupby(["operator_id", "state"], as_index=False).agg(
        commodity=("commodity", lambda s: "; ".join(sorted({c for c in s if c and c != "nan"}))),
        total_miles=("total_miles", "sum"))

    # HCA miles are reported per report on Part B (Part A-E / A-D sheet), not
    # per state. Spread each operator's HCA share across its states by mileage:
    # exact for single-state operators, an estimate for multi-state ones.
    system = out.groupby("operator_id")["total_miles"].sum()
    if op_hca:
        print(f"  -> HCA miles from {hca_src} (allocated to states by mileage)", file=sys.stderr)
    share = {o: min(1.0, op_hca.get(o, 0.0) / m) if m else 0.0 for o, m in system.items()}
    out["hca_miles"] = out["total_miles"] * out["operator_id"].map(share).fillna(0)
    out["operator_name"] = out["operator_id"].map(names).fillna("(unknown)").astype(str)
    out["system"] = system_label(lbl)
    return out


STATES = {
    "AL": "ALABAMA", "AK": "ALASKA", "AZ": "ARIZONA", "AR": "ARKANSAS", "CA": "CALIFORNIA",
    "CO": "COLORADO", "CT": "CONNECTICUT", "DE": "DELAWARE", "FL": "FLORIDA", "GA": "GEORGIA",
    "HI": "HAWAII", "ID": "IDAHO", "IL": "ILLINOIS", "IN": "INDIANA", "IA": "IOWA", "KS": "KANSAS",
    "KY": "KENTUCKY", "LA": "LOUISIANA", "ME": "MAINE", "MD": "MARYLAND", "MA": "MASSACHUSETTS",
    "MI": "MICHIGAN", "MN": "MINNESOTA", "MS": "MISSISSIPPI", "MO": "MISSOURI", "MT": "MONTANA",
    "NE": "NEBRASKA", "NV": "NEVADA", "NH": "NEW HAMPSHIRE", "NJ": "NEW JERSEY", "NM": "NEW MEXICO",
    "NY": "NEW YORK", "NC": "NORTH CAROLINA", "ND": "NORTH DAKOTA", "OH": "OHIO", "OK": "OKLAHOMA",
    "OR": "OREGON", "PA": "PENNSYLVANIA", "RI": "RHODE ISLAND", "SC": "SOUTH CAROLINA",
    "SD": "SOUTH DAKOTA", "TN": "TENNESSEE", "TX": "TEXAS", "UT": "UTAH", "VT": "VERMONT",
    "VA": "VIRGINIA", "WA": "WASHINGTON", "WV": "WEST VIRGINIA", "WI": "WISCONSIN", "WY": "WYOMING",
    "DC": "DISTRICT OF COLUMBIA", "PR": "PUERTO RICO",
}


def classify(row) -> str:
    miles, total = row["state_miles"], row["system_miles_all_states"]
    if 10 <= miles <= 100 and total <= 300:
        return "A - sweet spot (1-7 docks covers system)"
    if miles > 100 and row["hca_miles_est"] > 0:
        return "B - large; pitch HCA-segment docks + alarm verification"
    if miles < 10:
        return "C - very short; single dock / facility-scale"
    return "B - mid/large regional"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="+", type=Path, help="PHMSA annual report .zip or .xlsx files")
    ap.add_argument("--states", default="TX,LA",
                    help="comma-separated states (abbrev. or full name), or ALL (default TX,LA)")
    ap.add_argument("--out", type=Path, default=Path("pipeline_targets"), help="output path prefix")
    ap.add_argument("--top", type=int, default=25, help="tier-A rows per state in the .md summary")
    ap.add_argument("--list-columns", action="store_true", help="print detected sheet columns and exit")
    ap.add_argument("--miles-sheet", help="sheet-name substring to take mileage from (e.g. 'Part J')")
    for k in PATTERNS:
        ap.add_argument(f"--{k.replace('_', '-')}-col", dest=f"{k}_col", help=f"override {k} column")
    args = ap.parse_args()

    data = pd.concat([load(f, args) for f in args.files], ignore_index=True)
    if args.list_columns:
        return
    if data.empty:
        sys.exit("No usable sheets found. Run with --list-columns and pass --*-col overrides.")

    data["state"] = data["state"].replace(STATES)  # normalize any abbreviations
    if args.states.strip().upper() == "ALL":
        wanted = sorted(set(data["state"]) - {"", "NAN", "NONE"})
    else:
        wanted = [STATES.get(x.strip().upper(), x.strip().upper()) for x in args.states.split(",") if x.strip()]

    keys = ["operator_id", "operator_name", "system"]
    system_total = data.groupby(keys)["total_miles"].sum().rename("system_miles_all_states")
    other_states = data[data["total_miles"] > 0].groupby(keys)["state"].nunique().rename("states_operated")
    res = data[data["state"].isin(wanted) & (data["total_miles"] > 0)].rename(
        columns={"total_miles": "state_miles", "hca_miles": "hca_miles_est", "commodity": "commodities"})
    res = res.join(system_total, on=keys).join(other_states, on=keys)
    res["est_docks_for_full_coverage"] = res["state_miles"].apply(lambda m: max(1, math.ceil(m / MILES_PER_DOCK)))
    res["hca_share"] = (res["hca_miles_est"] / res["state_miles"]).round(2)
    res["tier"] = res.apply(classify, axis=1)
    res = res.sort_values(["state", "tier", "hca_miles_est", "state_miles"], ascending=[True, True, False, False])
    cols = ["state", "operator_id", "operator_name", "system", "commodities", "state_miles", "hca_miles_est",
            "hca_share", "system_miles_all_states", "states_operated", "est_docks_for_full_coverage", "tier"]
    res = res[cols]

    csv_path = args.out.with_suffix(".csv")
    res.round(1).to_csv(csv_path, index=False)

    by_state = res.groupby("state")["state_miles"].sum().sort_values(ascending=False)
    md = ["# Pipeline operator target list by state", "",
          f"Source: PHMSA annual report data ({', '.join(f.name for f in args.files)}).",
          "HCA miles are reported per operator, not per state; for multi-state operators they are",
          "spread across states by mileage (estimate).", "",
          "## States ranked by regulated miles", "",
          "| State | Operators | Miles | Est. HCA miles | Tier-A operators |", "|---|---:|---:|---:|---:|"]
    for st in by_state.index:
        g = res[res["state"] == st]
        md.append(f"| {st.title()} | {g['operator_id'].nunique()} | {g['state_miles'].sum():,.0f} "
                  f"| {g['hca_miles_est'].sum():,.0f} | {(g['tier'].str.startswith('A')).sum()} |")
    for st in by_state.index:
        g = res[res["state"] == st]
        md += ["", f"## {st.title()}", "", "| Tier | Operators | Miles |", "|---|---:|---:|"]
        for tier, t in g.groupby("tier"):
            md.append(f"| {tier} | {len(t)} | {t['state_miles'].sum():,.0f} |")
        top = g[g["tier"].str.startswith("A")].head(args.top)
        if len(top):
            md += ["", f"Top tier-A prospects in {st.title()} (by est. HCA miles, then miles):", "",
                   "| Operator | System | Miles here | Est. HCA | Commodities | Docks |",
                   "|---|---|---:|---:|---|---:|"]
            for _, r in top.iterrows():
                md.append(f"| {r.operator_name} | {r.system} | {r.state_miles:.0f} | {r.hca_miles_est:.0f} "
                          f"| {r.commodities} | {r.est_docks_for_full_coverage} |")
    md_path = args.out.with_suffix(".md")
    md_path.write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"wrote {csv_path} ({len(res)} operator-state rows, {len(by_state)} states) and {md_path}")


if __name__ == "__main__":
    main()
