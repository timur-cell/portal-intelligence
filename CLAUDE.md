# CLAUDE.md — Portal Intelligence

Context for Claude Code working in this repo. Read this first.

## What this is

A static, single-file market-intelligence dashboard for JamesEdition. It scores
real-estate agencies scraped from competitor portals through qualification
**gates** and surfaces acquisition targets + supply coverage. See `HANDOVER.md`
for the full business context and roadmap; `README.md` for run/deploy.

## Architecture (deliberately minimal)

- **`index.html`** — the entire app. Vanilla JS + [Chart.js](https://www.chartjs.org/)
  from CDN. **No framework, no build step, no package.json.** Edit and refresh.
- **`es-malaga.json`** — the only data input, shape `{ agg, rows }`. The UI is
  pure presentation over this file.
- **`generate_data.py`** — builds `es-malaga.json` from the source
  export (Excel today, BigQuery next). Pandas + openpyxl.

Keep this stack. Do **not** introduce React/Vue/a bundler/node_modules unless
explicitly asked — the value is that anyone can open one file and that Pages
serves it with zero build.

## Data contract (don't break it)

**Multi-dataset:** `datasets.json` is a manifest of available regions; each
entry points to a dataset file (e.g. `es-malaga.json`). The header's Dataset
switcher loads one at a time. Every dataset file has the same shape:

`<dataset-id>.json`:
- `agg` — precomputed headline numbers (see `HANDOVER.md` §3 for every field).
- `rows[]` — one office each. Key fields and encodings:
  - `g1` Gate 1 ICP: `1` Premier, `2` Qualified, `3` Needs Review, `4` Excluded (`icp` is the label).
  - `g2` Gate 2: `1` on JamesEdition, `0` not.
  - `g3` Gate 3: integer count of listings ≥ €1M (nullable).
  - `g4` overlap score 0–1 (nullable); `tier`, `model`, `buyers`, `est`
    (estimated total listings, nullable), `portal` (1 = aggregator), `region`, `province`, `city`.

Derived definitions used throughout the JS — keep them consistent:
- `isQual = g1 ∈ {1,2}` · `isLux = g3 >= 1` · `notJE = g2 === 0`
- **prime target** = `isQual && notJE && isLux`.

When adding a metric, prefer computing it client-side from `rows` (see
`compute()` in `index.html`) so it respects the active filters; only add to
`agg` if it's genuinely global.

## Front-end conventions

- **Filters** live in one bar and set the `state` object; `filtered()` applies
  them; `renderAll()` re-renders the active tab. Region → Province cascade via
  `buildProv()`.
- **Drill-down** is the core UX: `openPanel(title, eyebrow, predicate, context)`
  opens the side panel listing `filtered().filter(predicate)`. Make any new
  chart drillable by giving it an `onClick` that calls `openPanel` with a row
  predicate matching the clicked segment.
- **Charts** go through the `donut()` / `bar()` helpers (consistent styling +
  click handling). Reuse them rather than instantiating Chart.js directly.
- **Design tokens** (JamesEdition): body `#151515`, secondary `#606060`, teal
  `#006C75`, gold `#b9a16f`; fonts Inter (UI) + Prata (H1/H2 serif). Restrained,
  editorial. Teal/gold are accents — sparingly.
- "Coming soon" cards mark dimensions awaiting data — flip them to live widgets
  (mirror a Gate 3 chart) once the data lands.

## Common tasks

- **Refresh / add a region:** `python3 generate_data.py --input raw/<export>.xlsx --dataset-id <slug> --country <C> --label "<label>"` (writes `data/<slug>.json` and updates `datasets.json`; new regions appear in the switcher with no front-end change).
- **Switch to BigQuery:** `load_from_bigquery()` is already scaffolded (parameterized
  loader + `BQ_OFFICE_SQL` placeholders + `BQ_COLUMN_MAP`); just fill the table names.
  Project `jamesedition-152413`. Keep the output shape identical. See the
  **Live data: BigQuery access** section below for verified tables/gotchas.
- **Add a gate widget:** populate the field in `generate_data.py` → add a panel
  + `bar()/donut()` in the relevant tab → wire `onClick` → `openPanel`.

## Live data: BigQuery access (verified 2026-06)

JE's warehouse is reachable **in-session via MCP tools** — no service-account key
needed, and **never paste/commit one** (repo may be public). Tools:
`Bigquery_Query_Database` (query string only) and `Bigquery_Schema_Check`
(`datasetId`, `tableName`). ⚠️ `INFORMATION_SCHEMA` is **blocked** — you can't
enumerate tables, you must already know the names.

**JE platform tables (Postgres mirror, `pg_` prefix):**
- `data_marts.pg_offices` — JE offices. Cols incl. `office_id, name, city,
  country_code, country_subdivision, listings_count, agents_count,
  business_group1..4_id` (networks), `mls, external_url, path, vat_id, email,
  office_deleted_at`.
- `data_marts.pg_listings` — JE listings. Cols incl. `listing_id, office_id,
  price_cents, price_cents_usd, currency, country_code, country_subdivision,
  canonic_country_subdivision_id, canonic_city_id, active, state, type, rental,
  listing_created_at, listing_deleted_at, available_for_jamesedition, listing_score`.
- Scale: JE Spain ≈ **4,093 offices / 525k listings** (US ~100k offices, FR 12.7k, IT 6.8k).

**Gotchas when querying:**
- **€1M luxury**: no native EUR price column. Quick proxy used so far:
  `price_cents_usd >= 108000000` (~$1.08M ≈ €1M). For precision, convert FX or
  filter `currency='EUR' AND price_cents>=100000000`.
- **Geo is messy free-text**: `country_subdivision` for Málaga shows as
  `MALAGA/Malaga/Málaga/MA/M`, Andalucía as `AN/Andalusia`. **Join on the
  canonical integer keys** `canonic_country_subdivision_id`/`canonic_city_id`,
  not the strings. (Geo dimension table mapping id→name still TBD.)
- Always filter `*_deleted_at IS NULL` and (for supply) `active=TRUE`, `rental=FALSE`.

**Still needed from the team to finish `load_from_bigquery()`** (placeholders in
`generate_data.py`: `OFFICES_TABLE`, `LISTINGS_TABLE`, `JE_OFFICE_MATCH_TABLE`):
1. Scraped **competitor** offices/listings `dataset.table` names (Idealista etc.).
2. Where the **ICP gate enrichment** (`g1, tier, buyers, model, franchise, years`)
   lives — a BigQuery table or an external/Excel step?
3. **Geo dimension** table (canonic ids → names).
4. **Office-match key** competitor↔JE (domain? `external_url`/`vat_id`/`name`?).

## Dashboard structure (post-2026-06 build)

Three tabs (see `index.html`): **`market`** (Competitive Position — *default*),
`agency`, `listings`. Rationale + sources in `RESEARCH.md`.
- **Acquisition Priority Score** — `priorityScore(r)` (Fit+Value+Winnability+Signals,
  0–100), `PTIERS` (single source of truth for thresholds **65/45/25** + bar colors),
  `pTier`/`pBadge`. `decorate(ROWS)` runs once in `loadDataset` and sets
  `r.score`/`r.ptier` (compute-once, not per render).
- Helpers added: `hhi(vals)`, `countBy(arr,key)`, `luxCore=r=>isLuxTier(r)&&!r.portal`.
- `renderMarket(rows,c)` + `renderPriority(rows)`. **Coverage is measured on
  `tier`** (luxury/ultra) because **`g3` is null for all on-JE offices** in the
  current snapshot — do NOT compute €1M+ supply-share from `g3` (reads 0%). Exact
  supply-share waits on BigQuery per-listing prices.

## Deploy

Live at **https://timur-cell.github.io/portal-intelligence/**. Workflow
`.github/workflows/deploy-pages.yml` deploys on push to `main`. The auto-created
`github-pages` environment **only allows deploys from the default branch (`main`)**
— branch deploys fail instantly (no runner/logs); merge to `main` to publish.

## Guardrails

- Preserve the JSON contract; if you must change a field the UI reads, grep the
  field name in `index.html` and update every use.
- Don't commit `raw/` or any `*.xlsx` (see `.gitignore`).
- The repo may be public — never hardcode credentials, tokens, or BigQuery
  service-account keys. Use env/CI secrets.
- Verify numbers against the source after any data change (the funnel/KPIs must
  reconcile: total ≥ qualified ≥ qualifiedNotJE ≥ prime).
