#!/usr/bin/env python3
"""
Captura el fixture post-incidente reenviando los 20 requests de
pruebas/ejemplos.jsonl al oráculo ACTUAL y guardando las respuestas reales.

Salida: pruebas/ejemplos_post_incidente.jsonl
"""
import json
import os
import urllib.error
import urllib.request

TOKEN = os.environ.get("TEAM_TOKEN", "REDACTED_TEAM_TOKEN")
BASE = os.environ.get("ORACLE_URL", "https://caja-negra-production-c64f.up.railway.app")
UA = "Mozilla/5.0 Frontier-Fixture/1.0"
SRC = "pruebas/ejemplos.jsonl"
OUT = "pruebas/ejemplos_post_incidente.jsonl"


def call(path, body=None, method="POST"):
    h = {"User-Agent": UA, "Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}
    d = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(f"{BASE}{path}", data=d, headers=h, method=method)
    try:
        with urllib.request.urlopen(r, timeout=20) as x:
            return x.status, json.loads(x.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())


def main():
    call("/__reset", {})
    lines = [l for l in open(SRC, encoding="utf-8").read().splitlines() if l.strip()]
    out = []
    for i, line in enumerate(lines, 1):
        exp = json.loads(line)
        req = exp["request"]
        st, resp = call("/msg", req)
        rec = {"n": i, "id": exp.get("id", i), "seq": "post_incidente",
               "request": req, "status": st, "response": resp}
        out.append(rec)
        print(f"  {i:2d} {json.dumps(req)[:40]:42s} -> {st} {json.dumps(resp, ensure_ascii=False)}")
    with open(OUT, "w", encoding="utf-8") as f:
        for r in out:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"\nEscrito {OUT} ({len(out)} casos)")


if __name__ == "__main__":
    main()
