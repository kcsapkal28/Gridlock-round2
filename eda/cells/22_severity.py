import pandas as pd, json
df=pd.read_parquet("/kaggle/working/cleaned.parquet")
TIER={
 # Tier 3 - blocks moving lane / intersection
 "PARKING IN A MAIN ROAD":3,"DOUBLE PARKING":3,"PARKING NEAR ROAD CROSSING":3,
 "PARKING NEAR TRAFFIC LIGHT OR ZEBRA CROSS":3,"H T V PROHIBITED":3,
 "AGAINST ONE WAY/NO ENTRY":3,"STOPING ON WHITE/STOP LINE":3,"U TURN PROHIBITED":3,
 # Tier 2 - narrows carriageway / edge
 "WRONG PARKING":2,"NO PARKING":2,"PARKING OPPOSITE TO ANOTHER PARKED VEHICLE":2,
 "PARKING OTHER THAN BUS STOP":2,"PARKING NEAR BUSTOP/SCHOOL/HOSPITAL ETC":2,
 # Tier 1 - footpath
 "PARKING ON FOOTPATH":1,
 # Tier 0 - everything else (document/behaviour/moving) defaults to 0
}
viol=df["violation_type"].map(lambda x: json.loads(x) if isinstance(x,str) else [])
alllabels={v for vs in viol for v in vs}
unmapped=sorted(alllabels-set(TIER))
print("labels defaulting to Tier 0:", unmapped)
# GUARD: no Tier-2/3 label accidentally unmapped (these are the only acceptable Tier-0 defaults)
EXPECTED_T0={"DEFECTIVE NUMBER PLATE","USING BLACK FILM/OTHER MATERIALS","WITHOUT SIDE MIRROR",
 "REFUSE TO GO FOR HIRE","DEMANDING EXCESS FARE","FAIL TO USE SAFETY BELTS","RIDER NOT WEARING HELMET",
 "2W/3W - USING MOBILE PHONE","OTHER - USING MOBILE PHONE","JUMPING TRAFFIC SIGNAL",
 "VIOLATING LANE DISIPLINE","OBSTRUCTING DRIVER","CARRYING LENGHTY MATERIAL"}
assert set(unmapped)<=EXPECTED_T0, f"unexpected unmapped (would under-score!): {set(unmapped)-EXPECTED_T0}"
print("GUARD OK: only known Tier-0 labels are unmapped")
sev=viol.map(lambda vs:[TIER.get(v,0) for v in vs])
out=df[["id","is_valid"]].copy()
out["max_sev"]=sev.map(lambda s:max(s) if s else 0)
out["sev_sum"]=sev.map(sum)
out.to_parquet("/kaggle/working/derived/severity.parquet")
print("max_sev distribution:")
print(out["max_sev"].value_counts().sort_index().to_string())
print("tickets with a Tier-3 violation: %.2f%%" % ((out["max_sev"]==3).mean()*100))
