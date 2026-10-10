#!/usr/bin/env python3
"""Verifica la réplica desplegada contra la suite capturada del oráculo."""
import json
import os
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, r"C:\Users\usuario\Desktop\hackthon lab10")
from _tokens import TEAM_TOKEN  # noqa: E402

REPLICA = "https://caja-negra-reemplazo.parsec-ai-labs.workers.dev"
SUITE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "demo-suite.json")
UA = "Frontier-Verify/1.0"


def send(step):
    headers = {"User-Agent": UA}
    headers.update(step.get("headers", {}))
    if "auth" in step and not step.get("headers"):
        a = step["auth"]
        if a == "team":
            headers["Authorization"] = "Bearer " + TEAM_TOKEN
        elif a == "invalid":
            headers["Authorization"] = "Bearer invalid_token_99999999999999999"
    data = None
    if "raw" in step:
        data = step["raw"].encode("utf-8")
        headers.setdefault("Content-Type", "application/json")
    elif step.get("body") is not None:
        data = json.dumps(step["body"]).encode("utf-8")
        headers.setdefault("Content-Type", "application/json")
    elif "m" in step:
        data = json.dumps({"m": step["m"]}).encode("utf-8")
        headers.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(REPLICA + step["path"], data=data, headers=headers, method=step["method"])
    try:
        with urllib.request.urlopen(req, timeout=25) as res:
            return res.status, json.loads(res.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        try:
            return e.code, json.loads(body)
        except ValueError:
            return e.code, body


def canon(v):
    return json.dumps(v, sort_keys=True, ensure_ascii=False)


def main():
    tests = json.load(open(SUITE, encoding="utf-8"))
    fails = []
    for t in tests:
        send({"method": "POST", "path": "/__reset", "body": {}, "auth": "team"})
        for i, s in enumerate(t["steps"], 1):
            st, body = send(s)
            if st != s["expStatus"] or canon(body) != canon(s["expBody"]):
                fails.append((t["id"], i, st, s["expStatus"], body, s["expBody"]))
                break
        time.sleep(0.05)
    print(f"tests={len(tests)} fails={len(fails)}")
    for f in fails:
        print(f"  FAIL {f[0]} paso {f[1]}: got {f[2]} {f[4]} | exp {f[3]} {f[5]}")


if __name__ == "__main__":
    main()
