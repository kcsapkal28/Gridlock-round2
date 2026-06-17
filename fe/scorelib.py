# fe/scorelib.py
import numpy as np, pandas as pd
def pct(s):  # percentile rank 0..1
    return pd.Series(s).rank(pct=True).values
def ensemble_impact(gi_z, pca_composite, alpha=0.5):
    raw=alpha*pct(gi_z)+(1-alpha)*pct(pca_composite)
    return 100.0*pct(raw)
def hand_composite(f):
    comp={"Volume":pct(f["n"]),"Severity":pct(f["sev_sum_total"]),
          "VehicleImpact":pct(f["heavy_share"]),"RoadContext":pct(f["f_main_road"]+f["f_junction"]),
          "Persistence":pct(f["recurrence_weeks"])}
    w={"Volume":.25,"Severity":.30,"VehicleImpact":.20,"RoadContext":.15,"Persistence":.10}
    return 100.0*pct(sum(w[k]*comp[k] for k in w))
