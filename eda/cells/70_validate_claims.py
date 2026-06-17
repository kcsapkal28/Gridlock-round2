import pandas as pd, numpy as np
raw=pd.read_parquet("/kaggle/working/raw.parquet")  # validate on RAW (pre-dedup) to match teammate
N=len(raw)
isnull=lambda s: raw[s].isin(["NULL",""]) | raw[s].isna()
vs=raw["validation_status"].where(~isnull("validation_status"),"NULL")

print("="*70,"\nCLAIM 1: vehicle_type vs updated_vehicle_type mismatch (44.03%)")
upd_nan = isnull("updated_vehicle_type")
print("  rows with updated_vehicle_type NaN: %.3f%%"%(upd_nan.mean()*100))
# (a) teammate's method: any row where raw != updated (NaN counts as mismatch)
mism_all=(raw["vehicle_type"].astype(str)!=raw["updated_vehicle_type"].astype(str))
print("  (a) mismatch over ALL rows (NaN-as-mismatch): %.3f%%"%(mism_all.mean()*100))
# (b) correct method: mismatch only among rows that were actually reviewed (updated present)
rev=raw[~upd_nan]
mism_rev=(rev["vehicle_type"].astype(str)!=rev["updated_vehicle_type"].astype(str))
print("  (b) mismatch among REVIEWED rows only: %.3f%%"%(mism_rev.mean()*100))
# (c) among approved only
appr=raw[vs=="approved"]
mism_app=(appr["vehicle_type"].astype(str)!=appr["updated_vehicle_type"].astype(str))
print("  (c) mismatch among APPROVED rows only: %.3f%%"%(mism_app.mean()*100))
print("  reconciliation: NaN%% + reviewed-change-share = %.2f + %.2f = %.2f"%(
    upd_nan.mean()*100, (mism_rev.sum()/N)*100, upd_nan.mean()*100+(mism_rev.sum()/N)*100))
print("  top raw->updated TYPE transitions (reviewed):")
tr=rev[mism_rev].groupby([rev[mism_rev]["vehicle_type"],rev[mism_rev]["updated_vehicle_type"]]).size().sort_values(ascending=False)
print(tr.head(8).to_string())

print("="*70,"\nCLAIM 2: rejection rate (30.1%)")
cnt=vs.value_counts()
print(cnt.to_string())
ar=cnt.get("approved",0)+cnt.get("rejected",0)
allrev=cnt.drop("NULL").sum()
print("  rejected / (approved+rejected) = %d/%d = %.2f%%"%(cnt['rejected'],ar,cnt['rejected']/ar*100))
print("  rejected / ALL reviewed         = %d/%d = %.2f%%"%(cnt['rejected'],allrev,cnt['rejected']/allrev*100))
print("  rejected / ALL rows             = %.2f%%"%(cnt['rejected']/N*100))

print("="*70,"\nCLAIM 3: data retained under filtering choices")
print("  approved-only: %.1f%% of rows"%(((vs=='approved').mean())*100))
is_valid=~vs.isin(["rejected","duplicate"])
print("  is_valid (drop rejected/dup, keep unreviewed): %.1f%% of rows"%(is_valid.mean()*100))

print("="*70,"\nCLAIM 4: 'midnight spike' - TIMEZONE CHECK")
dt_utc=pd.to_datetime(raw["created_datetime"],errors="coerce",utc=True)
hr_utc=dt_utc.dt.hour
hr_ist=dt_utc.dt.tz_convert("Asia/Kolkata").dt.hour
cu=hr_utc.value_counts().sort_index()
ci=hr_ist.value_counts().sort_index()
print("  UTC  hour 4=%d 5=%d 14=%d  | UTC peak hour=%d"%(cu.get(4,0),cu.get(5,0),cu.get(14,0),cu.idxmax()))
print("  IST  hour 4=%d 5=%d 14=%d  | IST peak hour=%d"%(ci.get(4,0),ci.get(5,0),ci.get(14,0),ci.idxmax()))
print("  => UTC %02d:00 (teammate's peak) == IST %02d:00"%(cu.idxmax(),(cu.idxmax()+5)%24 + (1 if False else 0)))
print("  IST share 22:00-06:00 (true overnight): %.2f%%"%(hr_ist.between(22,23).mean()*100+hr_ist.between(0,6).mean()*100))
print("  IST share 08:00-12:00 (morning):        %.2f%%"%(hr_ist.between(8,12).mean()*100))
