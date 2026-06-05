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


def load_from_bigquery() -> pd.DataFrame:
    """PRODUCTION TODO.
    Replace with a query against the offices table once BigQuery is connected,
    returning the same columns this script expects (see Gate mapping above).
    Example:
        from google.cloud import bigquery
        client = bigquery.Client(project="jamesedition-152413")
        return client.query(SQL).to_dataframe()
    """
    raise NotImplementedError("Wire up BigQuery here — see HANDOVER.md.")


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
    args = ap.parse_args()

    df = load_from_bigquery() if args.source == "bigquery" else load_from_excel(args.input)
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
