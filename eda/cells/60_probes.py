import pandas as pd, numpy as np
df=pd.read_parquet("/kaggle/working/cleaned.parquet")

print("="*60,"\n6.1 REPEAT OFFENDERS")
vc=df["vehicle_number"].value_counts()
print("unique vehicles:",len(vc),"| max tickets on one vehicle:",int(vc.max()))
print("tickets-per-vehicle: mean=%.2f median=%d p99=%d"%(vc.mean(),vc.median(),vc.quantile(.99)))
print("vehicles with >=10 tickets:",int((vc>=10).sum()),"| their share of all tickets: %.1f%%"%(vc[vc>=10].sum()/vc.sum()*100))
rep=vc[vc>=10].index
sub=df[df.vehicle_number.isin(rep)]
# are repeat offenders spatially concentrated? distinct cells per repeat vehicle
sub=sub.assign(glat=sub.latitude.round(3),glon=sub.longitude.round(3))
cells_per=sub.groupby("vehicle_number").apply(lambda d:d.groupby(["glat","glon"]).ngroups,include_groups=False)
print("repeat offenders: median distinct 110m-cells they're ticketed in = %.1f"%cells_per.median())

print("="*60,"\n6.2 PLATE-CORRECTION SIGNAL")
rev=df[df["validation_status_clean"]!="NULL"]
chg=(rev["vehicle_number"].astype(str)!=rev["updated_vehicle_number"].astype(str))
print("reviewed tickets:",len(rev),"| vehicle_number changed on review: %.2f%%"%(chg.mean()*100))
tchg=(rev["vehicle_type"].astype(str)!=rev["updated_vehicle_type"].astype(str))
print("vehicle_TYPE changed on review: %.2f%%"%(tchg.mean()*100))

print("="*60,"\n6.3 data_sent_to_scita MEANING")
print("overall TRUE rate: %.1f%%"%((df["data_sent_to_scita"]=="TRUE").mean()*100))
print("TRUE rate by validation_status:")
print(df.groupby("validation_status_clean")["data_sent_to_scita"].apply(lambda s:(s=="TRUE").mean()).round(3).to_string())
print("TRUE rate by month:")
ist=pd.to_datetime(df["created_dt"]).dt.tz_convert("Asia/Kolkata")
print(df.assign(m=ist.dt.to_period("M").astype(str)).groupby("m")["data_sent_to_scita"].apply(lambda s:(s=="TRUE").mean()).round(3).to_string())
