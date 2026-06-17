# GridLock Parking-Congestion EDA — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Achieve complete, defensible understanding of the BTP parking-violation dataset — every distribution, bias, anomaly, and hidden spatial/temporal pattern — so that a later "congestion-impact score" can be built on signals we have explicitly validated rather than assumed.

**Architecture:** All computation runs on a **remote Kaggle Jupyter kernel** driven from this machine via `kaggle_exec.py` (already built + smoke-tested) over the kernel websocket. The dataset is already mounted at `/kaggle/input/datasets/kartikeysapkal/gridlock-round2-csv/jan to may police violation_anonymized791b166.csv`. Each analysis cell saves charts to `/kaggle/working/eda_out/*.png`; we pull them down with `kaggle_pull.py` and **visually inspect every one**. A cleaned `cleaned.parquet` checkpoint on `/kaggle/working` makes the session resumable across proxy-token expiry. Findings accrete into `eda/findings/FINDINGS.md`. The canonical reproducible notebook `gridlock_eda.ipynb` is assembled at the end.

**Tech Stack:** Python 3.12, pandas 2.3, numpy, matplotlib, seaborn, scikit-learn (DBSCAN), folium, pyarrow — all confirmed present on the kernel. Local driver venv has `requests` + `websocket-client`.

**Dynamic execution model:** This plan is a **decision tree, not a straight line.** Each phase ends in a **Decision Gate** with explicit, measurable criteria. The gate's outcome selects which follow-up tasks run next. Adaptive tasks are labelled `[SPAWNED IF ...]` with concrete trigger conditions — only execute them when the trigger fires. Record every gate decision in `FINDINGS.md` so the path taken is auditable.

**Verification-first discipline (the TDD analog for EDA):** No number is reported until a guard assertion proves the computation didn't silently corrupt the data. Typical guards: row counts conserved across transforms, group percentages sum to 100±0.1, parsed-array lengths equal across parallel columns, no coordinates outside the Bengaluru bbox after cleaning. The assertion is written and run *before* the finding is recorded — if it fails, the analysis is wrong, not the assertion.

**Commit cadence:** This project was `git init`'d locally. Commit after every task (driver code, findings updates, pulled charts referenced in findings). The dataset CSV and `.kaggle_url` are gitignored.

---

## File Structure

**Local (this repo — version-controlled):**
- `kaggle_exec.py` — remote kernel driver (EXISTS). Reads code from stdin/file, executes on kernel, prints output.
- `kaggle_pull.py` — CREATE. Downloads files from `/kaggle/working` via Contents API to local `eda/eda_out/`.
- `kaggle_lib.py` — CREATE. Importable form of the driver so other scripts can `run(code)` and `pull(path)` programmatically.
- `eda/findings/FINDINGS.md` — the running insight log; the primary human-readable deliverable.
- `eda/findings/DATA_DICTIONARY.md` — per-column meaning, dtype, null %, decision (keep/drop/derive).
- `eda/eda_out/*.png` — pulled charts (gitignored from bulk, but charts cited in FINDINGS are force-added).
- `eda/cells/*.py` — each analysis cell saved as a numbered source file, so the canonical notebook can be assembled deterministically and re-run.
- `gridlock_eda.ipynb` — CREATE in Phase 7. Canonical notebook assembled from `eda/cells/`.
- `.kaggle_url` — proxy URL (gitignored, holds the rotating token).

**Remote (`/kaggle/working/` — ephemeral, rebuilt from cells):**
- `eda_out/*.png` — generated charts.
- `cleaned.parquet` — cleaned dataframe checkpoint (resumability).
- `derived/*.parquet` — phase outputs (e.g. `grid_counts.parquet`, `hotspots.parquet`).

---

## Conventions used in every analysis task

Each analysis task follows this 6-step rhythm (the EDA analog of red-green-refactor):

1. **Write the guard** — an `assert` (or pair) that must hold if the computation is correct.
2. **Write the analysis cell** — save to `eda/cells/NN_name.py`, push via `kaggle_exec.py`.
3. **Run & confirm the guard passes** — if it fails, fix the analysis, not the guard.
4. **Save + pull the chart**, then **Read the PNG** to actually see it.
5. **Record the finding** — append a dated bullet to `FINDINGS.md`: what we saw, what it means for the impact score, what it rules in/out.
6. **Commit.**

Helper invocation patterns (used verbatim throughout):
```bash
# run a cell file on the remote kernel
.venv/bin/python kaggle_exec.py eda/cells/NN_name.py
# pull one or more artifacts down to eda/eda_out/
.venv/bin/python kaggle_pull.py eda_out/NN_chart.png
```

---

## Phase 0 — Plumbing, Load & Integrity Harness

Goal: a trustworthy, resumable connection to the data with integrity proven, before any analysis.

### Task 0.1: Create the artifact-pull helper

**Files:**
- Create: `kaggle_pull.py`

- [ ] **Step 1: Write the guard (as a runnable check)**

The guard for a downloader is a round-trip: a file written remotely must arrive locally byte-identical. We encode it as Step 4.

- [ ] **Step 2: Write `kaggle_pull.py`**

```python
#!/usr/bin/env python3
"""Download files from the remote Kaggle /kaggle/working dir via the Jupyter
Contents API. Usage: python kaggle_pull.py <remote_path> [<remote_path> ...]
Remote paths are relative to /kaggle/working (the server CWD), e.g. eda_out/x.png
Saves into eda/eda_out/ preserving basename."""
import os, sys, base64, requests

def base_url():
    u = os.environ.get("KAGGLE_URL")
    if not u and os.path.exists(".kaggle_url"):
        u = open(".kaggle_url").read().strip()
    if not u:
        sys.exit("Set KAGGLE_URL or create .kaggle_url")
    return u.rstrip("/")

def pull(remote_path, dest_dir="eda/eda_out"):
    http = base_url()
    os.makedirs(dest_dir, exist_ok=True)
    r = requests.get(f"{http}/api/contents/{remote_path}",
                     params={"format": "base64", "content": "1"}, timeout=120)
    r.raise_for_status()
    data = base64.b64decode(r.json()["content"])
    dest = os.path.join(dest_dir, os.path.basename(remote_path))
    with open(dest, "wb") as f:
        f.write(data)
    print(f"pulled {remote_path} -> {dest} ({len(data)} bytes)")
    return dest

if __name__ == "__main__":
    for p in sys.argv[1:]:
        pull(p)
```

