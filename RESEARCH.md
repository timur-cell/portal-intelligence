# Competitive / Market-Intelligence Dashboard — Research & Design

**For:** JamesEdition "Portal Intelligence"
**Question:** What should a best-in-class classified / competition-intelligence dashboard track for an *international luxury* (>€1M) real-estate platform competing with local mass-market leaders (Idealista · ES, Immobiliare.it · IT, SeLoger · FR)?
**Method:** Deep-research harness — 5 parallel search angles → source fetch → adversarial verification → synthesis, then mapped against the *actually computable* fields in `es-malaga.json`.
**Date:** 2026-06-07

> **TL;DR for this repo.** The biggest gaps in v1 are: (1) no **competitive market-share / supply-coverage** view (the headline ask), (2) the prime-target list isn't **ranked** into a sales queue, and (3) three well-populated fields (`franchise`, `years`, `model`) are unused. The build that ships alongside this doc adds a **Competitive Position** tab, an **Acquisition Priority Score**, and activates those fields — all computed client-side from the rows we already scrape, with anything that genuinely needs per-listing data left as explicit BigQuery roadmap.

---

## 1. The hard constraint: what is and isn't knowable from scraping

The single most important adversarial finding across angles 1 & 2: **the metrics portals brag about are mostly *not* externally computable.** Traffic, leads/enquiries, paying-agency counts, retention and ARPA are all *internal* data — Rightmove's "90%+ retention" and Realtor.com's "31% market share" are self-reported and unauditable ([Rightmove FY2025](https://propertyindustryeye.com/eye-newsflash-rightmove-post-strong-full-year-results/), [Realtor.com claim](https://www.realestatenews.com/2026/05/11/realtor-com-has-nearly-a-third-of-the-market-ceo-says)). A scraping-fed dashboard should therefore lean on what **is** verifiable from agency/office rows:

| Computable from our rows today | Needs per-listing / internal data (roadmap) |
|---|---|
| Listing/supply **share by geography** | Exact €1M+ supply share on JE (per-listing match) |
| **Supply concentration** (HHI, CR-N) | Days-on-market, price reductions, freshness/churn |
| Coverage **white-space** (offices off-platform) | Leads, views, traffic, conversion |
| Agency **league tables / ranking** | Take rate, GMV retention, supplier CAC |
| Network vs independent, tenure, buyer reach | Time-to-first-transaction |

Sources: [a16z – 13 Metrics for Marketplaces](https://a16z.com/13-metrics-for-marketplace-companies/), [a16z – Marketplace Glossary](https://a16z.com/the-marketplace-glossary/), [Casafari competitor monitoring](https://www.casafari.com/insights/how-monitor-competitors-real-estate-casafari/), [PropertyData agent rankings](https://propertydata.co.uk/agents).

### ⚠️ Data caveat we verified and corrected
`g3` (count of ≥€1M listings) is **null for all 401 on-JE offices** — only off-JE offices were scored for luxury depth. A naive "share of €1M+ listings on JE" widget would falsely read **0%**. The shipped dashboard therefore measures coverage on **`tier`** (luxury/ultra-luxury, populated on *both* sides → **34.5%** office coverage) and marks exact €1M+ supply-share as BigQuery-pending, consistent with the existing coverage-gap note.

---

## 2. What leading real-estate intelligence tools actually surface

Angle 4 confirmed the pattern to copy — **agency league tables + area-level supply share + cross-portal de-duplication**:

- **Casafari** (310M listings, 20+ countries): ranks agents by **listing count per area**, alerts when a **competitor gains listings** in your area, ML **de-dupes** the same property across portals ([product](https://www.casafari.com/products/improved-property-search/), [data integration](https://www.casafari.com/insights/casafari-innovative-data-integration-solutions/)).
- **PropertyData.co.uk**: normalises agent names across portals and **ranks agents by live listing count**; compares competitor volume by area ([agents](https://propertydata.co.uk/agents)).
- **CoStar**: quarterly **agency league tables**, absorption & months-on-market dashboards ([league tables](https://costar.co.uk/q3-2022-investment-agents-league-tables), [market analytics](https://www.costar.com/products/market-analytics)).
- **HouseSigma**: tracks **new vs removed/relisted** inventory and a **buyer-competition score** ([listing history](https://www.homesfound.ca/blog/beyond-price-tag-what-housesigmas-listing-history-reveals-about-property/)).
- **AirDNA**: colour-coded **investability scores** per submarket ([submarket insight](https://www.airdna.co/submarket-insight)).

**De-duplication across portals is table stakes** (Casafari, Reonomy IDs) — directly relevant to the roadmap item of merging Idealista + Kyero offices by domain.

---

## 3. Marketplace KPIs worth porting (supply-side)

Angle 2 (a16z, Gurley, NfX, Lenny, Sequoia):

- **Supply concentration — HHI** = Σ(shareᵢ×100)². <1,000 competitive · 1,000–1,800 moderate · >1,800 concentrated ([DOJ](https://www.justice.gov/atr/herfindahl-hirschman-index), [CFI](https://corporatefinanceinstitute.com/resources/valuation/herfindahl-hirschman-index-hhi/)). **Our Málaga luxury supply: HHI ≈ 243, CR10 ≈ 45%** → *highly fragmented*, which argues for a **broad** acquisition motion (no single agency to "win"), and makes coverage % the right north star.
- **Share of supply vs competitors** is a *leading* indicator of market share ([Brandwatch SOV](https://www.brandwatch.com/blog/share-of-voice/), [Sequoia](https://articles.sequoiacap.com/two-sided-marketplaces-and-engagement)).
- **Geographic coverage / white-space** — fill the gaps before competitors ([NfX expansion](https://www.nfx.com/post/marketplace-expansion-framework), [Lenny – how marketplaces win](https://www.lennysnewsletter.com/p/how-marketplaces-win-benjamin-lauzier)).
- **GMV/supply retention, churn, TTFT, liquidity/fill-rate** — all high-value but **need transaction/time-series data** → roadmap, not v1.

---

## 4. How luxury differs from mass-market (the niche thesis)

Angle 3 (Knight Frank, Savills, Christie's, Sotheby's, JamesEdition):

1. **€1M is not "luxury" everywhere.** It is entry-level on the Costa del Sol but ultra-prime inland; prime is better cut by **€/m² and price bands (€1–2M / €2–5M / €5M+)** ([Knight Frank PIRI](https://www.knightfrank.com/research/article/2026/4/piri-100-ultimate-prime-residential-property-index), [Idealista beachfront](https://www.idealista.com/en/news/luxury-real-estate-in-spain/2026/04/27/889338-spain-s-beachfront-renaissance-from-eu500-000-to-eu1-million-and-beyond)). → use `tier` as the band proxy until per-listing prices land.
2. **~60% of Spanish luxury demand is international**; Idealista's audience is ~88% domestic ([Idealista](https://www.idealista.com/en/news/luxury-real-estate-in-spain/2026/05/25/889418-the-simple-rent-60-of-demand-for-spain-s-luxury-homes-comes-from-foreign-)). → **buyer-reach** (`buyers`: international_hnwi/expat/local) is a first-class luxury metric, not a footnote.
3. **Luxury supply concentrates in tier-1 networks** — Sotheby's, Christie's, Engel & Völkers, Knight Frank ([brands](https://ardorseo.com/blog/top-10-luxury-real-estate-brands/)). → the unused **`franchise`/network** flag is a prestige/credibility signal worth scoring and surfacing.
4. **Off-market / "whisper" listings** are 15–20% of $3M+ deals and invisible to mass portals ([Luxury Presence](https://www.luxurypresence.com/blogs/off-market-listings/)) → a structural reason curation > volume; flagged as a future gate.
5. Luxury wins on **curation, verification, international syndication and prestige tiering**, not inventory size ([keycrew](https://keycrew.co/journal/luxury-real-estate-platforms-gain-edge-by-curating-not-expanding-inventory/)).

---

## 5. Dashboard & scoring design principles applied

Angle 5 (Crayon/Klue, Gartner/Forrester, HubSpot/ZoomInfo, Geckoboard):

- **One North Star + 4–6 diagnostics**, trends over snapshots, 5–7 KPIs/view, benchmark-vs-actual ([ClearPoint](https://www.clearpointstrategy.com/blog/kpi-dashboard-best-practices), [UXCam NSM](https://uxcam.com/blog/north-star-metric-framework/), [Geckoboard](https://www.geckoboard.com/blog/dashboard-design-what-makes-an-effective-kpi-dashboard/)). → **North Star = Luxury Supply Coverage %.**
- **Score fit first, then value/winnability; keep it simple** — complex models kill rep adoption; weighted additive across 4–6 categories, tier into **P1/P2/P3** ([Pedowitz fit vs intent](https://www.pedowitzgroup.com/how-do-you-balance-fit-vs.-intent-in-scoring), [Digital Applied ICP framework](https://www.digitalapplied.com/blog/b2b-icp-scoring-framework-2026-lead-qualification-playbook), [HubSpot](https://blog.hubspot.com/sales/lead-scoring-tactics-hubspot-uses)).
- **Prioritised target lists** with owner + "why this account" enrichment ([Demandbase](https://www.demandbase.com/blog/account-prioritization-for-business-quarter/), [Gradient.works](https://www.gradient.works/resources/b2b-account-prioritization)). → the Priority queue + CSV export feeds straight into the HubSpot roadmap item.

---

## 6. What shipped in this iteration (all client-side, contract preserved)

1. **New "Competitive Position" tab** (executive CI view, set as default):
   - North Star **Luxury Supply Coverage %** + diagnostics (open white-space, HHI concentration, prime targets).
   - **Coverage** donut (luxury-tier offices On JE vs Open) and **white-space by city** bar.
   - **Supply concentration** (top-office share + HHI readout with interpretation band).
   - **Buyer reach** (international/expat/local) and **network vs independent** — the luxury differentiators.
2. **Acquisition Priority Score** on the Agency tab — transparent additive model (Fit + Luxury value + Winnability + prestige Signals), tiered **P1/P2/P3**, with a ranked top-targets list. Score + network + tenure now show on every side-panel row, are sortable, and export to CSV.
3. **Activated unused fields:** `franchise` (network detection — Gate 5 card is now live), `years` (tenure signal), `model` (business-model mix).

### Deliberately left as roadmap (need BigQuery / per-listing / time-series)
Exact €1M+ supply-share & missing-listings, price-band split (€1–2M/2–5M/5M+), days-on-market, price reductions, listing freshness/churn, leads/traffic, GMV retention, cross-portal de-dup, off-market detection.

---

*Every metric above was checked against the data shape in `es-malaga.json`; figures (HHI 243, CR10 45%, 34.5% coverage, 286 prime targets) are reproducible from the current snapshot. Sources are linked inline for verification.*
