# Portal Intelligence

A market-intelligence dashboard for JamesEdition Sales & Supply. It scores
real-estate agencies scraped from competitor portals (Idealista today) against
three qualification **gates** and surfaces the best acquisition targets, plus a
listings-supply coverage view.

> **Status:** demo prototype, built for an All Hands. Front-end is complete and
> data-driven; the data layer is a one-off scraped export and is being moved to
> BigQuery. See [`HANDOVER.md`](./HANDOVER.md) for the full picture and roadmap.

![scope](https://img.shields.io/badge/scope-Andaluc%C3%ADa%20%C2%B7%20M%C3%A1laga-006C75)
![status](https://img.shields.io/badge/status-demo%20prototype-b9a16f)

---

## What it does

Three tabs, one shared filter bar:

- **Competitive Position** — the executive CI view: luxury **supply coverage**
  (our share vs. the portal leader), **white-space** by town, **supply
  concentration** (HHI / top-10 share), and the luxury differentiators —
  international **buyer reach** and **tier-1 network vs. independent**.
- **Agency Intelligence** — acquisition funnel (Gate 1 → 2 → 3), an
  **Acquisition Priority Score** (0–100, ranked P1/P2/P3 queue), ICP
  qualification, JamesEdition presence/penetration, and luxury qualification.
- **Listings Intelligence** — estimated supply by luxury segment, addressable
  volume and coverage gap by province, and inventory concentration by office.

Every chart, KPI, and funnel stage is **clickable** — it opens a side panel
listing the underlying agencies (with priority score, search, sort, and CSV
export). The design rationale and sources are in [`RESEARCH.md`](./RESEARCH.md).

### Acquisition Priority Score

A transparent, additive 0–100 score computed client-side per office:
**Fit** (ICP gate) + **Luxury value** (€1M+ depth, or tier proxy) +
**Winnability** (not-yet-on-JE, inventory overlap) + **prestige Signals**
(tier-1 network, tenure, international-HNWI focus). Tiered **P1 ≥ 65 · P2 ≥ 45 ·
P3 ≥ 25**. It respects the active filters and exports with the CSV.

### The three gates

| Gate | Meaning | Source field |
|------|---------|--------------|
| **Gate 1 — ICP Qualification** | `1` Premier · `2` Qualified · `3` Needs Review · `4` Excluded | `Gate 1: ICP Qualification` |
| **Gate 2 — JE Presence** | `1` already on JamesEdition · `0` not on JE | `Gate 2: JE Duplicate` |
| **Gate 3 — Luxury** | count of listings priced ≥ €1M | `Gate 3: # Listings ≥ 1M€` |

Gate 4 (overlap) and **Gate 5 (network/MLS — now live**, feeding the priority
score and the Network view) are populated; Gates 6–7 (scraping qualification,
website listing estimate) are stubbed in the UI as "coming soon".

---

## Run it locally

The dashboard fetches JSON from `data/` (a `datasets.json` manifest plus one
file per region), so it must be served over HTTP (opening `index.html` directly
via `file://` is blocked by browsers).

```bash
git clone git@github.com:timur-cell/portal-intelligence.git
cd portal-intelligence
python3 -m http.server 8080
# open http://localhost:8080
```

## Regenerate the data

```bash
pip install pandas openpyxl
# place the scraped export at raw/offices_malaga.xlsx (gitignored)
python3 generate_data.py --input raw/offices_malaga.xlsx \
  --dataset-id es-malaga --country Spain --label "Spain · Málaga (Idealista)" --default
```

The front-end only depends on the JSON **shape** (`{ agg, rows }`), so the
source can change (Excel → BigQuery) without touching `index.html`.

### Add another region or country

Each region is one dataset file plus an entry in `datasets.json`. Generate
it and it appears in the **Dataset switcher** in the header automatically:

```bash
python3 generate_data.py --input raw/madrid.xlsx \
  --dataset-id es-madrid --country Spain --label "Spain · Madrid (Idealista)"
```

No front-end changes needed — drop in the file, the switcher picks it up.

## Deploy (GitHub Pages)

A workflow at `.github/workflows/deploy-pages.yml` publishes the repo root on
every push to `main`. One-time: **Settings → Pages → Source = GitHub Actions**.

---

## Repo layout

```
portal-intelligence/
├── index.html                     # the dashboard (Chart.js, vanilla JS, no build step)
├── data/
│   ├── datasets.json              # manifest of available datasets (drives the switcher)
│   └── es-malaga.json             # one file per region/country, shape { agg, rows }
├── generate_data.py       # builds a dataset JSON + updates the manifest
├── .github/workflows/deploy-pages.yml
├── README.md
├── HANDOVER.md                    # context + roadmap for the next engineer
├── CLAUDE.md                      # context file for Claude Code
└── .gitignore                     # excludes raw/ scraped data
```

## Tech

No framework, no build step. Single `index.html` using
[Chart.js](https://www.chartjs.org/) from CDN and the JamesEdition design
tokens (Inter / Prata, teal + gold). Data is plain JSON.