- [ ] **Step 3: Push a probe file remotely**

Run:
```bash
.venv/bin/python kaggle_exec.py - <<'PY'
import os; os.makedirs("/kaggle/working/eda_out", exist_ok=True)
open("/kaggle/working/eda_out/_probe.bin","wb").write(b"GRIDLOCK"*4)
print("wrote probe")
PY
```
Expected: `wrote probe`

- [ ] **Step 4: Run the round-trip guard**

Run:
```bash
.venv/bin/python kaggle_pull.py eda_out/_probe.bin
.venv/bin/python -c "assert open('eda/eda_out/_probe.bin','rb').read()==b'GRIDLOCK'*4; print('ROUND-TRIP OK')"
```
Expected: `pulled ...` then `ROUND-TRIP OK`

- [ ] **Step 5: Commit**

```bash
git add kaggle_pull.py kaggle_exec.py .gitignore
git commit -m "feat(eda): add remote kernel driver + artifact pull helpers"
```

### Task 0.2: Create importable driver library

**Files:**
- Create: `kaggle_lib.py`

- [ ] **Step 1: Write `kaggle_lib.py`** (wraps the exec + pull so later tooling can call them)

```python
"""Importable helpers: run(code)->str executes on the remote kernel;
pull(remote_path)->local_path downloads an artifact."""
from kaggle_exec import run          # reuse the tested websocket exec
from kaggle_pull import pull         # reuse the tested downloader
__all__ = ["run", "pull"]
```

- [ ] **Step 2: Verify import + remote arithmetic**

Run:
```bash
.venv/bin/python -c "from kaggle_lib import run; out=run('print(6*7)'); assert '42' in out, out; print('LIB OK')"
```
Expected: `42` then `LIB OK`

- [ ] **Step 3: Commit**

```bash
git add kaggle_lib.py && git commit -m "feat(eda): importable remote driver library"
```

### Task 0.3: Load data + prove integrity + checkpoint

**Files:**
- Create: `eda/cells/00_load_integrity.py`

- [ ] **Step 1: Write guards + load cell**

```python
# eda/cells/00_load_integrity.py
import pandas as pd, numpy as np, hashlib, json, os
SRC = "/kaggle/input/datasets/kartikeysapkal/gridlock-round2-csv/jan to may police violation_anonymized791b166.csv"
df = pd.read_csv(SRC, dtype=str)            # read raw as str; we cast deliberately later
print("RAW shape:", df.shape)

# GUARD 1: expected row/col count (locally profiled = 298450 rows, 24 cols)
assert df.shape == (298450, 24), f"unexpected shape {df.shape}"

# GUARD 2: id is unique (primary key sanity)
assert df["id"].is_unique, "id not unique!"

# GUARD 3: lat/lon parse to float and sit inside Bengaluru bbox (allow tiny margin)
lat = pd.to_numeric(df["latitude"], errors="coerce")
lon = pd.to_numeric(df["longitude"], errors="coerce")
inbox = lat.between(12.7, 13.35) & lon.between(77.3, 77.9)
print("coords parseable:", lat.notna().mean()*100, "% ; in-bbox:", inbox.mean()*100, "%")

# Persist an immutable raw checkpoint as parquet (fast reload on token expiry)
os.makedirs("/kaggle/working", exist_ok=True)
df.to_parquet("/kaggle/working/raw.parquet")
print("checkpoint raw.parquet written")
print(df.dtypes.to_dict())
print(df.head(2).to_dict(orient="records"))
```

- [ ] **Step 2: Run it**

Run: `.venv/bin/python kaggle_exec.py eda/cells/00_load_integrity.py`
Expected: `RAW shape: (298450, 24)`, all three guards pass (no AssertionError), `checkpoint raw.parquet written`.

- [ ] **Step 3: Record baseline in DATA_DICTIONARY.md**

Create `eda/findings/DATA_DICTIONARY.md` with a table of all 24 columns: name, observed dtype, example value, and a "Decision" column initialised to `?`. (Populate from the printed `dtypes`/`head`.)

- [ ] **Step 4: Commit**

```bash
git add eda/cells/00_load_integrity.py eda/findings/DATA_DICTIONARY.md
git commit -m "feat(eda): load data, prove integrity, checkpoint raw.parquet"
```

> **DECISION GATE 0 — Coordinate validity.**
> - If `in-bbox ≥ 99%` → proceed normally; out-of-box rows are noise, drop them in Phase 1.
> - If `in-bbox < 99%` → `[SPAWNED]` add a sub-task in Phase 1.4 to map the out-of-box points (are they 0,0? a neighbouring city? swapped lat/lon?) before deciding to drop vs. repair.
> Record the chosen branch in `FINDINGS.md`.

---

## Phase 1 — Data Quality Deep-Dive (can we trust it?)

Goal: quantify nulls, parse the JSON-array columns, decode the validation lifecycle, find duplicates, and establish the **enforcement-bias baseline** — because this is a patrol log, not a sensor feed.

### Task 1.1: Null map + dead-column confirmation

**Files:** Create `eda/cells/10_nullmap.py`

- [ ] **Step 1: Write guard + cell**

