#!/usr/bin/env python3
"""
stats.py - render a GitHub stats card as SVG. Stdlib only.

Replaces github-readme-stats / streak-stats, which are shared public instances
that go down (503), run out of quota (402) or time out. These are files in your
own repo, so they render as long as GitHub renders.

    python scripts/stats.py --user jhontabo --out assets

Writes, each as -dark / -light:
  <out>/stats-*.svg      at-a-glance numbers
  <out>/languages-*.svg  top languages by bytes across owned public repos
  <out>/activity-*.svg   weekly contributions over the last year

A token in $GITHUB_TOKEN unlocks the contribution numbers and the activity chart
(they need the GraphQL API). Without one the stats card renders minus those three
tiles and the activity chart is left as it was.
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
        "muted": "#94a3b8", "value": "#f1f5f9", "accent": "#38bdf8",
        "grid": "#1e293b", "track": "#1e293b",
    },
    "light": {
        "bg": "#ffffff", "border": "#d0d7de", "title": "#0284c7",
        "muted": "#57606a", "value": "#1f2328", "accent": "#0284c7",
        "grid": "#eaeef2", "track": "#eaeef2",
    },
}

FONT = "ui-sans-serif,-apple-system,Segoe UI,Helvetica,Arial,sans-serif"
MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()


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
    """Return (total, current_streak, longest_streak, weeks) or None without a
    token. `weeks` is [(week_start_date, count), ...] oldest first."""
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
    weeks = []
    for w in cal["weeks"]:
        ds = w["contributionDays"]
        weeks.append((dt.date.fromisoformat(ds[0]["date"]),
                      sum(d["contributionCount"] for d in ds)))
    return cal["totalContributions"], current, longest, weeks


def fetch_languages(repos, token, exclude: set[str]):
    """Sum language bytes across owned, non-fork, non-archived repos."""
    totals: dict[str, int] = {}
    for r in repos:
        if r["fork"] or r.get("archived"):
            continue
        try:
            langs = rest(r["languages_url"].replace("https://api.github.com", ""), token)
        except urllib.error.HTTPError:
            continue
        for name, n in langs.items():
            if name.lower() not in exclude:
                totals[name] = totals.get(name, 0) + n
    return sorted(totals.items(), key=lambda kv: -kv[1])


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

    out = [header(c, W, pad, user, "at a glance")]
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
    return frame(W, H, c, "".join(out), f"{user} GitHub statistics")


def frame(W, H, c, body, label):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
        f'width="{W}" height="{H}" role="img" aria-label="{esc(label)}" '
        f'font-family="{FONT}">'
        f'<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="10" '
        f'fill="{c["bg"]}" stroke="{c["border"]}"/>'
        f"{body}</svg>"
    )


def header(c, W, pad, title, note):
    return (
        f'<text x="{pad}" y="{pad + 14}" font-size="15" font-weight="700" '
        f'fill="{c["title"]}">{esc(title)}</text>'
        f'<text x="{W - pad}" y="{pad + 14}" font-size="11" text-anchor="end" '
        f'fill="{c["muted"]}">{esc(note)}</text>'
        f'<line x1="{pad}" y1="{pad + 26}" x2="{W - pad}" y2="{pad + 26}" '
        f'stroke="{c["border"]}"/>'
    )


def render_languages(langs, theme, limit=6):
    """Horizontal bars, one hue: share of bytes. Rest folds into 'Other'."""
    c = THEMES[theme]
    pad, W, rh = 22, 480, 22
    total = sum(n for _, n in langs) or 1
    top = langs[:limit - 1] if len(langs) > limit else langs
    rest_n = total - sum(n for _, n in top)
    rows = [(name, n / total) for name, n in top]
    if rest_n > 0:
        rows.append(("Other", rest_n / total))

    label_w, val_w = 92, 44
    bar_x = pad + label_w
    bar_w = W - 2 * pad - label_w - val_w
    top_y = pad + 46
    H = top_y + len(rows) * rh - 8 + pad

    out = [header(c, W, pad, "Top languages", "by code size, public repos")]
    for i, (name, frac) in enumerate(rows):
        y = top_y + i * rh
        w = max(4, bar_w * frac)  # track = 100%
        out.append(f'<text x="{pad}" y="{y + 4}" font-size="11.5" '
                   f'fill="{c["value"]}">{esc(name)}</text>')
        out.append(f'<rect x="{bar_x}" y="{y - 4}" width="{bar_w}" height="8" '
                   f'rx="4" fill="{c["track"]}"/>')
        out.append(f'<rect x="{bar_x}" y="{y - 4}" width="{w:.1f}" height="8" '
                   f'rx="4" fill="{c["accent"]}"/>')
        out.append(f'<text x="{W - pad}" y="{y + 4}" font-size="11" text-anchor="end" '
                   f'fill="{c["muted"]}">{frac * 100:.1f}%</text>')
    return frame(W, H, c, "".join(out), "Top languages by code size")


def render_activity(weeks, total, theme):
    """Weekly contributions as a 2px line over a faint area, one series."""
    c = THEMES[theme]
    W, H = 960, 240
    pad, left, bottom = 22, 52, 34
    x0, x1 = left, W - pad
    y0, y1 = H - bottom, pad + 46          # baseline, top of plot
    vals = [n for _, n in weeks]
    peak = max(vals) or 1
    # round the axis top up to a tidy step so gridlines land on whole numbers
    step = max(1, -(-peak // 4))
    for nice in (1, 2, 5, 10, 20, 25, 50, 100, 200, 500):
        if nice >= step:
            step = nice
            break
    ymax = step * 4

    def px(i):
        return x0 + (x1 - x0) * i / max(1, len(vals) - 1)

    def py(v):
        return y0 - (y0 - y1) * v / ymax

    out = [header(c, W, pad, "Contribution activity",
                  f"{total:,} contributions in the last year · weekly")]

    for k in range(5):
        v = step * k
        y = py(v)
        out.append(f'<line x1="{x0}" y1="{y:.1f}" x2="{x1}" y2="{y:.1f}" '
                   f'stroke="{c["grid"]}" stroke-width="1"/>')
        out.append(f'<text x="{x0 - 10}" y="{y + 4:.1f}" font-size="10.5" '
                   f'text-anchor="end" fill="{c["muted"]}">{v}</text>')

    # month ticks at the first week that starts in a new month
    last_m = None
    for i, (d, _) in enumerate(weeks):
        if d.month != last_m and i > 0:
            out.append(f'<text x="{px(i):.1f}" y="{y0 + 20}" font-size="10.5" '
                       f'text-anchor="middle" fill="{c["muted"]}">{MONTHS[d.month - 1]}</text>')
        last_m = d.month

    pts = " ".join(f"{px(i):.1f},{py(v):.1f}" for i, v in enumerate(vals))
    out.append(f'<polygon points="{x0},{y0} {pts} {x1},{y0}" '
               f'fill="{c["accent"]}" fill-opacity="0.14"/>')
    out.append(f'<polyline points="{pts}" fill="none" stroke="{c["accent"]}" '
               f'stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>')

    # direct label on the busiest week only
    i = vals.index(peak)
    px_, py_ = px(i), py(peak)
    out.append(f'<circle cx="{px_:.1f}" cy="{py_:.1f}" r="4.5" fill="{c["accent"]}" '
               f'stroke="{c["bg"]}" stroke-width="2"/>')
    anchor = "end" if px_ > W - 160 else "start"
    dx = -10 if anchor == "end" else 10
    d = weeks[i][0]
    out.append(f'<text x="{px_ + dx:.1f}" y="{py_ + 4:.1f}" font-size="11" '
               f'text-anchor="{anchor}" fill="{c["value"]}">'
               f'Peak: {peak} · week of {MONTHS[d.month - 1]} {d.day}</text>')
    return frame(W, H, c, "".join(out), "Weekly contributions over the last year")


# --------------------------------------------------------------------------- #


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--user", required=True)
    p.add_argument("--out", type=Path, default=Path("assets"))
    p.add_argument("--exclude", default="html,css,scss,shell,makefile,dockerfile,batchfile,blade",
                   help="comma-separated languages to leave out of the languages card")
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
        total, current, longest, weeks = contrib
        tiles += [("Contributions (1y)", f"{total:,}"),
                  ("Current streak", f"{current:,} days"),
                  ("Longest streak", f"{longest:,} days")]
    else:
        print("  note: no usable token, skipping contribution tiles", file=sys.stderr)

    for theme in ("dark", "light"):
        dest = args.out / f"stats-{theme}.svg"
        dest.write_text(render_stats(args.user, tiles, theme), encoding="utf-8")
    print(f"wrote stats-*.svg  ({len(tiles)} tiles)")

    excl = {x.strip().lower() for x in args.exclude.split(",") if x.strip()}
    langs = fetch_languages(repos, token, excl)
    if langs:
        for theme in ("dark", "light"):
            (args.out / f"languages-{theme}.svg").write_text(
                render_languages(langs, theme), encoding="utf-8")
        print(f"wrote languages-*.svg  ({len(langs)} languages)")

    if contrib:
        for theme in ("dark", "light"):
            (args.out / f"activity-{theme}.svg").write_text(
                render_activity(weeks, total, theme), encoding="utf-8")
        print(f"wrote activity-*.svg  ({len(weeks)} weeks)")


if __name__ == "__main__":
    main()
