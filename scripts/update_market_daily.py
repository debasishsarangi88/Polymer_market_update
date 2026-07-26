#!/usr/bin/env python3
"""Daily market snapshot updater for GitHub Pages.

Fetches live Brent / WTI from Yahoo Finance, recalculates linked feedstock and
H030SG estimates, appends today's history point, and writes data/market.json.
Designed to run in GitHub Actions on a daily cron so the Pages site always
serves a fresh snapshot. The in-page Refresh button can still overlay live
quotes on top of this file.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MARKET_FILE = ROOT / "data" / "market.json"
UA = "PP-Woven-Bag-Dashboard/1.0 (+https://github.com/; daily refresh)"


def fetch_yahoo(symbol: str) -> tuple[float, list[float]]:
    url = (
        "https://query1.finance.yahoo.com/v8/finance/chart/"
        f"{symbol}?interval=1d&range=1mo"
    )
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=45) as resp:
        payload = json.loads(resp.read().decode())
    result = payload["chart"]["result"][0]
    meta = result["meta"]
    closes = [c for c in result["indicators"]["quote"][0]["close"] if c is not None]
    price = float(meta.get("regularMarketPrice") or closes[-1])
    return price, closes


def month_pct(closes: list[float], fallback: float) -> float:
    if len(closes) < 2 or not closes[0]:
        return fallback
    return round((closes[-1] / closes[0] - 1) * 100, 1)


def today_label(now: datetime) -> str:
    return f"{now.day} {now.strftime('%b %Y')}"


def apply_updates(market: dict, brent: float, wti: float, brent_closes: list[float], wti_closes: list[float]) -> dict:
    now = datetime.now(timezone.utc)
    label = today_label(now)
    baselines = market.setdefault(
        "baselines",
        {
            "h030sg": market.get("h030sg", 139.53),
            "brent": market.get("brent", 97.08),
            "naphtha": market.get("naphtha", 810.35),
            "propylene": market.get("propylene", 1010),
            "indiaBasket": market.get("indiaBasket", 103.33),
        },
    )

    market["brent"] = round(brent, 2)
    market["wti"] = round(wti, 2)
    market["naphtha"] = round(
        baselines["naphtha"] * (1 + (brent / baselines["brent"] - 1) * 0.85), 2
    )
    market["propylene"] = round(
        baselines["propylene"] * (1 + (brent / baselines["brent"] - 1) * 0.55)
    )
    market["indiaBasket"] = round(brent * 1.04 + 2.2, 2)

    est_move = (brent - baselines["brent"]) * 0.38
    market["h030sg"] = round(baselines["h030sg"] + est_move, 2)

    # Keep dealer grade list in sync for raffia flagship; others track crude lightly
    for grade in market.get("grades", []):
        if grade.get("code") == "H030SG":
            grade["px"] = market["h030sg"]
        elif str(grade.get("code", "")).startswith("H"):
            grade["px"] = round(grade.get("px", market["h030sg"]) + est_move * 0.15, 2)

    hist_dates = market.setdefault("histDates", [])
    hist_pp = market.setdefault("histPP", [])
    hist_brent = market.setdefault("histBrent", [])
    if hist_dates and hist_dates[-1] == label:
        hist_pp[-1] = market["h030sg"]
        hist_brent[-1] = market["brent"]
    else:
        hist_dates.append(label)
        hist_pp.append(market["h030sg"])
        hist_brent.append(market["brent"])
        # Keep chart readable
        if len(hist_dates) > 14:
            market["histDates"] = hist_dates[-14:]
            market["histPP"] = hist_pp[-14:]
            market["histBrent"] = hist_brent[-14:]

    brent_mo = month_pct(brent_closes, (market.get("feedMoves") or [30.3])[0])
    wti_mo = month_pct(wti_closes, (market.get("feedMoves") or [0, 25.8])[1])
    market["feedMoves"] = [
        brent_mo,
        wti_mo,
        round(brent_mo * 0.85, 1),
        round(brent_mo * 0.55, 1),
        round((market["indiaBasket"] / baselines["indiaBasket"] - 1) * 100, 1),
    ]

    market["asOf"] = label
    market["updatedAt"] = now.isoformat().replace("+00:00", "Z")
    market["source"] = "github-actions-daily"
    pu = market.setdefault("polymerupdate", {})
    pu["synced"] = f"{label} · daily Actions refresh (headlines last curated snapshot)"
    return market


def main() -> None:
    market = json.loads(MARKET_FILE.read_text())
    try:
        brent, brent_closes = fetch_yahoo("BZ=F")
        wti, wti_closes = fetch_yahoo("CL=F")
    except (urllib.error.URLError, KeyError, IndexError, TimeoutError) as exc:
        raise SystemExit(f"Failed to fetch crude quotes: {exc}") from exc

    updated = apply_updates(market, brent, wti, brent_closes, wti_closes)
    MARKET_FILE.parent.mkdir(parents=True, exist_ok=True)
    MARKET_FILE.write_text(json.dumps(updated, indent=2) + "\n")
    print(
        f"Updated {MARKET_FILE.relative_to(ROOT)} · "
        f"asOf={updated['asOf']} · Brent=${updated['brent']} · "
        f"H030SG=₹{updated['h030sg']}"
    )


if __name__ == "__main__":
    main()