```python
# eda/cells/10_nullmap.py
import pandas as pd, matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
df = pd.read_parquet("/kaggle/working/raw.parquet")
NULLTOK = df.isin(["NULL","null","",None]) | df.isna()
nullpct = (NULLTOK.mean()*100).sort_values(ascending=False)
print(nullpct.round(2).to_string())

# GUARD: known-dead columns are 100% null (from local profiling)
for c in ["description","closed_datetime","action_taken_timestamp"]:
    assert nullpct[c] == 100.0, f"{c} not fully null: {nullpct[c]}"

ax = nullpct.plot.barh(figsize=(8,9)); ax.invert_yaxis()
ax.set_title("Null % by column"); ax.set_xlabel("% null")
plt.tight_layout(); plt.savefig("/kaggle/working/eda_out/10_nullmap.png", dpi=120)
print("saved 10_nullmap.png")
```

- [ ] **Step 2: Run, pull, view**

```bash
.venv/bin/python kaggle_exec.py eda/cells/10_nullmap.py
.venv/bin/python kaggle_pull.py eda_out/10_nullmap.png
```
Then Read `eda/eda_out/10_nullmap.png`.

- [ ] **Step 3: Record finding + update DATA_DICTIONARY** — mark `description`, `closed_datetime`, `action_taken_timestamp` as **DROP**; note `data_sent_to_scita_timestamp` (~86% null) and the four 42%-null validation columns as a correlated null-block to investigate in 1.3.

- [ ] **Step 4: Commit**
```bash
git add eda/cells/10_nullmap.py eda/findings/ && git commit -m "feat(eda): null map + dead-column confirmation"
```

### Task 1.2: Parse JSON-array columns (violation_type / offence_code)

**Files:** Create `eda/cells/11_parse_arrays.py`

- [ ] **Step 1: Write guard + cell** (the two arrays must be parallel — equal length per row — or our severity logic breaks)

```python
# eda/cells/11_parse_arrays.py
import pandas as pd, json
df = pd.read_parquet("/kaggle/working/raw.parquet")
def parse(x):
    try: return json.loads(x) if isinstance(x,str) else []
    except Exception: return None
viol = df["violation_type"].map(parse)
offc = df["offence_code"].map(parse)

# GUARD 1: every row parses (no None)
assert viol.isna().sum()==0 and offc.isna().sum()==0, "unparseable array rows exist"
# GUARD 2: parallel arrays have equal length row-wise
mismatch = (viol.map(len) != offc.map(len))
print("length-mismatch rows:", int(mismatch.sum()))
assert mismatch.sum()==0, "violation_type and offence_code lengths differ"

# Build the code<->label map and check it's 1:1
pairs = set()
for vs,os_ in zip(viol,offc):
    for v,o in zip(vs,os_): pairs.add((o,v))
code2label = {}
ambig = []
for o,v in pairs:
    if o in code2label and code2label[o]!=v: ambig.append((o,v,code2label[o]))
    code2label[o]=v
print("distinct offence codes:", len(code2label), "| ambiguous mappings:", ambig)
df_arr = df[["id"]].copy(); df_arr["viol"]=viol; df_arr["offc"]=offc
df_arr["n_violations"]=viol.map(len)
df_arr.to_parquet("/kaggle/working/derived/arrays.parquet")
print("n_violations distribution:\n", df_arr["n_violations"].value_counts().to_string())
```
(Prepend `import os; os.makedirs("/kaggle/working/derived",exist_ok=True)`.)

- [ ] **Step 2: Run** — `.venv/bin/python kaggle_exec.py eda/cells/11_parse_arrays.py`. Expected: both guards pass; prints code→label map and multi-violation distribution.

- [ ] **Step 3: Record finding** — the offence_code↔label dictionary (paste into DATA_DICTIONARY), and how common multi-violation tickets are (matters: a single stop can carry several violations).

- [ ] **Step 4: Commit** — `git add eda/cells/11_parse_arrays.py eda/findings/ && git commit -m "feat(eda): parse + validate parallel violation arrays"`

### Task 1.3: Validation lifecycle + the 42% null block

**Files:** Create `eda/cells/12_validation.py`

- [ ] **Step 1: Write cell** — cross-tab `validation_status` against null-ness of `updated_vehicle_number`, `validation_timestamp`, and `data_sent_to_scita`; check whether `validation_status is null` ⇔ the whole update block is null (i.e. "never reviewed").

```python
# eda/cells/12_validation.py
import pandas as pd
df = pd.read_parquet("/kaggle/working/raw.parquet")
isnull = lambda s: df[s].isin(["NULL",""]) | df[s].isna()
vs = df["validation_status"].where(~isnull("validation_status"), "NULL")
print(vs.value_counts(dropna=False).to_string())
# GUARD: the 42%-null block is co-null (one review event populates all four)
block = ["validation_status","updated_vehicle_number","updated_vehicle_type","validation_timestamp"]
conull = pd.DataFrame({c: isnull(c) for c in block})
print("co-null agreement matrix:\n", conull.corr().round(3).to_string())
# scita send vs validation outcome
print(pd.crosstab(vs, df["data_sent_to_scita"], normalize="index").round(3).to_string())
```

- [ ] **Step 2: Run, record finding** — define what "approved/rejected/created1/processing/duplicate/NULL" mean operationally and decide: **for hotspot analysis, do we keep all tickets, or only `approved`?** (rejected tickets may be false positives that would pollute hotspots.)

- [ ] **Step 3: Commit** — `git commit -am "feat(eda): validation lifecycle analysis"`

> **DECISION GATE 1A — Which records count as a "real" violation.**
> - If `rejected + duplicate` is a small share (<10%) AND not spatially clustered → keep all, note caveat.
> - If `rejected`/`duplicate` is large OR concentrated in specific stations/devices → `[SPAWNED]` Task 1.3b: build a `is_valid` filter (`validation_status in {approved, created1, processing, NULL-but-sent}`) and carry both "all" and "valid-only" counts through spatial analysis to compare.
> Record decision + the filter definition in FINDINGS.

