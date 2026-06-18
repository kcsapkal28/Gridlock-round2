import os, pandas as pd, pytest
FIX = "api/tests/fixtures/cell_scores_mini.parquet"
@pytest.fixture(scope="session", autouse=True)
def mini_scores():
    if not os.path.exists(FIX):
        src = "fe_work/cell_scores.parquet"
        if os.path.exists(src):
            d = pd.read_parquet(src)
            d[d["ranked"]].sort_values("impact", ascending=False).head(30).to_parquet(FIX)
        else:  # synthesize a minimal frame if the full parquet is absent
            import numpy as np
            pd.DataFrame({"gh7":[f"tdr1z{i:02d}" for i in range(30)],
                "gh6":["tdr1z"]*30,"gh5":["tdr1"]*30,
                "lat":12.97+np.linspace(0,0.05,30),"lon":77.59+np.linspace(0,0.05,30),
                "impact":np.linspace(99,60,30),"rank":range(1,31),"n":np.arange(60,90),
                "tier3_share":np.linspace(0.6,0.1,30),"heavy_share":np.linspace(0.4,0.0,30),
                "gi_z":np.linspace(4,1,30),"ranked":[True]*30}).to_parquet(FIX)
    return FIX
