#!/usr/bin/env python3
"""Publish the dashboard to htmldrop as a password-gated, unlisted link.

Kept as a fallback for sharing with people who should not need a GitHub
account. Each run mints a new random subdomain, so the URL changes every time.
GitHub Pages is the stable-URL route.

Usage:
    python3 scripts/publish_htmldrop.py [--password PASS] [--ttl-days N]
"""

import argparse
import json
import urllib.request
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DASHBOARD = ROOT / "index.html"
PUBLISH_DIR = ROOT / "publish"
OWNER_KEY_FILE = PUBLISH_DIR / "owner.key"
ACCESS_FILE = PUBLISH_DIR / "access.json"

ENDPOINT = "https://htmldrop.link/publish"


def load_owner_key() -> str:
    """Reuse the existing owner key so TTL limits stay lifted across republishes."""
    if OWNER_KEY_FILE.exists():
        return OWNER_KEY_FILE.read_text().strip()
    key = "pp-woven-owner-" + uuid.uuid4().hex
    PUBLISH_DIR.mkdir(exist_ok=True)
    OWNER_KEY_FILE.write_text(key + "\n")
    return key


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--password", default="PPWoven-26Jul")
    parser.add_argument("--ttl-days", type=int, default=3650)
    args = parser.parse_args()

    market_path = ROOT / "data" / "market.json"
    html = DASHBOARD.read_text()
    if market_path.exists():
        import re
        market_json = market_path.read_text().strip()
        block = (
            '<script type="application/json" id="embedded-market">\n'
            + market_json
            + "\n</script>\n"
        )
        if 'id="embedded-market"' in html:
            html = re.sub(
                r'<script type="application/json" id="embedded-market">[\s\S]*?</script>\n?',
                lambda _m: block,
                html,
                count=1,
            )
        else:
            html = html.replace(
                "<script>\n(function () {",
                block + "<script>\n(function () {",
                1,
            )
    payload = {
        "html": html,
        "title": "PP Woven Bag — Polymer Market Dashboard",
        "ttl_days": args.ttl_days,
        "password": args.password,
        "owner_key": load_owner_key(),
    }

    request = urllib.request.Request(
        ENDPOINT,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=90) as response:
        published = json.loads(response.read().decode())

    previous = json.loads(ACCESS_FILE.read_text()) if ACCESS_FILE.exists() else {}
    record = {
        "url": published["url"],
        "password": args.password,
        "expires_at": published.get("expiresAt") or published.get("expires_at"),
        "previous_url": previous.get("url"),
        "platform": "htmldrop (https://github.com/vin-spiegel/htmldrop)",
    }
    PUBLISH_DIR.mkdir(exist_ok=True)
    ACCESS_FILE.write_text(json.dumps(record, indent=2))

    print(f"URL:      {record['url']}")
    print(f"Password: {record['password']}")
    print(f"Expires:  {record['expires_at']}")


if __name__ == "__main__":
    main()
