#!/usr/bin/env python3
"""Inline Chart.js and harden dashboard for htmldrop CSP."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HTML_PATH = ROOT / "index.html"
CHART_PATH = Path("/tmp/chart.umd.min.js")
MARKET_PATH = ROOT / "data" / "market.json"


def close_withchart(html: str, after_fn: str, next_fn: str) -> str:
    a = html.find(f"function {after_fn}")
    b = html.find(f"function {next_fn}", a + 1)
    if a < 0 or b < 0:
        print("cannot close", after_fn, "->", next_fn)
        return html
    chunk = html[a:b]
    idx = chunk.rfind("    });")
    if idx < 0:
        print("no end for", after_fn)
        return html
    if chunk[idx : idx + 7] == "    }));":
        return html
    chunk2 = chunk[:idx] + "    }));" + chunk[idx + 6 :]
    return html[:a] + chunk2 + html[b:]


def main() -> None:
    html = HTML_PATH.read_text()
    chart_js = CHART_PATH.read_text()
    market = json.loads(MARKET_PATH.read_text())

    cdn = '<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.7/dist/chart.umd.min.js"></script>'
    inline = (
        "<script>\n"
        "/* Chart.js 4.4.7 inlined for CSP hosts (htmldrop blocks CDN + connect-src) */\n"
        + chart_js
        + "\n</script>"
    )
    if cdn not in html:
        if "Chart.js 4.4.7 inlined" not in html:
            raise SystemExit("CDN script tag not found and Chart not inlined")
    else:
        html = html.replace(cdn, inline, 1)

    block = (
        '<script type="application/json" id="embedded-market">\n'
        + json.dumps(market, indent=2)
        + "\n</script>\n"
    )
    html = re.sub(
        r'<script type="application/json" id="embedded-market">[\s\S]*?</script>\n?',
        lambda _m: block,
        html,
        count=1,
    )

    html = html.replace(
        """  function setAsOf(label, live) {
    state.asOf = label;
    $("asOfPill").textContent = (live ? "Live · " : "As of ") + label;
  }""",
        """  function setAsOf(label, live) {
    state.asOf = label;
    setText("asOfPill", (live ? "Live · " : "As of ") + label);
  }""",
    )

    helper = """
  function withChart(canvasId, build) {
    try {
      if (typeof Chart === "undefined") throw new Error("Chart is not defined");
      const canvas = $(canvasId);
      if (!canvas) throw new Error("missing canvas " + canvasId);
      return build(canvas);
    } catch (e) {
      console.warn("chart skip", canvasId, e && e.message ? e.message : e);
      return null;
    }
  }