### Task 1.4: Duplicates + coordinate cleaning → `cleaned.parquet`

**Files:** Create `eda/cells/13_clean.py`

- [ ] **Step 1: Write guards + cell** — define duplicate as identical (`vehicle_number`, rounded lat/lon, `created_datetime` to the minute); cast dtypes; drop dead columns; drop/repair out-of-bbox coords per Gate 0; write `cleaned.parquet`.

```python
# eda/cells/13_clean.py
import pandas as pd, numpy as np
df = pd.read_parquet("/kaggle/working/raw.parquet")
n0=len(df)
for c in ["latitude","longitude"]: df[c]=pd.to_numeric(df[c],errors="coerce")
df["created_dt"]=pd.to_datetime(df["created_datetime"],errors="coerce",utc=True)
# duplicate key
df["_dupkey"]=(df["vehicle_number"].astype(str)+"|"+df["latitude"].round(5).astype(str)
              +"|"+df["longitude"].round(5).astype(str)+"|"+df["created_dt"].dt.floor("min").astype(str))
dups=df["_dupkey"].duplicated().sum()
print("exact-ish duplicate rows:", dups, f"({dups/n0*100:.2f}%)")
clean=df.drop_duplicates("_dupkey").copy()
# bbox filter (Gate 0 branch)
inbox=clean["latitude"].between(12.7,13.35)&clean["longitude"].between(77.3,77.9)
print("dropping out-of-bbox:", int((~inbox).sum()))
clean=clean[inbox]
clean=clean.drop(columns=["description","closed_datetime","action_taken_timestamp","_dupkey"])
# GUARD: monotonic shrink only, never grew, and lost < 5% total
assert len(clean)<=n0 and len(clean)>=0.95*n0, f"cleaning removed too much: {n0}->{len(clean)}"
clean.to_parquet("/kaggle/working/cleaned.parquet")
print("CLEANED rows:", len(clean), "from", n0)
```

- [ ] **Step 2: Run** — confirm guard passes; record cleaning ledger (rows in → dups → out-of-bbox → rows out) in FINDINGS. This `cleaned.parquet` is the basis for ALL later phases.

- [ ] **Step 3: Commit** — `git add eda/cells/13_clean.py eda/findings/ && git commit -m "feat(eda): dedup + coord clean -> cleaned.parquet"`

### Task 1.5: Enforcement-bias baseline (devices & officers)

**Files:** Create `eda/cells/14_enforcement_bias.py`

- [ ] **Step 1: Write cell** — Lorenz/Gini-style concentration of tickets across `device_id` and `created_by_id`; top-N share; activity span (first/last ticket per device). This quantifies the headline risk: are "hotspots" demand or patrol artifacts?

```python
# eda/cells/14_enforcement_bias.py
import pandas as pd, numpy as np, matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
df=pd.read_parquet("/kaggle/working/cleaned.parquet")
for col in ["device_id","created_by_id"]:
    c=df[col].value_counts()
    share_top10=c.head(int(len(c)*0.1)).sum()/c.sum()
    # Gini
    x=np.sort(c.values); n=len(x); cum=np.cumsum(x)
    gini=(n+1-2*np.sum(cum)/cum[-1])/n
    print(f"{col}: {len(c)} unique | top-10% make {share_top10*100:.1f}% of tickets | Gini={gini:.3f}")
df["device_id"].value_counts().head(30).plot.bar(figsize=(10,4),title="Tickets per device (top 30)")
plt.tight_layout(); plt.savefig("/kaggle/working/eda_out/14_device_concentration.png",dpi=120)
print("saved")
```

- [ ] **Step 2: Run, pull, view** the chart. **Record the most important caveat of the whole project here.**

- [ ] **Step 3: Commit** — `git commit -am "feat(eda): enforcement-bias baseline (device/officer Gini)"`

> **DECISION GATE 1B — Bias severity.**
> - If Gini < 0.5 (reasonably spread) → spatial density can be read fairly directly.
> - If Gini ≥ 0.5 (highly concentrated) → `[SPAWNED]` Phase 4 must include a **bias-normalised hotspot map** (tickets per active-device-hour per zone), not raw counts. Flag this forward.

---

## Phase 2 — Univariate & Severity Taxonomy

Goal: know the volume + mix of every categorical, and turn violation types into a **defensible congestion-severity ranking** (the weighting backbone of any impact score).

### Task 2.1: Categorical distributions (vehicle / violation / station / center)

**Files:** Create `eda/cells/20_univariate.py`

- [ ] **Step 1: Write guard + cell** — value-counts + bar charts for `vehicle_type`, exploded `violation_type`, `police_station`, `center_code`; guard that exploded violation counts sum back to total tags.

```python
# eda/cells/20_univariate.py
import pandas as pd, matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt, json
df=pd.read_parquet("/kaggle/working/cleaned.parquet")
viol=df["violation_type"].map(lambda x: json.loads(x) if isinstance(x,str) else [])
exploded=viol.explode()
# GUARD: explode conserves total tags
assert exploded.notna().sum()==viol.map(len).sum(), "explode lost tags"
fig,axes=plt.subplots(2,2,figsize=(15,11))
df["vehicle_type"].value_counts().head(15).plot.bar(ax=axes[0,0],title="vehicle_type (top15)")
exploded.value_counts().head(15).plot.bar(ax=axes[0,1],title="violation_type (top15)")
df["police_station"].value_counts().head(15).plot.bar(ax=axes[1,0],title="police_station (top15)")
df["center_code"].value_counts().head(15).plot.bar(ax=axes[1,1],title="center_code (top15)")
plt.tight_layout(); plt.savefig("/kaggle/working/eda_out/20_univariate.png",dpi=110)
print("saved")
```

- [ ] **Step 2: Run, pull, view, record.**
- [ ] **Step 3: Commit** — `git commit -am "feat(eda): univariate categorical distributions"`

