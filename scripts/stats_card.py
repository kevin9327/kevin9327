#!/usr/bin/env python3
"""Build the profile's stats card as an animated SVG from the GitHub GraphQL API.

Self-hosted on purpose: the public readme-stats services rate-limit and die,
and a broken image on a profile is worse than none. Runs in CI with the
workflow token (GITHUB_TOKEN / GH_TOKEN) and writes dist/stats.svg.

Usage: python scripts/stats_card.py [login] [out_path]
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request
from collections import defaultdict

LOGIN = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("STATS_LOGIN", "kevin9327")
OUT = sys.argv[2] if len(sys.argv) > 2 else "dist/stats.svg"
TOKEN = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
if not TOKEN:
    raise SystemExit("GITHUB_TOKEN or GH_TOKEN is required")

QUERY = """
query($login: String!) {
  user(login: $login) {
    followers { totalCount }
    pullRequests(states: MERGED) { totalCount }
    contributionsCollection {
      totalCommitContributions
      totalPullRequestReviewContributions
      contributionCalendar { totalContributions }
    }
    repositories(first: 100, ownerAffiliations: OWNER, isFork: false,
                 orderBy: {field: STARGAZERS, direction: DESC}) {
      totalCount
      nodes {
        stargazerCount
        languages(first: 6, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name color } }
        }
      }
    }
  }
}
"""

req = urllib.request.Request(
    "https://api.github.com/graphql",
    data=json.dumps({"query": QUERY, "variables": {"login": LOGIN}}).encode(),
    headers={"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json",
             "User-Agent": "profile-stats-card"},
)
with urllib.request.urlopen(req, timeout=60) as r:
    payload = json.load(r)
if "errors" in payload:
    raise SystemExit(f"GraphQL error: {payload['errors']}")
u = payload["data"]["user"]

stars = sum(n["stargazerCount"] for n in u["repositories"]["nodes"])
sizes: dict[str, int] = defaultdict(int)
colors: dict[str, str] = {}
for n in u["repositories"]["nodes"]:
    for e in n["languages"]["edges"]:
        sizes[e["node"]["name"]] += e["size"]
        colors[e["node"]["name"]] = e["node"]["color"] or "#8b949e"
langs = sorted(sizes.items(), key=lambda kv: -kv[1])[:5]
total = sum(sizes.values()) or 1

cc = u["contributionsCollection"]
stats = [
    ("Contributions", cc["contributionCalendar"]["totalContributions"], "past year"),
    ("PRs merged", u["pullRequests"]["totalCount"], "all time"),
    ("Commits", cc["totalCommitContributions"], "past year"),
    ("Stars", stars, "earned"),
    ("Followers", u["followers"]["totalCount"], ""),
]


def fmt(n: int) -> str:
    return f"{n / 1000:.1f}k" if n >= 10000 else f"{n:,}"


W, H = 495, 160
parts = [
    f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
    f'font-family="Segoe UI, Helvetica Neue, Helvetica, Arial, sans-serif">',
    "<defs>",
    '<linearGradient id="hot" x1="0" y1="0" x2="1" y2="0">'
    '<stop offset="0" stop-color="#ec4899"/><stop offset="0.5" stop-color="#f97316"/>'
    '<stop offset="1" stop-color="#facc15"/>'
    '<animateTransform attributeName="gradientTransform" type="translate" '
    'values="-1 0;1 0;-1 0" dur="6s" repeatCount="indefinite"/></linearGradient>',
    '<linearGradient id="edge" x1="0" y1="0" x2="1" y2="1">'
    '<stop offset="0" stop-color="#ec4899" stop-opacity="0.9"/>'
    '<stop offset="1" stop-color="#facc15" stop-opacity="0.9"/></linearGradient>',
    "</defs>",
    f'<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="10" fill="#0d1117" stroke="url(#edge)"/>',
    '<text x="18" y="26" font-size="13" font-weight="700" fill="url(#hot)" letter-spacing="1.5">'
    f'{LOGIN.upper()} · BY THE NUMBERS</text>',
]

# left: five numbers, fading and sliding in one after another
x0, y0 = 18, 58
for i, (label, value, sub) in enumerate(stats):
    col, row = i % 3, i // 3
    x = x0 + col * 92
    y = y0 + row * 52
    begin = 0.15 + i * 0.12
    parts.append(
        f'<g opacity="0"><animate attributeName="opacity" values="0;1" dur="0.6s" begin="{begin:.2f}s" fill="freeze"/>'
        f'<animateTransform attributeName="transform" type="translate" values="0 8;0 0" dur="0.6s" begin="{begin:.2f}s" fill="freeze"/>'
        f'<text x="{x}" y="{y}" font-size="22" font-weight="800" fill="#f0f6fc">{fmt(value)}</text>'
        f'<text x="{x}" y="{y + 16}" font-size="10.5" font-weight="600" fill="#8b949e">{label}'
        f'{(" · " + sub) if sub else ""}</text></g>'
    )

# right: languages as bars that grow in
bx, by, bw = 300, 48, 170
parts.append(f'<text x="{bx}" y="{by - 10}" font-size="10.5" font-weight="700" fill="#8b949e" letter-spacing="1">TOP LANGUAGES</text>')
for i, (name, size) in enumerate(langs):
    frac = size / total
    y = by + i * 21
    w = max(6, bw * frac)
    begin = 0.4 + i * 0.12
    parts.append(
        f'<text x="{bx}" y="{y + 9}" font-size="10.5" font-weight="600" fill="#c9d1d9">{name}</text>'
        f'<rect x="{bx + 78}" y="{y}" width="{bw - 78}" height="10" rx="5" fill="#161b22"/>'
        f'<rect x="{bx + 78}" y="{y}" width="0" height="10" rx="5" fill="{colors[name]}">'
        f'<animate attributeName="width" values="0;{w * (bw - 78) / bw:.1f}" dur="0.9s" begin="{begin:.2f}s" '
        f'fill="freeze" calcMode="spline" keySplines="0.2 0.8 0.2 1"/></rect>'
        f'<text x="{bx + bw + 4}" y="{y + 9}" font-size="10" fill="#8b949e">{frac * 100:.0f}%</text>'
    )

parts.append("</svg>")
os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
with open(OUT, "w", encoding="utf-8", newline="\n") as f:
    f.write("".join(parts))
print(f"{OUT}: {[s[:2] for s in stats]} langs={[l[0] for l in langs]}")
