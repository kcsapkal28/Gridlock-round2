import os, pandas as pd
from api.geo import encode_gh7, nearest_idx
class ScoringService:
    def __init__(self, scores_parquet, model_path=None):
        self.df=pd.read_parquet(scores_parquet).reset_index(drop=True)
        self.by_gh7={r.gh7:i for i,r in self.df.iterrows()}
        self.model=None
        if model_path and os.path.exists(model_path):
            try:
                import lightgbm as lgb; self.model=lgb.Booster(model_file=model_path)
            except Exception: self.model=None
        self.model_loaded=self.model is not None
    def _row(self,i):
        r=self.df.iloc[i]
        return {"gh7":r.gh7,"lat":float(r.lat),"lon":float(r.lon),"impact":float(r.impact),
                "rank":int(r["rank"]),"tier3_share":float(r.tier3_share),"heavy_share":float(r.heavy_share)}
    def _nearest(self,lat,lon,k=3):
        order=self.df.assign(_d=((self.df.lat-lat)**2+(self.df.lon-lon)**2)).nsmallest(k,"_d").index
        return [self._row(i) for i in order]
    def score(self,lat,lon):
        gh=encode_gh7(lat,lon)
        if gh in self.by_gh7:
            base=self._row(self.by_gh7[gh])
            return {**base,"source":"grid","degraded":False,"nearest":self._nearest(lat,lon)}
        nb=self._nearest(lat,lon)
        top=dict(nb[0]); top.update({"gh7":gh,"source":"nearest","degraded":True,"nearest":nb})
        return top