### Task 2.2: Violation co-occurrence

**Files:** Create `eda/cells/21_cooccurrence.py`

- [ ] **Step 1: Write cell** — pairwise co-occurrence matrix of violation types within the same ticket (heatmap). Reveals which violations bundle (e.g. "wrong parking" + "main road").

```python
# eda/cells/21_cooccurrence.py
import pandas as pd, numpy as np, json, itertools, matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt, seaborn as sns
df=pd.read_parquet("/kaggle/working/cleaned.parquet")
viol=df["violation_type"].map(lambda x: json.loads(x) if isinstance(x,str) else [])
labels=sorted({v for vs in viol for v in vs})
idx={l:i for i,l in enumerate(labels)}
M=np.zeros((len(labels),len(labels)),int)
for vs in viol:
    for a,b in itertools.combinations(set(vs),2):
        M[idx[a],idx[b]]+=1; M[idx[b],idx[a]]+=1
top=pd.Series([v for vs in viol for v in vs]).value_counts().head(12).index.tolist()
sub=[idx[t] for t in top]
plt.figure(figsize=(11,9))
sns.heatmap(pd.DataFrame(M[np.ix_(sub,sub)],index=top,columns=top),annot=True,fmt="d",cmap="rocket_r")
plt.title("Violation co-occurrence (top 12)"); plt.tight_layout()
plt.savefig("/kaggle/working/eda_out/21_cooccurrence.png",dpi=110); print("saved")
```

- [ ] **Step 2: Run, pull, view, record** which bundles dominate.
- [ ] **Step 3: Commit** — `git commit -am "feat(eda): violation co-occurrence matrix"`

### Task 2.3: Build the congestion-severity taxonomy

**Files:** Create `eda/findings/SEVERITY_TAXONOMY.md` + `eda/cells/22_severity.py`

- [ ] **Step 1: Draft the taxonomy** — map every offence label to a **carriageway-impact tier** derived purely from the label semantics (native to the schema, no external data):
  - Tier 3 (high — blocks moving lane): `PARKING IN A MAIN ROAD`, `DOUBLE PARKING`, `PARKING NEAR ROAD CROSSING`, `PARKING NEAR TRAFFIC LIGHT OR ZEBRA CROSS`, `H T V PROHIBITED`, `AGAINST ONE WAY/NO ENTRY`.
  - Tier 2 (medium — narrows/edge): `WRONG PARKING`, `NO PARKING`, `PARKING OPPOSITE TO ANOTHER PARKED VEHICLE`, `PARKING OTHER THAN BUS STOP`, `PARKING NEAR BUSTOP/SCHOOL/HOSPITAL ETC`.
  - Tier 1 (low — footpath/non-flow): `PARKING ON FOOTPATH`.
  - Tier 0 (no flow impact — document-only/behavioural): `DEFECTIVE NUMBER PLATE`, `USING BLACK FILM`, `WITHOUT SIDE MIRROR`, `REFUSE TO GO FOR HIRE`, `DEMANDING EXCESS FARE`, mobile-phone/seatbelt/helmet codes.
- [ ] **Step 2: Encode it** in `22_severity.py` as a dict, attach `max_severity` + `severity_sum` per ticket, write `derived/severity.parquet`; guard that every observed label has a tier (no unmapped label silently scored 0).

```python
# eda/cells/22_severity.py
import pandas as pd, json
df=pd.read_parquet("/kaggle/working/cleaned.parquet")
TIER={ # paste full mapping from SEVERITY_TAXONOMY.md
 "PARKING IN A MAIN ROAD":3,"DOUBLE PARKING":3,"PARKING NEAR ROAD CROSSING":3,
 "PARKING NEAR TRAFFIC LIGHT OR ZEBRA CROSS":3,"H T V PROHIBITED":3,"AGAINST ONE WAY/NO ENTRY":3,
 "WRONG PARKING":2,"NO PARKING":2,"PARKING OPPOSITE TO ANOTHER PARKED VEHICLE":2,
 "PARKING OTHER THAN BUS STOP":2,"PARKING NEAR BUSTOP/SCHOOL/HOSPITAL ETC":2,
 "PARKING ON FOOTPATH":1,
}
viol=df["violation_type"].map(lambda x: json.loads(x) if isinstance(x,str) else [])
alllabels={v for vs in viol for v in vs}
unmapped=alllabels-set(TIER)
print("UNMAPPED labels (default to 0):", sorted(unmapped))
# GUARD: every Tier>=1 label we intended is present; unmapped are only the known Tier-0 set
sev=viol.map(lambda vs:[TIER.get(v,0) for v in vs])
out=df[["id"]].copy(); out["max_sev"]=sev.map(lambda s:max(s) if s else 0)
out["sev_sum"]=sev.map(sum)
out.to_parquet("/kaggle/working/derived/severity.parquet")
print(out["max_sev"].value_counts().sort_index().to_string())
```

- [ ] **Step 3: Run, record** the severity distribution; commit taxonomy + cell. `git add eda/cells/22_severity.py eda/findings/SEVERITY_TAXONOMY.md && git commit -m "feat(eda): congestion-severity taxonomy"`

> **DECISION GATE 2 — Severity coverage.** If any Tier-2/3 label landed in `unmapped`, stop and add it to the taxonomy before proceeding (it would under-score real congestion). If only the documented Tier-0 set is unmapped, proceed.

---

## Phase 3 — Temporal + Timestamp Anomaly Investigation

Goal: **first decide whether `created_datetime` reflects real violation timing or enforcement scheduling**, then characterise trends. Time convention is decided HERE (per earlier agreement), not assumed.

### Task 3.1: Crack the hour-of-day anomaly

**Files:** Create `eda/cells/30_time_anomaly.py`

- [ ] **Step 1: Write cell** — convert to IST; plot hour-of-day overall, then split by `device_id` cohort and by `police_station`; test whether the dead 3–9 PM window is uniform (⇒ systemic/scheduling) or station-specific (⇒ partly real). Also compare `created_dt` vs `modified_datetime` lag.

