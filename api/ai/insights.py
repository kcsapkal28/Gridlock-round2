"""Native candidate findings for the proactive-insights surface. We compute the patterns
deterministically from the scored data; Claude only phrases/prioritises them (spec pillar 4)."""


def candidates(svc):
    df = svc.df[svc.df["ranked"]].copy()
    if df.empty:
        return {"findings": []}
    df["rank_impact"] = df["impact"].rank(ascending=False)
    df["rank_volume"] = df["n"].rank(ascending=False)
    # under-counted: impact rank much better than volume rank (volume-blind hotspots)
    df["divergence"] = df["rank_volume"] - df["rank_impact"]
    found = []

    div = df.sort_values("divergence", ascending=False).head(3)
    for r in div.itertuples():
        if r.divergence > 50:
            found.append(f"zone {r.gh7}: impact rank #{int(r.rank_impact)} but only volume rank "
                         f"#{int(r.rank_volume)} ({int(r.n)} tickets) — high impact a count-based view misses")

    heavy = df.sort_values("heavy_share", ascending=False).head(2)
    for r in heavy.itertuples():
        if r.heavy_share > 0.3:
            found.append(f"zone {r.gh7}: {round(r.heavy_share*100)}% heavy/commercial vehicles "
                         f"(impact {round(r.impact,1)}) — freight choke point")

    t3 = df.sort_values("tier3_share", ascending=False).head(2)
    for r in t3.itertuples():
        if r.tier3_share > 0.6:
            found.append(f"zone {r.gh7}: {round(r.tier3_share*100)}% carriageway-blocking violations "
                         f"(impact {round(r.impact,1)})")

    # de-dup by gh7 mention while preserving order, cap to 6 candidates
    seen, out = set(), []
    for f in found:
        gh = f.split()[1].rstrip(":")
        if gh in seen:
            continue
        seen.add(gh)
        out.append(f)
    return {"findings": out[:6]}
