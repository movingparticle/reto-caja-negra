#!/usr/bin/env python3
"""Precedencia del estado 'service halted' y del 409 E520."""
import json
import urllib.error
import urllib.request

TOKEN = "REDACTED_TEAM_TOKEN"
BASE = "https://caja-negra-production-c64f.up.railway.app"
UA = "Mozilla/5.0 Frontier-Halt-State/1.0"


def cc(p):
    rem = 0
    for c in p.upper():
        o = ord(c)
        if 65 <= o <= 90:
            v = o - 64
            rem = (rem * 100 + v) % 97 if v >= 10 else (rem * 10 + v) % 97
        elif 48 <= o <= 57:
            rem = (rem * 10 + (o - 48)) % 97
    return 98 - (rem * 3) % 97


def call(path, body=None, method="POST", token=TOKEN, raw=None, show=True, label=""):
    h = {"User-Agent": UA, "Content-Type": "application/json"}
    if token:
        h["Authorization"] = f"Bearer {token}"
    if raw is not None:
        d = raw.encode() if isinstance(raw, str) else raw
    else:
        d = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(f"{BASE}{path}", data=d, headers=h, method=method)
    try:
        with urllib.request.urlopen(r, timeout=15) as x:
            st, txt, xr = x.status, x.read().decode(), x.headers.get("X-Req")
    except urllib.error.HTTPError as e:
        st, txt, xr = e.code, e.read().decode(), e.headers.get("X-Req") if e.headers else None
    except Exception as e:  # noqa: BLE001
        st, txt, xr = None, str(e), None
    if show:
        print(f"  {label:42s} -> {st} xreq={xr} {txt[:80]}")
    return st, txt, xr


def m(p):
    return f"{p};{cc(p)}"


def reset():
    call("/__reset", {})


print("=== Estado normal: precedencia del 409 E520 ===")
reset()
call("/msg", {"m": m("HALT;1") + ""}, label="no-op")  # placeholder
reset()
call("/msg", {"m": m("HALT;AC-0001")}, label="HALT;AC-0001 (409)")
call("/msg", {"m": m("CONSULTA;AC-0001")}, label="CONSULTA tras 409 (no halt)")

print("\n=== Entrar en halt y probar precedencia ===")
reset()
call("/msg", {"m": m("HALT;1")}, label="HALT;1 (halt)")
call("/msg", {"m": m("PING")}, label="PING durante halt")
call("/msg", raw="not-json", label="body malformado durante halt")
call("/msg", raw="", label="body vacio durante halt")
call("/msg", raw="x" * 9000, label="body >8KiB durante halt")
call("/msg", {"m": m("PING")}, token=None, label="sin auth durante halt")
call("/msg", {"m": m("PING")}, token="wrong", label="token malo durante halt")
call("/unknown", method="GET", label="ruta desconocida durante halt")
call("/health", method="GET", label="health durante halt")
call("/msg", method="GET", label="GET /msg durante halt")
call("/msg", method="OPTIONS", token=None, label="OPTIONS /msg durante halt")

print("\n=== Recuperacion ===")
reset()
call("/msg", {"m": m("PING")}, label="PING tras reset")
