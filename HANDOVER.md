# Handover — Portal Intelligence

**To:** Scraping / Data Engineer
**From:** Timur (Product / Market Intelligence)
**Purpose:** take this demo dashboard from a one-off scraped snapshot to a
maintained, company-wide market-intelligence tool fed by live data.

---

## 1. TL;DR

We scrape agencies and their listings from competitor portals (Idealista first,
others next), score each office through qualification **gates**, and use that to
(a) find acquisition targets for Sales and (b) measure supply coverage gaps.

The **front-end is done** and fully data-driven. Your job is the **data layer**:
move it off the static Excel export onto BigQuery, complete gates 4–7, and add
real per-listing detail. The dashboard reads dataset files from `data/` (one per region, listed in
`datasets.json`) — nothing in the UI changes as long as that shape holds.

---

## 2. Current state (what works today)

- **Source:** a single scraped Excel export of **2,288 Idealista offices** in
  **Málaga province** (39 columns). Not committed — keep it under `raw/`.
- **Gates 1–3 are fully populated and drive the whole dashboard.** Gate 4
  (overlap) is partially populated; gates 5–7 are placeholders.
- **Headline numbers (current snapshot):**
  - 2,288 offices → **582 qualified** (Gate 1: 45 Premier, 537 Qualified)
  - **17.5%** JE penetration (401 on JE, 1,887 not)
  - **986** offices carry ≥1 listing at €1M+, **7,841** luxury listings total
  - **287 prime targets** = qualified · not on JE · luxury
- **Listings figures are agency-level *estimates*** (`ICP Estimated Listings`),
  not per-listing rows. Totals are skewed by portal aggregators (e.g. one office
  estimated at 40k listings), so the dashboard shows both the raw total
  (575,083) and a portal-excluded "core" figure (320,577), and labels them as
  estimates.

## 3. Data model — the JSON the dashboard consumes

`generate_data.py` emits one dataset file per region (e.g.
`es-malaga.json`) plus a `datasets.json` manifest that the header's
**Dataset switcher** reads. Each dataset file is shaped as:

```jsonc
{
  "agg": {                      // precomputed headline aggregates
    "total": 2288,
    "region": "Andalucía", "province": "Málaga", "portal": "Idealista",
    "estTotal": 575083, "estCore": 320577, "estMedian": 30,
    "luxListings": 7841,
    "gate4": { "withOverlap": 191, "avg": 0.23 },
    "funnel": { "total": 2288, "qualified": 582, "qualifiedNotJE": 375, "prime": 287 }
  },
  "rows": [                     // one object per office
    {
      "name": "...", "url": "...", "city": "Marbella",
      "region": "Andalucia", "province": "Málaga",
      "g1": 1,                  // Gate 1: 1 Premier 2 Qualified 3 Needs Review 4 Excluded
      "icp": "Premier",         // label form of g1
      "g2": 0,                  // Gate 2: 1 on JE, 0 not on JE
      "g3": 45,                 // Gate 3: # listings >= 1M EUR
      "g4": 0.02,               // Gate 4: overlap score 0..1 (nullable)
      "tier": "ultra_luxury",   // ICP luxury tier
      "model": "resale_agency", // ICP business model
      "franchise": 0, "buyers": "international_hnwi",
      "est": 60,                // estimated total listings (nullable)
      "portal": 0,              // 1 if model is a portal/aggregator
      "years": "..."
    }
  ]
}
```

