#!/usr/bin/env python3
"""Caracteriza limpiamente el protocolo de HALT y el estado 'service halted'."""
import json
import time
import urllib.error
import urllib.request

TOKEN = "REDACTED_TEAM_TOKEN"
BASE = "https://caja-negra-production-c64f.up.railway.app"
UA = "Mozilla/5.0 Frontier-HALT-Clean/1.0"


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


def call(path, body=None, method="POST", show=True):
    h = {"User-Agent": UA, "Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}
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
        print(f"    {method} {path} {json.dumps(body) if body else ''} -> {st} xreq={xr} {txt}")
    return st, txt, xr


def m(p):
    return f"{p};{cc(p)}"


def reset():
    call("/__reset", {})


def scenario(title, *msgs):
    print(f"\n--- {title} ---")
    reset()
    for p in msgs:
        call("/msg", {"m": m(p)})


scenario("1) HALT;1 directo (reset fresco)", "HALT;1", "PING")
scenario("2) HALT;0", "HALT;0", "PING")
scenario("3) HALT;2", "HALT;2", "PING")
scenario("4) dos pasos: HALT;AC-0001 luego HALT;1", "HALT;AC-0001", "HALT;1", "PING")
scenario("5) HALT;SI", "HALT;SI", "PING")
scenario("6) HALT;X + HALT;X (repetido)", "HALT;X", "HALT;X", "PING")
scenario("7) HALT;1 y consulta estado tras halt", "HALT;1", "CONSULTA;AC-0001", "ALTA;A")

# Estado tras halt sin reset
print("\n--- 8) secuencia halt + errores + reset ---")
reset()
call("/msg", {"m": m("PING")})
call("/msg", {"m": m("HALT;1")})
call("/msg", {"m": m("PING")})
call("/msg", {"m": m("FOO;1")})
call("/msg", {"m": "not json"})
print("  ahora reset:")
reset()
call("/msg", {"m": m("PING")})
