#!/usr/bin/env python3
"""
generate_data.py — build data/data.json for the Portal Intelligence dashboard.

CURRENT SOURCE (demo): an office-level Excel export scraped from Idealista
(Malaga province). See --input.

TARGET SOURCE (production): swap `load_from_excel()` for `load_from_bigquery()`
once BigQuery access is wired up. The dashboard only consumes the JSON shape
produced at the bottom of this file, so as long as that shape is preserved the
front-end needs no changes.

Usage:
    python3 generate_data.py --input "raw/offices_malaga.xlsx" --dataset-id es-malaga
"""
import argparse, json, math, os
import pandas as pd

# --- Gate / field mapping (source column -> meaning) -----------------------
# Gate 1: ICP Qualification   1=Premier 2=Qualified 3=Needs Review 4=Excluded
# Gate 2: JE Duplicate        1=already on JamesEdition 0=not on JE
# Gate 3: # Listings >= 1M EUR (luxury listing count)
# Gate 4: Listings Overlap Score (0..1)
ICP_MAP = {1: "Premier", 2: "Qualified", 3: "Needs Review", 4: "Excluded"}
PORTAL_MODELS = {"portal", "portal_hybrid"}


def _num(series):
    return pd.to_numeric(series, errors="coerce")


def _s(v):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return None
    return v


def load_from_excel(path: str) -> pd.DataFrame:
    """Demo loader. Reads the scraped office export."""
    return pd.read_excel(path)


# --- BigQuery production loader --------------------------------------------
# Maps the snake_case columns the SQL returns -> the exact column names build()
# already consumes (kept identical to the Excel export, so build() is unchanged).
BQ_COLUMN_MAP = {
    "office_name":            "Portal Office Name",
    "office_url":             "Portal URL",
    "city":                   "City",
    "region":                 "Region",
    "province":               "Province",
    "g1_icp_qualification":   "Gate 1: ICP Qualification",
    "icp_label":              "ICP Label",
    "g2_on_jamesedition":     "Gate 2: JE Duplicate",
    "g3_listings_ge_1m":      "Gate 3: # Listings ≥ 1M€",
    "g4_overlap_score":       "Gate 4: Listings Overlap Score",
    "icp_luxury_tier":        "ICP Luxury Tier",
    "icp_model":              "ICP Model",
    "icp_franchise":          "ICP Franchise",
    "icp_buyer_types":        "ICP Buyer Types",
    "icp_estimated_listings": "ICP Estimated Listings",
    "icp_years_operating":    "ICP Years Operating",
}

# Office-level query. TODO(data-eng): replace the *_TABLE placeholders with the
# real fully-qualified tables. The shape it returns must match BQ_COLUMN_MAP.
# Each competitor office becomes one row; gates are computed here in SQL so the
# Python side stays a thin transform.
BQ_OFFICE_SQL = """
WITH listings AS (              -- one row per scraped competitor listing
  SELECT
    office_id,
    price_eur,
    -- a listing counts as "luxury" at/above the €1M threshold
    IF(price_eur >= 1000000, 1, 0) AS is_lux
  FROM `{project}.{dataset}.LISTINGS_TABLE`
  WHERE portal = @portal
    AND (@province IS NULL OR province = @province)
),
listing_agg AS (
  SELECT
    office_id,
    COUNT(*)                         AS est_listings,     -- exact, not estimated, once BQ is live
    SUM(is_lux)                      AS listings_ge_1m
  FROM listings
  GROUP BY office_id
),
je_match AS (                   -- offices already present on JamesEdition
  SELECT DISTINCT office_id, 1 AS on_je
  FROM `{project}.{dataset}.JE_OFFICE_MATCH_TABLE`
)
SELECT
  o.name                              AS office_name,
  o.url                               AS office_url,
  o.city                              AS city,
  o.region                            AS region,
  o.province                          AS province,
  o.icp_qualification                 AS g1_icp_qualification,   -- 1..4
  o.icp_label                         AS icp_label,
  COALESCE(j.on_je, 0)                AS g2_on_jamesedition,      -- 1/0
  la.listings_ge_1m                   AS g3_listings_ge_1m,
  o.overlap_score                     AS g4_overlap_score,        -- 0..1
  o.luxury_tier                       AS icp_luxury_tier,
  o.business_model                    AS icp_model,
  o.is_franchise                      AS icp_franchise,           -- 1/0
  o.buyer_types                       AS icp_buyer_types,
  la.est_listings                     AS icp_estimated_listings,
  o.years_operating                   AS icp_years_operating
FROM `{project}.{dataset}.OFFICES_TABLE` o
LEFT JOIN listing_agg la USING (office_id)
LEFT JOIN je_match     j  USING (office_id)
WHERE o.portal = @portal
  AND (@province IS NULL OR o.province = @province)
"""


