import os, json
from api.artifacts import build_static
def test_build_static_writes_manifest(tmp_path, mini_scores):
    out=str(tmp_path/"data")
    man=build_static(scores_parquet=mini_scores, fe_out="fe_work/fe_out", out_dir=out)
    assert os.path.exists(os.path.join(out,"manifest.json"))
    assert os.path.exists(os.path.join(out,"priority_table.json"))
    m=json.load(open(os.path.join(out,"manifest.json")))
    assert m["artifacts_version"] and isinstance(m["files"],list) and m["headline_stats"]["zones"]>0
    assert all("sha256" in f and "bytes" in f for f in m["files"])