**Contract:** keep this shape. If you add fields, the UI ignores unknown keys —
safe. If you rename or drop a field the charts use, update `index.html`
accordingly (search the field name; it's a single file).

## 4. Your roadmap (priority order)

1. **Connect BigQuery (highest value).**
   - `load_from_bigquery()` in `generate_data.py` is now a **working,
     parameterized loader** (auth via ADC/env, no keys) + a SQL skeleton
     (`BQ_OFFICE_SQL`). **Your only job:** replace the three `*_TABLE`
     placeholders (`OFFICES_TABLE`, `LISTINGS_TABLE`, `JE_OFFICE_MATCH_TABLE`)
     with the real tables, then run `python3 generate_data.py --source bigquery
     --bq-dataset <ds> --portal Idealista`. Output columns already match what
     the dashboard consumes (verified against `BQ_COLUMN_MAP`).
   - Pull **JE's own live listing volume** per province/segment. This is the
     missing half of the **coverage-gap** widget — right now the competitor bar
     is real and the JE bar is `0` / "pending BQ". With JE volume you get an
     exact **missing-listings-by-province** count.
   - Pull **per-listing detail** (price, property type, location, status). This
     unlocks the four "Needs BigQuery" cards on the Listings tab: price-range
     distribution, property-type split, missing-listings-by-province, and
     freshness/churn.

2. **Complete gates 4–7.**
   - Gate 4 — finish listing-overlap scoring across all offices.
   - Gate 5 — network/MLS detection (de-dupe franchises; target head offices).
   - Gate 6 — scraping qualification (can we scrape the office's own site).
   - Gate 7 — estimated true website listing count.
   - Each is already a column concept; populate it, then flip the UI card from
     "coming soon" to a live widget (mirror an existing Gate 3 chart).

3. **Scale the geography & sources.**
   - Same pipeline across all of Andalucía → Spain → every JE market. The geo
     filters (Region → Province) are already built to scale; today the data is
     Málaga-only.
   - Add Kyero and other portals; **de-duplicate offices across sources**
     (domain match is the obvious key — `Domain` exists in the raw export).

4. **Automate & operationalize.**
   - Schedule `generate_data.py` (e.g. in `je-airflow`) so each dataset file
     refreshes on a cadence; Pages redeploys on push.
   - Push prime targets into HubSpot with owner assignment + contact enrichment.
   - Weekly "new luxury offices" alert for Sales.

## 5. Front-end notes

- Single `index.html`, **no build step**. Chart.js from CDN, vanilla JS, JE
  design tokens inline. Edit and refresh.
- The side panel (`openPanel(title, eyebrow, predicate, context)`) is the
  drill-down: any click builds a predicate over the filtered rows. To make a new
  chart drillable, pass an `onClick` that calls `openPanel` with a row predicate.
- Performance: ~2.3k rows is trivial client-side. At ~50k+ rows, consider
  paginating/virtualizing the side-panel list (already capped at 300 rendered)
  and precomputing more in `agg`.

## 6. ⚠️ Before you rely on this publicly

- **The repo is currently Public.** `es-malaga.json` contains competitor agency
  names, our ICP scores, and JE-penetration data. **Recommend making the repo
  Private** (Settings → General → Danger Zone → Change visibility) before adding
  more data or enabling Pages, and confirm with whoever owns data governance.
- Even private, scraped competitor data has legal/ToS considerations — worth a
  quick check with the team before broad distribution.

## 7. Quick start for you

```bash
git clone git@github.com:timur-cell/portal-intelligence.git
cd portal-intelligence
python3 -m http.server 8080          # open http://localhost:8080
# to use Claude Code on it:
claude                                # CLAUDE.md gives it full project context
```

## 8. Adding a new region or country (multi-dataset)

The dashboard is built to scale across geographies. Each region/country is a
**self-contained dataset file** in `data/`, registered in `datasets.json`:

```jsonc
{ "datasets": [
  { "id": "es-malaga", "country": "Spain", "region": "Andalucía",
    "label": "Spain · Málaga (Idealista)", "file": "es-malaga.json", "default": true }
]}
```

To add one:

```bash
python3 generate_data.py --input raw/madrid.xlsx \
  --dataset-id es-madrid --country Spain --label "Spain · Madrid (Idealista)"
```

That writes `es-madrid.json` and adds it to the manifest. The header's
**Dataset switcher** picks it up automatically — no front-end edits. Within a
dataset, the Region → Province filters still apply, so a dataset can be a single
province (today) or a whole country once you have the volume.

Design choices when you scale:
- **Granularity:** one file per province keeps payloads small and switching fast;
  one file per country is simpler to manage. Pick per data volume.
- **De-dupe across portals** before generating (domain match) so the same office
  from Idealista + Kyero is one row.
- When a single file gets large (~50k+ offices), precompute more in `agg` and
  keep the side-panel render cap (already 300).

Questions → Timur.
