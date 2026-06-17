import pandas as pd, numpy as np, matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.close("all")
df=pd.read_parquet("/kaggle/working/cleaned.parquet")
ist=pd.to_datetime(df["created_dt"]).dt.tz_convert("Asia/Kolkata")
df["hour"]=ist.dt.hour
fig,ax=plt.subplots(1,2,figsize=(16,5))
df["hour"].value_counts().sort_index().plot.bar(ax=ax[0],title="Hour-of-day (IST) — overall")
ax[0].set_xlabel("hour"); ax[0].set_ylabel("tickets")
top6=df["police_station"].value_counts().head(6).index
for s in top6:
    df[df.police_station==s]["hour"].value_counts(normalize=True).sort_index().reindex(range(24),fill_value=0).plot(ax=ax[1],label=s,marker=".")
ax[1].legend(fontsize=7); ax[1].set_title("Hour profile by station (normalised)"); ax[1].set_xlabel("hour")
plt.tight_layout(); plt.savefig("/kaggle/working/eda_out/30_time_anomaly.png",dpi=110)
print("saved 30_time_anomaly.png")
dead=df["hour"].between(15,21).mean()*100
print(f"share of tickets in 15:00-21:00 IST: {dead:.2f}%")
# uniformity test: std of per-station dead-window share
per_station_dead=df.groupby("police_station")["hour"].apply(lambda h:h.between(15,21).mean())
print("per-station dead-share: mean=%.3f std=%.4f min=%.3f max=%.3f"%(
    per_station_dead.mean(),per_station_dead.std(),per_station_dead.min(),per_station_dead.max()))
# also check per-device uniformity (top 50 devices)
topdev=df["device_id"].value_counts().head(50).index
pdd=df[df.device_id.isin(topdev)].groupby("device_id")["hour"].apply(lambda h:h.between(15,21).mean())
print("per-device(top50) dead-share: mean=%.3f std=%.4f"%(pdd.mean(),pdd.std()))
# created_dt vs modified lag
mod=pd.to_datetime(df["modified_datetime"],errors="coerce",utc=True)
lag=(mod-df["created_dt"]).dt.total_seconds()/3600
print("created->modified lag hrs: median=%.2f p90=%.2f"%(lag.median(),lag.quantile(.9)))
