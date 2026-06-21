# fe/scorelib.py
import numpy as np, pandas as pd
def pct(s):  # percentile rank 0..1
    return pd.Series(s).rank(pct=True).values

def impact_character(f):
    """Volume-INDEPENDENT impact character: rates of carriageway-blocking / heavy / road-context.
    Prefers empirical-Bayes-smoothed rates (*_eb) when present (small-cell noise reduction)."""
    t3 = f["tier3_share_eb"] if "tier3_share_eb" in f else f["tier3_share"]
    hv = f["heavy_share_eb"] if "heavy_share_eb" in f else f["heavy_share"]
    road=(f["f_main_road"].values + f["f_junction"].values + f["f_circle"].values).clip(0,1) \
         if "f_circle" in f else (f["f_main_road"].values + f["f_junction"].values)
    return (pct(t3) + pct(hv) + pct(road)) / 3.0

def ensemble_impact(gi_z, char, beta=0.5):
    """Blend Gi* impact-significance (volume-aware) with impact-character (volume-independent)."""
    raw = beta*pct(gi_z) + (1.0-beta)*np.asarray(char)
    return 100.0*pct(raw)

# --- cross-checks (not the shipped score) ---
def hand_composite(f):
    comp={"Volume":pct(f["n"]),"Severity":pct(f["sev_sum_total"]),
          "VehicleImpact":pct(f["heavy_share"]),"RoadContext":pct(f["f_main_road"]+f["f_junction"]),
          "Persistence":pct(f["recurrence_weeks"])}
    w={"Volume":.25,"Severity":.30,"VehicleImpact":.20,"RoadContext":.15,"Persistence":.10}
    return 100.0*pct(sum(w[k]*comp[k] for k in w))
