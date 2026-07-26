# PP Woven Bag — Polymer Market Dashboard

A single-file, self-contained dashboard for PP woven bag procurement in India
(West/Gujarat focus). Tracks raffia-grade PP, PE, BOPP film, crude/naphtha/propylene
feedstock, a Polymerupdate news wire, and an 8-week crude-linked price projection
with a Buy/Hold/Wait call and risk score.

Everything lives in [`index.html`](index.html) — no build step, no dependencies to
install. Chart.js loads from a CDN at runtime.

## Viewing locally

Open `index.html` in a browser, or serve it:

```bash
python3 -m http.server 8000
# then visit http://localhost:8000
```

## Deploying to GitHub Pages

The workflow in `.github/workflows/deploy.yml` publishes the repository root on
every push to `main`.

1. Push this repository to GitHub.
2. Go to **Settings → Pages** and set **Source** to **GitHub Actions**.
3. Push a commit. The site redeploys in about a minute at a stable URL.

### Plan requirements

Publishing Pages from a **private** repository requires a paid plan (Pro, Team,
or Enterprise). On the Free plan, Pages only works from public repositories.

### Site visibility

A private repository does **not** make the published site private. On Pro and
Team plans the Pages site is publicly reachable by anyone who has the URL.
Restricting site access to repository members requires GitHub Enterprise Cloud
(**Settings → Pages → Visibility → Private**).

If you need password-based sharing with people who do not have GitHub accounts,
use the htmldrop fallback below.

## Refresh behaviour

Two layers keep the GitHub Pages site current:

1. **Daily GitHub Action** (`.github/workflows/daily-refresh.yml`) runs every day at
   **00:30 UTC (~06:00 IST)**. It updates [`data/market.json`](data/market.json)
   with live Brent/WTI, recalculated naphtha/propylene/India-basket estimates,
   and an updated H030SG path, then commits. The existing Pages deploy workflow
   republishes automatically so the **same URL** serves the new snapshot.

2. **Refresh latest button** (and auto-run on page open) reloads `data/market.json`
   and overlays live crude quotes, then recalculates every chart and panel:
   KPI tiles, risk score, factor weights, history chart, feedstock heatmap, and
   the 8-week projection.

Manual trigger: **Actions → Daily market refresh → Run workflow**.

Local test:

```bash
python3 scripts/update_market_daily.py
```

Polymerupdate headlines remain a curated snapshot inside `data/market.json`
(their price tables are login-gated). Update those fields in the JSON when you
want new headlines, then push.

## htmldrop fallback (password-gated link)

For sharing with people who should not need a GitHub account:

```bash
python3 scripts/publish_htmldrop.py
```

This returns an unlisted, password-protected URL. Note that each run mints a
**new** random subdomain, so the link changes on every republish.

Credentials are written to `publish/access.json` and `publish/owner.key`, both of
which are gitignored and must never be committed.

## Data sources

Polymerupdate · Plastic4trade · Plastemart producer circulars · Trading Economics ·
ET Energyworld · ChemOrbis · Yahoo Finance (live refresh).

Figures are indicative. Confirm against producer or DCA circulars before booking.
The projection is a heuristic model, not a price guarantee.