```python
# eda/cells/30_time_anomaly.py
import pandas as pd, matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
df=pd.read_parquet("/kaggle/working/cleaned.parquet")
ist=pd.to_datetime(df["created_dt"]).dt.tz_convert("Asia/Kolkata")
df["hour"]=ist.dt.hour
fig,ax=plt.subplots(1,2,figsize=(15,5))
df["hour"].value_counts().sort_index().plot.bar(ax=ax[0],title="Hour-of-day (IST) — overall")
# per-station hour profile for top 6 stations -> are they all dead 15-21h?
top6=df["police_station"].value_counts().head(6).index
for s in top6:
    df[df.police_station==s]["hour"].value_counts(normalize=True).sort_index().plot(ax=ax[1],label=s)
ax[1].legend(fontsize=7); ax[1].set_title("Hour profile by station (normalised)")
plt.tight_layout(); plt.savefig("/kaggle/working/eda_out/30_time_anomaly.png",dpi=110)
# quantify the dead window
dead=df["hour"].between(15,21).mean()*100
print(f"share of tickets in 15:00-21:00 IST: {dead:.2f}%")
print("uniform-across-stations check (std of dead-share):",
      df.groupby("police_station")["hour"].apply(lambda h:h.between(15,21).mean()).std().round(4))
```

- [ ] **Step 2: Run, pull, view, record.**

> **DECISION GATE 3 — Timestamp trustworthiness (THE pivotal gate).**
> - If the dead window is **uniform across all stations/devices** (low std) → timestamps reflect **enforcement scheduling, not violation timing**. **Decision:** time-of-day must NOT be used as a literal congestion proxy; use it only to describe *enforcement activity*. Record this prominently; it constrains Phase 6 and the impact score.
> - If the dead window **varies by station** → timing is at least partly real; `[SPAWNED]` Task 3.1b: model hour-of-day per zone and treat it as a weak congestion-time signal with documented caveats.
> - Either way, write the chosen **time convention** (IST) and the trust verdict into FINDINGS + DATA_DICTIONARY.

### Task 3.2: Calendar trends (month / week / dow) + growth

**Files:** Create `eda/cells/31_calendar.py`

- [ ] **Step 1: Write cell** — daily time series (with 7-day rolling mean), month totals, day-of-week profile; flag the partial first/last months (Nov-09 start, Apr-08 end) so trend isn't misread.

```python
# eda/cells/31_calendar.py
import pandas as pd, matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
df=pd.read_parquet("/kaggle/working/cleaned.parquet")
ist=pd.to_datetime(df["created_dt"]).dt.tz_convert("Asia/Kolkata")
daily=ist.dt.date.value_counts().sort_index()
# GUARD: every daily count > 0 and date range matches expectation
assert str(daily.index.min())>="2023-11-09" and str(daily.index.max())<="2024-04-09", "date range drift"
fig,ax=plt.subplots(2,1,figsize=(14,9))
s=pd.Series(daily.values,index=pd.to_datetime(list(daily.index)))
s.plot(ax=ax[0],alpha=.4); s.rolling(7).mean().plot(ax=ax[0],lw=2,title="Daily tickets + 7d rolling")
ist.dt.day_name().value_counts().reindex(["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]).plot.bar(ax=ax[1],title="Day-of-week")
plt.tight_layout(); plt.savefig("/kaggle/working/eda_out/31_calendar.png",dpi=110); print("saved")
```

- [ ] **Step 2: Run, pull, view, record** trends + the partial-month caveat. Commit.

---

## Phase 4 — Spatial Hotspots (the core deliverable)

Goal: turn point-tickets into stable, defensible hotspot zones; connect them to junctions; apply bias-normalisation if Gate 1B demanded it.

### Task 4.1: Geohash/grid binning + density choropleth

**Files:** Create `eda/cells/40_grid.py`

- [ ] **Step 1: Write guard + cell** — bin to a ~150–250 m grid (round lat/lon to 3 dp ≈ 110 m, or use a geohash precision-7); count per cell; guard that summed cell counts == total rows; save `derived/grid_counts.parquet`; plot a hexbin density map.

```python
# eda/cells/40_grid.py
import pandas as pd, numpy as np, matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
df=pd.read_parquet("/kaggle/working/cleaned.parquet")
df["glat"]=df["latitude"].round(3); df["glon"]=df["longitude"].round(3)  # ~110m cells
grid=df.groupby(["glat","glon"]).size().rename("n").reset_index()
# GUARD: binning conserves all rows
assert grid["n"].sum()==len(df), "grid lost rows"
grid.to_parquet("/kaggle/working/derived/grid_counts.parquet")
print("cells:", len(grid), "| top cell count:", grid["n"].max(),
      "| cells holding 50% of tickets:",
      (grid.sort_values("n",ascending=False)["n"].cumsum()<=0.5*len(df)).sum())
plt.figure(figsize=(9,9))
plt.hexbin(df["longitude"],df["latitude"],gridsize=120,cmap="inferno",bins="log")
plt.colorbar(label="log tickets"); plt.title("Parking-violation density (Bengaluru)")
plt.savefig("/kaggle/working/eda_out/40_density.png",dpi=120); print("saved")
```

- [ ] **Step 2: Run, pull, view, record** the spatial concentration ("X cells hold 50% of all tickets" is a headline insight). Commit.

### Task 4.2: DBSCAN hotspot clustering

**Files:** Create `eda/cells/41_dbscan.py`

- [ ] **Step 1: Write cell** — DBSCAN on radians (haversine metric), `eps≈150 m`, `min_samples` tuned to volume; label clusters; rank by ticket count × Tier-3 share (join `derived/severity.parquet`); save `derived/hotspots.parquet`.

