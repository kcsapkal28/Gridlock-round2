#!/usr/bin/env python3
"""Local executor for the EDA/FE cells when the remote Kaggle kernel is unavailable.
Rewrites the hardcoded /kaggle paths to a local working dir + the local CSV, then
execs each given cell file in-process. Usage: python run_local.py <cell.py> [<cell.py> ...]"""
import sys, os, shutil

WORK = os.path.abspath("fe_work")
os.makedirs(WORK + "/derived", exist_ok=True)
os.makedirs(WORK + "/fe_out", exist_ok=True)
CSV = os.path.abspath("jan to may police violation_anonymized791b166.csv")
KAGGLE_CSV = ("/kaggle/input/datasets/kartikeysapkal/gridlock-round2-csv/"
              "jan to may police violation_anonymized791b166.csv")

def run(path):
    shutil.copy("fe/scorelib.py", WORK + "/scorelib.py")  # keep scorelib fresh in WORK
    src = open(path).read().replace(KAGGLE_CSV, CSV).replace("/kaggle/working", WORK)
    print(f"\n===== RUN {path} =====")
    exec(compile(src, path, "exec"), {"__name__": "__cellrun__"})

if __name__ == "__main__":
    for c in sys.argv[1:]:
        run(c)
