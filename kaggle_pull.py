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
