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

The **Refresh latest** button in the dashboard fetches live Brent and WTI quotes
client-side (via public CORS proxies) and recalculates every chart and panel:
KPI tiles, risk score, factor weights, the price/Brent history chart, the
feedstock heatmap, and the 8-week projection with its scenario table.

Two things it does **not** do:

- Polymerupdate headlines are a published snapshot. Their price tables are
  behind a login, so the wire updates when you edit `index.html` and redeploy.
- Producer circular prices (Reliance, IOCL, OPaL, HMEL, GAIL) are point-in-time
  values that need manual confirmation against your DCA circular.

To refresh the underlying snapshot data, edit the `state` object near the bottom
of `index.html` (`grades`, `histPP`, `histBrent`, `baselines`, `polymerupdate`),
commit, and push. Pages redeploys and the same URL serves the new version.

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
