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
- **Switch to BigQuery:** implement `load_from_bigquery()` in the script
  (project `jamesedition-152413`), keep the output shape identical.
- **Add a gate widget:** populate the field in `generate_data.py` → add a panel
  + `bar()/donut()` in the relevant tab → wire `onClick` → `openPanel`.

## Guardrails

- Preserve the JSON contract; if you must change a field the UI reads, grep the
  field name in `index.html` and update every use.
- Don't commit `raw/` or any `*.xlsx` (see `.gitignore`).
- The repo may be public — never hardcode credentials, tokens, or BigQuery
  service-account keys. Use env/CI secrets.
- Verify numbers against the source after any data change (the funnel/KPIs must
  reconcile: total ≥ qualified ≥ qualifiedNotJE ≥ prime).
