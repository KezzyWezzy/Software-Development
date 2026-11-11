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

TARGET_STATES = {"TX": "TEXAS", "LA": "LOUISIANA"}
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
        if m["state"]:
            m["total"] = args.total_miles_col if args.total_miles_col in cols else total_col(cols)
            m["hca"] = args.hca_miles_col if args.hca_miles_col in cols else hca_col(cols)
            state_sheets.append((label, df, m))
    if args.list_columns or not state_sheets:
        return pd.DataFrame()

    states = set(TARGET_STATES) | set(TARGET_STATES.values())

    def tgt_sum(df, mm):
        if not mm["total"]:
            return 0.0
        st = df[mm["state"]].astype(str).str.strip().str.upper()
        return float(pd.to_numeric(df.loc[st.isin(states), mm["total"]], errors="coerce").fillna(0).sum())

    # Pick the mileage sheet: several breakdown parts (by pipe size, decade,
    # SMYS, ...) each sum to the same system total, so take the total that the
    # most sheets agree on. --miles-sheet overrides.
    sums = [(lbl, d, mm, tgt_sum(d, mm)) for lbl, d, mm in state_sheets]
    print(f"\n{path.name}: candidate mileage columns (TX+LA sums):", file=sys.stderr)
    for lbl, _, mm, s in sums:
        print(f"  {lbl.split(':')[-1]:<28} total={mm['total']!s:<30} hca={mm['hca']!s:<25} TX+LA={s:,.1f}",
              file=sys.stderr)
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
    print(f"  -> using {lbl.split(':')[-1]} / {mm['total']}", file=sys.stderr)

    out = pd.DataFrame({
        "operator_id": df[mm["operator_id"]],
        "state": df[mm["state"]].astype(str).str.strip().str.upper(),
        "commodity": df[mm["commodity"]].astype(str).str.strip() if mm["commodity"] else "",
        "total_miles": pd.to_numeric(df[mm["total"]], errors="coerce").fillna(0),
        "hca_miles": 0.0,
    })
    # HCA miles: from the picked sheet if it has them, else the first sheet that does.
    hsrc = next(((d, x) for l2, d, x, _ in sums if x["hca"] and d is df), None) or \
        next(((d, x) for l2, d, x, _ in sums if x["hca"]), None)
    if hsrc:
        hd, hx = hsrc
        hl = next(l2 for l2, d, x, _ in sums if d is hd)
        print(f"  -> HCA miles from {hl.split(':')[-1]} / {hx['hca']}", file=sys.stderr)
        h = pd.DataFrame({"operator_id": hd[hx["operator_id"]],
                          "state": hd[hx["state"]].astype(str).str.strip().str.upper(),
                          "hca": pd.to_numeric(hd[hx["hca"]], errors="coerce").fillna(0)})
        h = h.groupby(["operator_id", "state"])["hca"].sum()
        out = out.groupby(["operator_id", "state"], as_index=False).agg(
            commodity=("commodity", lambda s: "; ".join(sorted({c for c in s if c and c != "nan"}))),
            total_miles=("total_miles", "sum"))
        out["hca_miles"] = [h.get((o, s), 0.0) for o, s in zip(out["operator_id"], out["state"])]
    out["operator_name"] = out["operator_id"].map(names).fillna("(unknown)").astype(str)
    out["system"] = system_label(lbl)
    return out


def classify(row) -> str:
    tgt, total = row["target_miles"], row["system_miles_all_states"]
    if 10 <= tgt <= 100 and total <= 300:
        return "A - sweet spot (1-7 docks covers system)"
    if tgt > 100 and row["target_hca_miles"] > 0:
        return "B - large; pitch HCA-segment docks + alarm verification"
    if tgt < 10:
        return "C - very short; single dock / facility-scale"
    return "B - mid/large regional"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="+", type=Path, help="PHMSA annual report .zip or .xlsx files")
    ap.add_argument("--out", type=Path, default=Path("tx_la_pipeline_targets"), help="output path prefix")
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

    states = set(TARGET_STATES) | set(TARGET_STATES.values())
    data["in_target"] = data["state"].isin(states)
    keys = ["operator_id", "operator_name", "system"]

    system_total = data.groupby(keys)["total_miles"].sum().rename("system_miles_all_states")
    tgt = data[data["in_target"]]
    per_state = tgt.pivot_table(index=keys, columns="state", values="total_miles",
                                aggfunc="sum", fill_value=0).add_prefix("miles_")
    agg = tgt.groupby(keys).agg(
        target_miles=("total_miles", "sum"),
        target_hca_miles=("hca_miles", "sum"),
        commodities=("commodity", lambda s: "; ".join(sorted({c for c in s if c and c != "nan"}))),
    )
    res = agg.join(per_state).join(system_total).reset_index()
    res = res[res["target_miles"] > 0].copy()
    res["est_docks_for_full_coverage"] = res["target_miles"].apply(lambda m: max(1, math.ceil(m / MILES_PER_DOCK)))
    res["hca_share"] = (res["target_hca_miles"] / res["target_miles"]).round(2)
    res["tier"] = res.apply(classify, axis=1)
    res = res.sort_values(["tier", "target_hca_miles", "target_miles"], ascending=[True, False, False])

    csv_path = args.out.with_suffix(".csv")
    res.round(1).to_csv(csv_path, index=False)

    md = ["# TX/LA pipeline operator target list", "",
          f"Source: PHMSA annual report data ({', '.join(f.name for f in args.files)}).", "",
          "| Tier | Operators | TX+LA miles |", "|---|---:|---:|"]
    for tier, g in res.groupby("tier"):
        md.append(f"| {tier} | {len(g)} | {g['target_miles'].sum():,.0f} |")
    top = res[res["tier"].str.startswith("A")].head(50)
    md += ["", "## Top tier-A prospects (ranked by HCA miles, then miles)", "",
           "| Operator | System | TX+LA miles | HCA miles | Commodities | Docks |",
           "|---|---|---:|---:|---|---:|"]
    for _, r in top.iterrows():
        md.append(f"| {r.operator_name} | {r.system} | {r.target_miles:.0f} | {r.target_hca_miles:.0f} "
                  f"| {r.commodities} | {r.est_docks_for_full_coverage} |")
    md_path = args.out.with_suffix(".md")
    md_path.write_text("\n".join(md) + "\n")
    print(f"wrote {csv_path} ({len(res)} operators) and {md_path}")


if __name__ == "__main__":
    main()
