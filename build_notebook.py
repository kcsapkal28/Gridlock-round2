#!/usr/bin/env python3
"""Assemble eda/cells/*.py (numeric order) into a single reproducible notebook.
Prepends an intro + a setup cell that creates output dirs so it runs on a fresh kernel."""
import nbformat as nbf, glob, os

SETUP = ('import os\n'
         'os.makedirs("/kaggle/working/eda_out", exist_ok=True)\n'
         'os.makedirs("/kaggle/working/derived", exist_ok=True)\n'
         'print("output dirs ready")')

INTRO = ("# GridLock — Parking-Induced Congestion EDA\n\n"
         "Reproducible analysis of the BTP parking-violation dataset.\n"
         "Reads from `/kaggle/input/...`, writes checkpoints to `/kaggle/working`, "
         "charts to `/kaggle/working/eda_out`.\n\n"
         "Cells run top-to-bottom on a fresh kernel: load+integrity → quality → "
         "univariate+severity → temporal → spatial → cross-dim → hidden patterns.\n\n"
         "See `eda/findings/EDA_REPORT.md` for the executive summary.")

nb = nbf.v4.new_notebook()
cells = [nbf.v4.new_markdown_cell(INTRO), nbf.v4.new_code_cell(SETUP)]
for f in sorted(glob.glob("eda/cells/*.py")):
    cells.append(nbf.v4.new_markdown_cell(f"## `{os.path.basename(f)}`"))
    cells.append(nbf.v4.new_code_cell(open(f).read()))
nb["cells"] = cells
nbf.write(nb, "gridlock_eda.ipynb")
print(f"wrote gridlock_eda.ipynb with {len(cells)} cells ({len(glob.glob('eda/cells/*.py'))} analysis cells)")