def load_from_bigquery(project=None, dataset=None, portal="Idealista",
                       province=None, location="EU") -> pd.DataFrame:
    """Production loader. Returns a DataFrame with the same columns build() expects.

    Auth comes from the environment (ADC / GOOGLE_APPLICATION_CREDENTIALS or a
    workload-identity / CI secret) — never hardcode a key. Config via flags or
    env: BQ_PROJECT, BQ_DATASET.
    """
    from google.cloud import bigquery  # lazy import: keeps the Excel path dependency-free

    project = project or os.environ.get("BQ_PROJECT", "jamesedition-152413")
    dataset = dataset or os.environ.get("BQ_DATASET", "market_intelligence")
    client = bigquery.Client(project=project)
    job_config = bigquery.QueryJobConfig(query_parameters=[
        bigquery.ScalarQueryParameter("portal", "STRING", portal),
        bigquery.ScalarQueryParameter("province", "STRING", province),
    ])
    sql = BQ_OFFICE_SQL.format(project=project, dataset=dataset)
    df = client.query(sql, job_config=job_config, location=location).to_dataframe()

    missing = [c for c in BQ_COLUMN_MAP if c not in df.columns]
    if missing:
        raise ValueError(f"BigQuery result is missing expected columns: {missing}. "
                         "Check the SELECT aliases against BQ_COLUMN_MAP.")
    return df.rename(columns=BQ_COLUMN_MAP)


def build(df: pd.DataFrame) -> dict:
    g1 = _num(df["Gate 1: ICP Qualification"])
    g2 = _num(df["Gate 2: JE Duplicate"])
    g3 = _num(df["Gate 3: # Listings ≥ 1M€"])
    g4 = _num(df["Gate 4: Listings Overlap Score"])
    est = _num(df["ICP Estimated Listings"])
    fr = _num(df["ICP Franchise"])

    rows = []
    for i, r in df.iterrows():
        model = _s(r.get("ICP Model"))
        rows.append({
            "name": _s(r.get("Portal Office Name")),
            "url": _s(r.get("Portal URL")),
            "city": (_s(r.get("City")) or "").replace("Malaga", "Málaga"),
            "region": _s(r.get("Region")) or "Andalucia",
            "province": _s(r.get("Province")) or "Málaga",
            "g1": None if pd.isna(g1[i]) else int(g1[i]),
            "icp": _s(r.get("ICP Label")) or ICP_MAP.get(None if pd.isna(g1[i]) else int(g1[i])),
            "g2": None if pd.isna(g2[i]) else int(g2[i]),
            "g3": None if pd.isna(g3[i]) else int(g3[i]),
            "g4": None if pd.isna(g4[i]) else round(float(g4[i]), 2),
            "tier": _s(r.get("ICP Luxury Tier")),
            "model": model,
            "franchise": None if pd.isna(fr[i]) else int(fr[i]),
            "buyers": _s(r.get("ICP Buyer Types")),
            "est": None if pd.isna(est[i]) else int(est[i]),
            "portal": 1 if model in PORTAL_MODELS else 0,
            "years": _s(r.get("ICP Years Operating")),
        })

    total = len(df)
    icp_ok = g1.isin([1, 2])
    not_je = g2 == 0
    lux = g3 >= 1
    core_mask = ~df["ICP Model"].isin(list(PORTAL_MODELS))

    agg = {
        "total": total,
        "region": "Andalucía",
        "province": "Málaga",
        "portal": "Idealista",
        "estTotal": int(est.fillna(0).sum()),
        "estCore": int(est[core_mask].fillna(0).sum()),
        "estMedian": int(est.median()),
        "luxListings": int(g3.fillna(0).sum()),
        "gate4": {
            "withOverlap": int((g4 > 0).sum()),
            "avg": round(float(g4[g4 > 0].mean()), 2) if (g4 > 0).any() else 0,
        },
        "funnel": {
            "total": total,
            "qualified": int(icp_ok.sum()),
            "qualifiedNotJE": int((icp_ok & not_je).sum()),
            "prime": int((icp_ok & not_je & lux).sum()),
        },
    }
    return {"agg": agg, "rows": rows}