"""
    if "function withChart(" not in html:
        html = html.replace("  const charts = {};", "  const charts = {};\n" + helper)

    replacements = [
        (
            """    const ctx = $("riskGauge").getContext("2d");
    if (charts.risk) charts.risk.destroy();
    charts.risk = new Chart(ctx, {""",
            """    if (charts.risk) { try { charts.risk.destroy(); } catch (_) {} }
    charts.risk = withChart("riskGauge", (canvas) => new Chart(canvas.getContext("2d"), {""",
        ),
        (
            """    if (charts.hist) charts.hist.destroy();
    charts.hist = new Chart($("histChart"), {""",
            """    if (charts.hist) { try { charts.hist.destroy(); } catch (_) {} }
    charts.hist = withChart("histChart", (canvas) => new Chart(canvas, {""",
        ),
        (
            """    if (charts.feed) charts.feed.destroy();
    charts.feed = new Chart($("feedChart"), {""",
            """    if (charts.feed) { try { charts.feed.destroy(); } catch (_) {} }
    charts.feed = withChart("feedChart", (canvas) => new Chart(canvas, {""",
        ),
        (
            """    if (charts.proj) charts.proj.destroy();
    charts.proj = new Chart($("projChart"), {""",
            """    if (charts.proj) { try { charts.proj.destroy(); } catch (_) {} }
    charts.proj = withChart("projChart", (canvas) => new Chart(canvas, {""",
        ),
    ]
    for old, new in replacements:
        if old in html:
            html = html.replace(old, new, 1)
        else:
            print("skip missing pattern")

    # Close risk chart withChart wrapper
    risk_marker = """      options: {
        cutout: "72%",
        plugins: { legend: { display: false }, tooltip: { enabled: true } },
      },
    });
  }

  function chartDefaults()"""
    risk_repl = """      options: {
        cutout: "72%",
        plugins: { legend: { display: false }, tooltip: { enabled: true } },
      },
    }));
  }

  function chartDefaults()"""
    if risk_marker in html:
        html = html.replace(risk_marker, risk_repl, 1)

    html = close_withchart(html, "renderHist", "monthPct")
    html = close_withchart(html, "renderFeed", "renderProj")
    html = close_withchart(html, "renderProj", "setAsOf")

    # Network probe helpers
    if "let networkBlocked" not in html:
        inject = """
  let networkBlocked = false;
  async function canUseNetwork() {
    if (networkBlocked) return false;
    try {
      const ctrl = new AbortController();
      const t = setTimeout(() => ctrl.abort(), 800);
      await fetch(MARKET_URL + "?probe=" + Date.now(), { cache: "no-store", signal: ctrl.signal });
      clearTimeout(t);
      return true;
    } catch (e) {
      networkBlocked = true;
      return false;
    }
  }
"""
        html = html.replace(
            "  async function loadMarketSnapshot() {",
            inject + "\n  async function loadMarketSnapshot() {",
        )

    old_load = """  async function loadMarketSnapshot() {
    try {
      const res = await fetch(MARKET_URL + "?t=" + Date.now(), { cache: "no-store" });
      if (res.ok) {
        applySnapshot(await res.json());
        return { ok: true, via: "market.json" };
      }
    } catch (_) { /* fall through */ }
"""
    new_load = """  async function loadMarketSnapshot() {
    if (await canUseNetwork()) {
      try {
        const res = await fetch(MARKET_URL + "?t=" + Date.now(), { cache: "no-store" });
        if (res.ok) {
          applySnapshot(await res.json());
          return { ok: true, via: "market.json" };
        }
      } catch (_) { networkBlocked = true; }
    }
"""
    if old_load in html:
        html = html.replace(old_load, new_load, 1)

    old_live = """      try {
        const [brent, wti] = await Promise.all([
          fetchYahoo("BZ=F"),
          fetchYahoo("CL=F"),
        ]);
        live = applyLiveCrude(brent, wti);
      } catch (e) {
        liveErr = (e && e.message) ? e.message : "network";
      }
"""
    new_live = """      if (await canUseNetwork()) {
        try {
          const [brent, wti] = await Promise.all([
            fetchYahoo("BZ=F"),
            fetchYahoo("CL=F"),
          ]);
          live = applyLiveCrude(brent, wti);
        } catch (e) {
          liveErr = (e && e.message) ? e.message : "network";
          networkBlocked = true;
        }
      } else {
        liveErr = "host CSP blocks network";
      }
"""
    if old_live in html:
        html = html.replace(old_live, new_live, 1)

    html = html.replace(
        "Unlisted · password-gated · not indexed · long-lived access (owner-keyed host)",
        "Unlisted · password-gated · Chart.js inlined · refresh uses embedded snapshot (host CSP blocks live network)",
    )

    # Hero defaults
    html = re.sub(
        r'<b id="heroPPRef">[^<]*</b>',
        f'<b id="heroPPRef">₹{market["h030sg"]:.2f}/kg</b>',
        html,
        count=1,
    )
    html = re.sub(
        r'<b id="heroBrent">[^<]*</b>',
        f'<b id="heroBrent">${market["brent"]:.2f}/bbl</b>',
        html,
        count=1,
    )

    # Fallback state values
    state_start = html.find("const state = {")
    charts_start = html.find("const charts = {}")
    mid = html[state_start:charts_start]
    mid = re.sub(r'asOf: "[^"]+"', f'asOf: "{market["asOf"]}"', mid, count=1)
    mid = re.sub(r"brent: [0-9.]+", f"brent: {market['brent']}", mid, count=1)
    mid = re.sub(r"wti: [0-9.]+", f"wti: {market['wti']}", mid, count=1)
    mid = re.sub(r"\nh030sg: [0-9.]+", f"\nh030sg: {market['h030sg']}", mid, count=1)
    html = html[:state_start] + mid + html[charts_start:]

    HTML_PATH.write_text(html)
    print("wrote", HTML_PATH, "bytes", HTML_PATH.stat().st_size)
    print("inlined", "Chart.js 4.4.7 inlined" in html)
    print("cdn_removed", "cdn.jsdelivr.net/npm/chart.js" not in html)
    print("withChart", "function withChart" in html)
    print("networkBlocked", "networkBlocked" in html)


if __name__ == "__main__":
    main()
