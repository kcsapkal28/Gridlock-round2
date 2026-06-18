import os, json, hashlib, shutil, pandas as pd
def _sha(p):
    h=hashlib.sha256(); h.update(open(p,"rb").read()); return h.hexdigest()[:16]
def build_static(scores_parquet, fe_out, out_dir, version="0.1.0"):
    os.makedirs(out_dir, exist_ok=True)
    df=pd.read_parquet(scores_parquet)
    ranked=df[df["ranked"]].sort_values("impact",ascending=False)
    cols=["gh7","lat","lon","impact","rank","n","tier3_share","heavy_share"]
    json.dump(ranked[cols].head(100).round(4).to_dict("records"),
              open(os.path.join(out_dir,"priority_table.json"),"w"))
    for fn in ["cells.geojson","top_enriched.geojson","kde_points.csv","rollup_gh6.csv","rollup_gh5.csv"]:
        src=os.path.join(fe_out,fn)
        if os.path.exists(src): shutil.copy(src, os.path.join(out_dir,fn))
    files=[]
    for fn in sorted(os.listdir(out_dir)):
        if fn=="manifest.json": continue
        p=os.path.join(out_dir,fn); files.append({"name":fn,"sha256":_sha(p),"bytes":os.path.getsize(p)})
    manifest={"artifacts_version":version,"files":files,
              "headline_stats":{"zones":int(len(df)),"ranked":int(df['ranked'].sum())}}
    json.dump(manifest, open(os.path.join(out_dir,"manifest.json"),"w"), indent=2)
    return manifest