def upsert_manifest(data_dir, entry):
    """Add or replace this dataset's entry in data/datasets.json (the switcher source)."""
    mpath = os.path.join(data_dir, "datasets.json")
    manifest = {"datasets": []}
    if os.path.exists(mpath):
        with open(mpath, encoding="utf-8") as f:
            manifest = json.load(f)
    ds = [d for d in manifest.get("datasets", []) if d.get("id") != entry["id"]]
    if entry.get("default"):
        for d in ds:
            d["default"] = False
    ds.append(entry)
    manifest["datasets"] = ds
    with open(mpath, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    return mpath


def main():
    ap = argparse.ArgumentParser(
        description="Build a dataset JSON (+ manifest entry) for the dashboard.")
    ap.add_argument("--input", default="raw/offices_malaga.xlsx",
                    help="Scraped office Excel export (when --source excel).")
    ap.add_argument("--source", choices=["excel", "bigquery"], default="excel")
    ap.add_argument("--data-dir", default=".",
                    help="Folder holding the dataset files + datasets.json.")
    ap.add_argument("--dataset-id", default="es-malaga",
                    help="Slug for this region, e.g. es-malaga, es-madrid, pt-lisbon.")
    ap.add_argument("--label", default=None,
                    help="Label shown in the dataset switcher (defaults from country/scope).")
    ap.add_argument("--country", default="Spain")
    ap.add_argument("--default", action="store_true",
                    help="Mark this dataset as the one loaded first.")
    ap.add_argument("--out", default=None,
                    help="Override output path (default: <data-dir>/<dataset-id>.json).")
    # BigQuery options (only used when --source bigquery). Auth via ADC / env — no keys here.
    ap.add_argument("--bq-project", default=None, help="GCP project (or env BQ_PROJECT).")
    ap.add_argument("--bq-dataset", default=None, help="BigQuery dataset (or env BQ_DATASET).")
    ap.add_argument("--portal", default="Idealista", help="Competitor portal to pull.")
    ap.add_argument("--bq-province", default=None,
                    help="Optional province filter for the BigQuery pull.")
    args = ap.parse_args()

    if args.source == "bigquery":
        df = load_from_bigquery(project=args.bq_project, dataset=args.bq_dataset,
                                portal=args.portal, province=args.bq_province)
    else:
        df = load_from_excel(args.input)
    out = build(df)

    out_path = args.out or os.path.join(args.data_dir, f"{args.dataset_id}.json")
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False)

    scope = out["agg"].get("province") or out["agg"].get("region") or ""
    label = args.label or f"{args.country} \u00b7 {scope} ({out['agg'].get('portal','')})".strip()
    entry = {"id": args.dataset_id, "country": args.country,
             "region": out["agg"].get("region"), "label": label,
             "file": os.path.basename(out_path), "default": bool(args.default)}
    mpath = upsert_manifest(args.data_dir, entry)
    print(f"Wrote {out_path}: {len(out['rows'])} offices, "
          f"{out['agg']['funnel']['prime']} prime targets.")
    print(f"Updated {mpath}: dataset '{args.dataset_id}' -> {label}")


if __name__ == "__main__":
    main()
