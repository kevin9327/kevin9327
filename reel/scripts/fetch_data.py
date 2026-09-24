"""Collect kevin9327's merged outside PRs (merge dates) for the profile reel -> src/data.json."""
import json, subprocess, datetime as dt, pathlib, collections

ME = "kevin9327"
OUT = pathlib.Path(__file__).resolve().parent.parent / "src" / "data.json"
Q = """query($q:String!,$c:String){search(query:$q,type:ISSUE,first:100,after:$c){pageInfo{hasNextPage endCursor}
nodes{... on PullRequest{number createdAt mergedAt repository{nameWithOwner isPrivate owner{login}}}}}}"""
WINDOWS = [("2026-01-01", "2026-08-15"), ("2026-08-16", "2026-08-31"), ("2026-09-01", "2026-09-10"),
           ("2026-09-11", "2026-09-17"), ("2026-09-18", "2026-09-24"), ("2026-09-25", "2026-12-31")]

def gh(args):
    r = subprocess.run(["gh"] + args, capture_output=True, text=True, encoding="utf-8")
    if r.returncode:
        raise RuntimeError(r.stderr[:300])
    return r.stdout

merged, first_created = {}, None
for a, b in WINDOWS:
    cur = None
    while True:
        args = ["api", "graphql", "-f", f"query={Q}", "-f", f"q=is:pr is:merged author:{ME} created:{a}..{b}"]
        if cur:
            args += ["-f", f"c={cur}"]
        d = json.loads(gh(args))["data"]["search"]
        for n in d["nodes"]:
            if not n:
                continue
            r = n["repository"]
            if r["owner"]["login"].lower() == ME or r["isPrivate"]:
                continue
            merged[(r["nameWithOwner"], n["number"])] = n
        if not d["pageInfo"]["hasNextPage"]:
            break
        cur = d["pageInfo"]["endCursor"]

days = sorted(n["mergedAt"][:10] for n in merged.values())
start = dt.date.fromisoformat(min(n["createdAt"][:10] for n in merged.values()))
end = dt.date.today()
per_day = collections.Counter(days)
series, total, d = [], 0, start
while d <= end:
    total += per_day.get(d.isoformat(), 0)
    series.append({"date": d.isoformat(), "total": total})
    d += dt.timedelta(days=1)

by_repo = collections.Counter(k[0] for k in merged)
top = [{"repo": r.split("/")[1], "owner": r.split("/")[0], "merged": c} for r, c in by_repo.most_common(8)]
out = {"generated": dt.datetime.now(dt.timezone.utc).isoformat(), "total": len(merged), "repos": len(by_repo),
       "start": start.isoformat(), "end": end.isoformat(), "days": (end - start).days, "series": series, "top": top,
       "all": [{"repo": r.split("/")[1], "merged": c} for r, c in by_repo.most_common()]}
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(out, indent=1), encoding="utf-8")
print(out["total"], "merged in", out["repos"], "repos over", out["days"], "days;", top)