```python
# eda/cells/41_dbscan.py
import pandas as pd, numpy as np
from sklearn.cluster import DBSCAN
df=pd.read_parquet("/kaggle/working/cleaned.parquet")
sev=pd.read_parquet("/kaggle/working/derived/severity.parquet")
df=df.merge(sev,on="id",how="left")
coords=np.radians(df[["latitude","longitude"]].values)
eps=150/6371000.0  # 150m in radians
db=DBSCAN(eps=eps,min_samples=30,metric="haversine",algorithm="ball_tree").fit(coords)
df["cluster"]=db.labels_
n_clusters=df["cluster"].nunique()-(1 if -1 in df["cluster"].values else 0)
print("clusters:",n_clusters,"| noise pts:",(df["cluster"]==-1).mean()*100,"%")
agg=(df[df.cluster>=0].groupby("cluster")
     .agg(n=("id","size"),lat=("latitude","mean"),lon=("longitude","mean"),
          tier3_share=("max_sev",lambda s:(s>=3).mean()),
          top_station=("police_station",lambda s:s.mode().iat[0]))
     .sort_values("n",ascending=False))
agg.to_parquet("/kaggle/working/derived/hotspots.parquet")
print(agg.head(20).to_string())
```

- [ ] **Step 2: Run, record** top hotspots (lat/lon + dominant station + severity share). These are the prototype's headline output.

> **DECISION GATE 4 — Cluster quality.** If noise > 60% or n_clusters < 10 → re-tune (`min_samples`/`eps`) via a spawned task and document the sweep; if clusters look stable, proceed.

### Task 4.3: Interactive folium hotspot map + junction linkage

**Files:** Create `eda/cells/42_map_junctions.py`

- [ ] **Step 1: Write cell** — folium HeatMap of all tickets + markers for top-20 clusters; cross-tab cluster vs `junction_name` ("No Junction" vs named BTP junction); save HTML to `/kaggle/working/eda_out/42_hotspots.html` and a static PNG fallback.

```python
# eda/cells/42_map_junctions.py
import pandas as pd, folium
from folium.plugins import HeatMap
df=pd.read_parquet("/kaggle/working/cleaned.parquet")
hot=pd.read_parquet("/kaggle/working/derived/hotspots.parquet")
m=folium.Map(location=[12.97,77.59],zoom_start=12,tiles="cartodbpositron")
HeatMap(df[["latitude","longitude"]].sample(min(50000,len(df)),random_state=0).values,radius=8).add_to(m)
for cl,r in hot.head(20).iterrows():
    folium.CircleMarker([r.lat,r.lon],radius=6,color="red",fill=True,
        popup=f"cluster {cl}: {int(r.n)} tickets, T3={r.tier3_share:.0%}, {r.top_station}").add_to(m)
m.save("/kaggle/working/eda_out/42_hotspots.html")
# junction linkage
named=df["junction_name"].ne("No Junction")&df["junction_name"].notna()
print("tickets at named junctions:",named.mean()*100,"%")
print(df[named]["junction_name"].value_counts().head(15).to_string())
```

- [ ] **Step 2: Run, pull both** (`kaggle_pull.py eda_out/42_hotspots.html` + view the static map); record the named-junction share and top junctions. Commit.

### Task 4.4 `[SPAWNED IF Gate 1B = high bias]`: Bias-normalised hotspot map

- [ ] Only if device/officer Gini ≥ 0.5. Recompute per-cell intensity as `tickets / (active_device_hours in cell)` so a hotspot reflects demand, not patrol frequency. Compare ranked hotspots raw vs normalised; record which zones change rank (a key credibility point for BTP).

---

## Phase 5 — Cross-Dimensional Analysis

Goal: characterise *what kind* of hotspot each is — the contextual fuel for an impact score.

### Task 5.1: Violation × location, vehicle × violation, severity × station

**Files:** Create `eda/cells/50_crosstabs.py`

- [ ] **Step 1: Write cell** — (a) for top-20 clusters, the violation-type mix; (b) vehicle_type × max_sev heatmap; (c) per-station mean severity ranking. Guard each crosstab's marginal totals.

```python
# eda/cells/50_crosstabs.py
import pandas as pd, json, matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt, seaborn as sns
df=pd.read_parquet("/kaggle/working/cleaned.parquet")
sev=pd.read_parquet("/kaggle/working/derived/severity.parquet")
df=df.merge(sev,on="id")
ct=pd.crosstab(df["vehicle_type"],df["max_sev"],normalize="index")
# GUARD: each row sums to 1
assert (ct.sum(axis=1).round(3)==1).all(), "crosstab rows don't normalise"
plt.figure(figsize=(10,8)); sns.heatmap(ct.loc[df["vehicle_type"].value_counts().head(15).index],annot=True,fmt=".2f",cmap="mako")
plt.title("Vehicle type × max severity tier"); plt.tight_layout()
plt.savefig("/kaggle/working/eda_out/50_vehicle_severity.png",dpi=110)
print(df.groupby("police_station")["max_sev"].mean().sort_values(ascending=False).head(15).to_string())
```

- [ ] **Step 2: Run, pull, view, record** which vehicle types drive high-severity violations and which stations are "high-severity" beyond raw volume. Commit.

### Task 5.2: Space × time coupling

**Files:** Create `eda/cells/51_space_time.py`

