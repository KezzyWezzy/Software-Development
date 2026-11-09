# TX/LA Pipeline Operator Target List

Builds a prospect list for the SpecFlow LDS + solar drone-dock offering from
PHMSA's public annual report mileage data.

## 1. Download the data (manual: PHMSA's site blocks automated downloads)

From <https://www.phmsa.dot.gov/data-and-statistics/pipeline/gas-distribution-gas-gathering-gas-transmission-hazardous-liquids>
download the **Annual Report Data** zips:

- Hazardous Liquid Annual Data (2010–present)
- Gas Transmission & Gathering Annual Data (2010–present)

Put them in `tools/pipeline_prospects/data/` (git-ignored).

## 2. Run

```bash
pip install pandas openpyxl
python tools/pipeline_prospects/build_target_list.py tools/pipeline_prospects/data/*.zip \
    --out tools/pipeline_prospects/tx_la_pipeline_targets
```

The script uses the newest report year in each zip. It writes
`tx_la_pipeline_targets.csv` (every operator with TX/LA miles) and
`tx_la_pipeline_targets.md` (a summary with the top prospects).

If a column isn't detected, run with `--list-columns`, then pass an override,
e.g. `--total-miles-col PARTBTOTAL --hca-miles-col PARTBHCATOTAL`.

## Tiers

| Tier | Rule | Pitch |
|---|---|---|
| A — sweet spot | 10–100 TX+LA miles, ≤300 miles system-wide | Full coverage with 1–7 docks + LDS |
| B — large | >100 TX+LA miles | Docks on HCA segments only + drone check of LDS alarms |
| C — very short | <10 miles | Single dock / facility-scale |

Dock estimate assumes about 15 linear miles of line per dock. That's a
planning number; refine it per site for terrain, wind and flight time.
