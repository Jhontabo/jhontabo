#!/usr/bin/env python3
"""Static fallback banner (stdlib only) until full generate.py can run with numpy/scipy.
Writes assets/banner-dark.svg and assets/banner-light.svg with same layout/ROWS.
Run: python3 scripts/banner/static.py
"""
from pathlib import Path
import html

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "assets"
W, H = 1180, 610
ROWS = [
    ("Subject", "Jhon Tajumbina"),
    ("Role", "Software Engineer · Media Buyer"),
    ("Origin", "Colombia"),
    ("Education", "Ing. de Sistemas · Univ. Mariana"),
    ("Status", "Building + Shipping + Optimizing"),
    ("ToolChain", "Neovim · BSPWM · Git"),
    ("Core.Lang", "TypeScript · PHP · Dart"),
    ("Core.Frontend", "React · Next.js · Tailwind"),
    ("Core.Backend", "Laravel · Node · Express"),
    ("Core.Mobile", "Flutter · Android"),
    ("Core.Data", "MySQL · Firebase"),
    ("Core.Infra", "Docker · AWS · Linux"),
    ("Grid.Mail", "jhonse.tajumbina@gmail.com"),
    ("Grid.LinkedIn", "/in/jhon-tajumbina-8917922a3"),
    ("Grid.GitHub", "jhontabo"),
    ("Grid.Ads", "Meta Ads · TikTok Ads"),
]
THEMES = {
    "dark": {"bg":"#0f172a","panel":"#0f172a","panel2":"#1e293b","line":"#334155","muted":"#94a3b8","text":"#e2e8f0","accent":"#38bdf8","ok":"#22c55e","shadow":"#020617"},
    "light": {"bg":"#F6F8FA","panel":"#FFFFFF","panel2":"#EDF3F7","line":"#CBD7E1","muted":"#64748B","text":"#172033","accent":"#0284c7","ok":"#16a34a","shadow":"#AAB7C4"},
}

def tw(s, fs=14): return len(s)*fs*0.605
def num(v): return f"{v:.1f}".rstrip("0").rstrip(".")

def render(theme):
    t = THEMES[theme]
    p = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img">']
    p.append(f'<rect width="{W}" height="{H}" rx="18" fill="{t["bg"]}"/>')
    p.append(f'<rect x="13" y="13" width="1154" height="584" rx="13" fill="{t["panel"]}" stroke="{t["line"]}"/>')
    p.append(f'<path d="M13 62H1167" stroke="{t["line"]}"/>')
    p.append('<circle cx="38" cy="38" r="6" fill="#FF5F57"/><circle cx="59" cy="38" r="6" fill="#FEBC2E"/><circle cx="80" cy="38" r="6" fill="#28C840"/>')
    p.append(f'<text x="590" y="43" text-anchor="middle" fill="{t["muted"]}" font-family="ui-monospace,Consolas,monospace" font-size="13">profile.sh --live</text>')
    p.append(f'<rect x="35" y="88" width="418" height="472" rx="6" fill="{t["panel2"]}" stroke="{t["line"]}"/>')
    p.append(f'<path d="M35 124H453" stroke="{t["line"]}"/>')
    p.append(f'<text x="49" y="111" fill="{t["accent"]}" font-family="ui-monospace,Consolas,monospace" font-size="13" font-weight="700">VISUAL.MAP</text>')
    # placeholder dot grid (static stand-in for 1-bit dither)
    dots = []
    import math
    for yy in range(150, 530, 10):
        for xx in range(70, 430, 10):
            dx, dy = (xx-250)/150, (yy-340)/170
            if dx*dx+dy*dy < 1 + 0.15*math.sin(xx/25)*math.cos(yy/25):
                dots.append(f"M{xx} {yy}h2")
    p.append(f'<path d="{"".join(dots)}" stroke="{t["accent"]}" stroke-width="2" opacity=".7"/>')
    p.append(f'<text x="58" y="551" fill="{t["muted"]}" font-family="ui-monospace,Consolas,monospace" font-size="10">STATIC PREVIEW · add assets/source/jhon.png + run banner/generate.py</text>')
    p.append(f'<rect x="474" y="88" width="672" height="472" rx="6" fill="{t["panel2"]}" stroke="{t["line"]}"/>')
    p.append(f'<path d="M474 124H1146" stroke="{t["line"]}"/>')
    p.append(f'<text x="490" y="111" fill="{t["accent"]}" font-family="ui-monospace,Consolas,monospace" font-size="13" font-weight="700">SYSTEM.INFO</text>')
    p.append(f'<circle cx="915" cy="106" r="4" fill="#FF4D5A"/><text x="927" y="111" fill="#FF4D5A" font-family="ui-monospace,Consolas,monospace" font-size="12" font-weight="700">LIVE</text>')
    p.append(f'<text x="1055" y="111" text-anchor="middle" fill="{t["accent"]}" font-family="ui-monospace,Consolas,monospace" font-size="14" font-weight="700">@jhontabo</text>')
    y = 153.0
    for label, value in ROWS:
        vl, ll = tw(value,14), tw(label,14)
        ls, le = 491+ll+12, 1127.0-vl-12
        leader = "".join(f"M{x} {num(y-4)}h1" for x in __import__("numpy") if False) if False else ""
        # simple leader without numpy
        x = ls
        segs = []
        while x < le:
            segs.append(f"M{int(x)} {num(y-4)}h1"); x += 5
        p.append(f'<text x="491" y="{num(y)}" fill="{t["muted"]}" font-family="ui-monospace,Consolas,monospace" font-size="14">{html.escape(label)}</text>')
        p.append(f'<path d="{"".join(segs)}" stroke="{t["line"]}" stroke-width="1"/>')
        p.append(f'<text x="1127" y="{num(y)}" text-anchor="end" fill="{t["text"]}" font-family="ui-monospace,Consolas,monospace" font-size="14">{html.escape(value)}</text>')
        y += 23
    p.append(f'<path d="M490 530H1130" stroke="{t["line"]}"/>')
    p.append(f'<text x="491" y="548" fill="{t["ok"]}" font-family="ui-monospace,Consolas,monospace" font-size="11">● ALL SYSTEMS NOMINAL</text>')
    p.append(f'<text x="1128" y="548" text-anchor="end" fill="{t["muted"]}" font-family="ui-monospace,Consolas,monospace" font-size="11">UTC-5 · COLOMBIA NODE</text>')
    p.append("</svg>")
    return "".join(p)

def main():
    for theme in ("dark","light"):
        (ASSETS/f"banner-{theme}.svg").write_text(render(theme), encoding="utf-8")
        print(f"wrote assets/banner-{theme}.svg")
if __name__ == "__main__":
    main()