- [ ] **Step 1: Write cell** — for the top-10 clusters, hour-of-day profile (subject to Gate 3's trust verdict — label axis "enforcement activity" if timestamps deemed scheduling-driven). Reveals whether hotspots are persistent or time-localised.
- [ ] **Step 2: Run, pull, view, record.** Commit.

---

## Phase 6 — Hidden-Pattern Hunt ("know it in-and-out")

Goal: the open-ended insight phase. Each task is a hypothesis probe; negative results are recorded too (knowing what *isn't* there is also understanding).

### Task 6.1: Repeat offenders & fleet/commercial behaviour

**Files:** Create `eda/cells/60_repeat_offenders.py`
- [ ] Probe: distribution of tickets per `vehicle_number`; do a few vehicles get ticketed dozens of times? Are repeat offenders spatially concentrated (same street) → chronic-spot signal? Record. Commit.

### Task 6.2: Vehicle-number anonymisation leakage check
**Files:** Create `eda/cells/61_vehnum_check.py`
- [ ] Probe: `vehicle_number` vs `updated_vehicle_number` mismatch rate (the validation correction signal); whether anonymised IDs still encode useful structure (length/prefix patterns). Record whether it's usable or noise. Commit.

### Task 6.3: `data_sent_to_scita` meaning
**Files:** Create `eda/cells/62_scita.py`
- [ ] Probe: what distinguishes TRUE vs FALSE rows (station? time? violation type?). SCITA = traffic integration system; the flag may indicate which tickets fed downstream — relevant to data completeness. Record. Commit.

### Task 6.4: Spatial-severity divergence map
**Files:** Create `eda/cells/63_severity_density.py`
- [ ] Probe: plot a second hexbin weighted by `sev_sum` instead of raw count; overlay/diff against the raw-count map (40_density). Where do they diverge? Those are **high-impact-but-low-volume** zones an enforcement-by-count approach would miss — a flagship insight for the "quantify impact" mandate. Pull, view, record. Commit.

### Task 6.5: Completeness critic
**Files:** Create `eda/cells/64_completeness.py`
- [ ] Re-read FINDINGS.md; list every column not yet analysed, every gate decision, every "TODO"/open question. Spawn a final probe task for any unexamined column. Record gaps closed. Commit.

> **DECISION GATE 6 — Saturation.** If 6.5 surfaces a materially unexamined column or an unresolved contradiction, spawn a targeted task to close it before Phase 7. If everything is covered and internally consistent, proceed to synthesis.

---

## Phase 7 — Synthesis & Canonical Notebook

Goal: a single re-runnable artifact + an executive findings report.

### Task 7.1: Assemble `gridlock_eda.ipynb`

**Files:** Create `build_notebook.py`, `gridlock_eda.ipynb`

- [ ] **Step 1: Write `build_notebook.py`** — read `eda/cells/*.py` in numeric order, wrap each as a code cell with a markdown header, prepend an intro markdown cell, emit `gridlock_eda.ipynb` via `nbformat`.

```python
# build_notebook.py
import nbformat as nbf, glob, os, re
nb=nbf.v4.new_notebook(); cells=[nbf.v4.new_markdown_cell(
  "# GridLock Parking-Congestion EDA\nReproducible analysis. Reads from /kaggle/input; writes charts to /kaggle/working/eda_out.")]
for f in sorted(glob.glob("eda/cells/*.py")):
    name=os.path.basename(f)
    cells.append(nbf.v4.new_markdown_cell(f"## {name}"))
    cells.append(nbf.v4.new_code_cell(open(f).read()))
nb["cells"]=cells; nbf.write(nb,"gridlock_eda.ipynb"); print("wrote gridlock_eda.ipynb with",len(cells),"cells")
```

- [ ] **Step 2: Run locally** (`.venv/bin/python -m pip install nbformat -q` first), then **upload to Kaggle** via Contents API and **execute end-to-end** to prove it runs clean from a fresh kernel. Guard: notebook runs with zero exceptions.
- [ ] **Step 3: Commit** — `git add build_notebook.py gridlock_eda.ipynb && git commit -m "feat(eda): assemble reproducible canonical notebook"`

### Task 7.2: Write the EDA findings report

**Files:** Create `eda/findings/EDA_REPORT.md`

- [ ] **Step 1: Write the report** — structured executive summary: dataset overview, data-quality verdict, enforcement-bias caveat, timestamp-trust verdict, severity taxonomy, top hotspots (with map screenshot), space-time + cross-dim insights, the divergence (high-impact-low-volume) finding, and an explicit **"signals validated for the future impact score"** section + **"signals NOT to trust"** section.
- [ ] **Step 2: Self-review** the report against FINDINGS.md — every gate decision represented, no placeholder, no unsupported claim.
- [ ] **Step 3: Commit** — `git add eda/findings/EDA_REPORT.md && git commit -m "docs(eda): executive findings report"`

---

## Self-Review (run after drafting; fix inline)

**Spec coverage vs agreed EDA scope (2.1–2.5 + plumbing + dynamic gates):**
- 2.1 Data quality → Phase 0 + Phase 1 ✅
- 2.2 Univariate → Phase 2 ✅
- 2.3 Temporal + timestamp investigation → Phase 3 (Gate 3 = decided, not assumed) ✅
- 2.4 Spatial hotspots → Phase 4 (+ bias-normalisation branch) ✅
- 2.5 Cross-dimensional → Phase 5 ✅
- "Hidden patterns / insights / know it in-and-out" → Phase 6 + Phase 7 ✅
- "Dynamic based on findings" → Decision Gates 0,1A,1B,2,3,4,6 with concrete triggers + `[SPAWNED]` tasks ✅
- Resumability across token expiry → `raw.parquet` + `cleaned.parquet` checkpoints ✅

**Placeholder scan:** No "TBD"/"handle later". Severity taxonomy and offence map are concrete; the one intentionally-empty spot is `code2label`/`unmapped`, which is *computed at runtime* and guarded — not a placeholder.

**Type consistency:** Artifact paths consistent (`/kaggle/working/derived/*.parquet`, `eda_out/*.png`); `id` is the join key everywhere; `max_sev`/`sev_sum` names stable across 22→41→50→63; cluster key `cluster` consistent 41→42→51.

**Ambiguity check:** Grid resolution fixed (round to 3 dp ≈ 110 m); DBSCAN eps fixed (150 m); time convention fixed (IST) with trust verdict gated. Duplicate key explicitly defined.
