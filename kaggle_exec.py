#!/usr/bin/env python3
"""Minimal driver for a remote Jupyter (Kaggle) kernel over its websocket channel.

Usage:
    python kaggle_exec.py <code-file-or-`-`-for-stdin>

Reads the proxy base URL from KAGGLE_URL env var (or .kaggle_url file).
Sends one execute_request to the running python3 kernel and prints all
stdout/stderr/results/errors until the kernel returns to idle.
"""
import json, os, sys, uuid, ssl
import requests
import websocket  # websocket-client


def base_url():
    u = os.environ.get("KAGGLE_URL")
    if not u and os.path.exists(".kaggle_url"):
        u = open(".kaggle_url").read().strip()
    if not u:
        sys.exit("Set KAGGLE_URL env var or create .kaggle_url file")
    return u.rstrip("/")


def get_kernel_id(http):
    r = requests.get(f"{http}/api/kernels", timeout=20)
    r.raise_for_status()
    kernels = r.json()
    if not kernels:
        sys.exit("No running kernel found on the server")
    return kernels[0]["id"]


def run(code, timeout=300):
    http = base_url()
    kid = get_kernel_id(http)
    ws_url = http.replace("https://", "wss://").replace("http://", "ws://")
    ws = websocket.create_connection(
        f"{ws_url}/api/kernels/{kid}/channels",
        sslopt={"cert_reqs": ssl.CERT_NONE},
        timeout=timeout,
    )
    msg_id = uuid.uuid4().hex
    hdr = {"msg_id": msg_id, "username": "claude", "session": uuid.uuid4().hex,
           "msg_type": "execute_request", "version": "5.3"}
    ws.send(json.dumps({
        "header": hdr, "parent_header": {}, "metadata": {},
        "channel": "shell",
        "content": {"code": code, "silent": False, "store_history": True,
                    "user_expressions": {}, "allow_stdin": False, "stop_on_error": True},
    }))
    out = []
    while True:
        msg = json.loads(ws.recv())
        parent = msg.get("parent_header", {}).get("msg_id")
        if parent != msg_id:
            continue
        mt = msg["msg_type"]
        c = msg["content"]
        if mt == "stream":
            out.append(c.get("text", ""))
            print(c.get("text", ""), end="")
        elif mt in ("execute_result", "display_data"):
            txt = c.get("data", {}).get("text/plain", "")
            out.append(txt)
            print(txt)
        elif mt == "error":
            tb = "\n".join(c.get("traceback", []))
            out.append(tb)
            print(tb)
        elif mt == "status" and c.get("execution_state") == "idle":
            break
    ws.close()
    return "".join(out)


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else "-"
    code = sys.stdin.read() if src == "-" else open(src).read()
    run(code)
