#!/usr/bin/env python3
"""Assemble fe/cells/*.py into a reproducible Kaggle notebook gridlock_fe.ipynb.
Prereq cells: gridlock_eda.ipynb must have produced cleaned.parquet + derived/severity.parquet."""
import nbformat as nbf, glob, os

scorelib_src = open("fe/scorelib.py").read()
SETUP = ('import os, subprocess, sys\n'
         'subprocess.run([sys.executable,"-m","pip","install","-q","pygeohash"],check=True)\n'
         'os.makedirs("/kaggle/working/derived",exist_ok=True)\n'
         'os.makedirs("/kaggle/working/fe_out",exist_ok=True)\n'
         '# write scorelib.py so cells can import it\n'
         'open("/kaggle/working/scorelib.py","w").write(' + repr(scorelib_src) + ')\n'
         'print("setup done")')

INTRO = ("# GridLock — Congestion-Impact Score & Models\n\n"
         "**Prerequisite:** run `gridlock_eda.ipynb` first (produces `cleaned.parquet` and "
         "`derived/severity.parquet` in `/kaggle/working`).\n\n"
         "Pipeline: prepare → features (+EB smoothing) → spatial-lag/KDE → Getis-Ord Gi* → PCA → "
         "ensemble impact score (β=0.75) → validation → outputs → supervised impact model → "
         "hotspot-detection classifier. See `fe/findings/FE_REPORT.md` and `fe/findings/MODEL_CARD.md`.")

nb = nbf.v4.new_notebook()
cells = [nbf.v4.new_markdown_cell(INTRO), nbf.v4.new_code_cell(SETUP)]
for fp in sorted(glob.glob("fe/cells/*.py")):
    cells.append(nbf.v4.new_markdown_cell(f"## `{os.path.basename(fp)}`"))
    cells.append(nbf.v4.new_code_cell(open(fp).read()))
nb["cells"] = cells
nbf.write(nb, "gridlock_fe.ipynb")
print(f"wrote gridlock_fe.ipynb with {len(cells)} cells ({len(glob.glob('fe/cells/*.py'))} analysis cells)")
