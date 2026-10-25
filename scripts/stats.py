#!/usr/bin/env python3
"""
stats.py - render a GitHub stats card as SVG. Stdlib only.

Replaces github-readme-stats / streak-stats, which are shared public instances
that go down (503), run out of quota (402) or time out. These are files in your
own repo, so they render as long as GitHub renders.

    python scripts/stats.py --user jhontabo --out assets

Writes <out>/stats-{dark,light}.svg.

A token in $GITHUB_TOKEN unlocks the contribution and streak numbers (they need
the GraphQL API). Without one the card still renders, minus those three tiles.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

UA = {"User-Agent": "stats.py"}

THEMES = {
    "dark": {
        "bg": "#0f172a", "border": "#1e293b", "title": "#38bdf8",
        "muted": "#94a3b8", "value": "#f1f5f9",
    },
    "light": {
        "bg": "#ffffff", "border": "#d0d7de", "title": "#0284c7",
        "muted": "#57606a", "value": "#1f2328",
    },
}

FONT = "ui-sans-serif,-apple-system,Segoe UI,Helvetica,Arial,sans-serif"


# --------------------------------------------------------------------------- #
# api
# --------------------------------------------------------------------------- #


def rest(path: str, token: str | None):
    req = urllib.request.Request("https://api.github.com" + path, headers=dict(UA))
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def graphql(query: str, variables: dict, token: str):
    body = json.dumps({"query": query, "variables": variables}).encode()
    req = urllib.request.Request("https://api.github.com/graphql", data=body,
                                 headers={**UA, "Content-Type": "application/json",
                                          "Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


CONTRIB_QUERY = """
query($login:String!){
  user(login:$login){
    contributionsCollection{
      contributionCalendar{
        totalContributions
        weeks{ contributionDays{ date contributionCount } }
      }
    }
  }
}
"""


def fetch_contributions(user: str, token: str | None):
    """Return (total, current_streak, longest_streak) or None without a token."""
    if not token:
        return None
    try:
        data = graphql(CONTRIB_QUERY, {"login": user}, token)
    except urllib.error.HTTPError as e:
        print(f"  contributions unavailable (HTTP {e.code})", file=sys.stderr)
        return None
    if data.get("errors"):
        print(f"  contributions unavailable: {data['errors'][0].get('message')}",
              file=sys.stderr)
        return None

    cal = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    days = [(dt.date.fromisoformat(d["date"]), d["contributionCount"])
            for w in cal["weeks"] for d in w["contributionDays"]]
    days.sort()

    longest = run = 0
    for _, c in days:
        run = run + 1 if c > 0 else 0
        longest = max(longest, run)

    # Today counts only if it already has activity; an empty today does not
    # break a streak that was alive yesterday.
    current = 0
    for date, c in reversed(days):
        if c > 0:
            current += 1
        elif date != days[-1][0]:
            break
    return cal["totalContributions"], current, longest


# --------------------------------------------------------------------------- #
# svg
# --------------------------------------------------------------------------- #


def esc(s: str) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def render_stats(user, stats, theme):
    c = THEMES[theme]
    pad = 22
    cols = 3
    rows = (len(stats) + cols - 1) // cols
    # Height follows the tile count, so the card does not leave a dead band when
    # the contribution tiles are unavailable.
    rh, W = 46, 480
    H = pad + 52 + (rows - 1) * rh + 17 + pad
    tw = (W - 2 * pad) / cols

    out = [
        f'<text x="{pad}" y="{pad + 14}" font-size="15" font-weight="700" '
        f'fill="{c["title"]}">{esc(user)}</text>',
        f'<text x="{W - pad}" y="{pad + 14}" font-size="11" text-anchor="end" '
        f'fill="{c["muted"]}">at a glance</text>',
        f'<line x1="{pad}" y1="{pad + 26}" x2="{W - pad}" y2="{pad + 26}" '
        f'stroke="{c["border"]}"/>',
    ]
    top = pad + 52
    for i, (label, value) in enumerate(stats):
        cx = pad + (i % cols) * tw
        cy = top + (i // cols) * rh
        out.append(
            f'<text x="{cx:.0f}" y="{cy:.0f}" font-size="23" font-weight="700" '
            f'fill="{c["value"]}">{esc(value)}</text>'
        )
        out.append(
            f'<text x="{cx:.0f}" y="{cy + 17:.0f}" font-size="10.5" '
            f'fill="{c["muted"]}">{esc(label)}</text>'
        )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
        f'width="{W}" height="{H}" role="img" aria-label="{esc(user)} GitHub statistics" '
        f'font-family="{FONT}">'
        f'<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="10" '
        f'fill="{c["bg"]}" stroke="{c["border"]}"/>'
        f'{"".join(out)}</svg>'
    )


# --------------------------------------------------------------------------- #


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--user", required=True)
    p.add_argument("--out", type=Path, default=Path("assets"))
    args = p.parse_args(argv)

    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    args.out.mkdir(parents=True, exist_ok=True)

    user = rest(f"/users/{args.user}", token)
    repos = []
    page = 1
    while True:
        batch = rest(f"/users/{args.user}/repos?per_page=100&page={page}&type=owner", token)
        repos += batch
        if len(batch) < 100:
            break
        page += 1
    stars = sum(r["stargazers_count"] for r in repos if not r["fork"])

    tiles = [("Total stars", f"{stars:,}"),
             ("Public repos", f"{user['public_repos']:,}"),
             ("Followers", f"{user['followers']:,}")]

    contrib = fetch_contributions(args.user, token)
    if contrib:
        total, current, longest = contrib
        tiles += [("Contributions (1y)", f"{total:,}"),
                  ("Current streak", f"{current:,} days"),
                  ("Longest streak", f"{longest:,} days")]
    else:
        print("  note: no usable token, skipping contribution tiles", file=sys.stderr)

    for theme in ("dark", "light"):
        dest = args.out / f"stats-{theme}.svg"
        dest.write_text(render_stats(args.user, tiles, theme), encoding="utf-8")
    print(f"wrote stats-*.svg  ({len(tiles)} tiles)")


if __name__ == "__main__":
    main()
