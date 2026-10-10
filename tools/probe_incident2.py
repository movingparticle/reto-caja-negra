#!/usr/bin/env python3
"""Caracteriza el incidente: límite de transferencia, E506 y E510 (cuenta bloqueada)."""
import json
import urllib.error
import urllib.request

TOKEN = "REDACTED_TEAM_TOKEN"
BASE = "https://caja-negra-production-c64f.up.railway.app"
UA = "Mozilla/5.0 Frontier-Incident2/1.0"


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


def call(path, body=None, method="POST"):
    h = {"User-Agent": UA, "Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}
    d = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(f"{BASE}{path}", data=d, headers=h, method=method)
    try:
        with urllib.request.urlopen(r, timeout=15) as x:
            return x.status, json.loads(x.read().decode())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode())
        except Exception:
            return e.code, e.read().decode()


def m(p):
    return f"{p};{cc(p)}"


def s(p):
    st, r = call("/msg", {"m": m(p)})
    return st, r


print("=== Formato de saldo (centavos -> decimal) ===")
call("/__reset", {})
s("ALTA;A")
for amt in [1, 9, 10, 99, 100, 101, 12345, 1000000000]:
    s(f"DEPOSITO;AC-0001;{amt}")
    st, r = s("CONSULTA;AC-0001")
    print(f"  +{amt:<12} -> {r}")

print("\n=== Límite exacto de transferencia ===")
call("/__reset", {})
s("ALTA;A"); s("ALTA;B")
s("DEPOSITO;AC-0001;9000000000")
for amt in [10000, 10001, 11000, 20000, 50000, 99999, 100000]:
    call("/__reset", {}); s("ALTA;A"); s("ALTA;B"); s("DEPOSITO;AC-0001;9000000000")
    st, r = s(f"TRANSFER;AC-0001;AC-0002;{amt}")
    print(f"  TRANSFER {amt:<8} -> {st} {r}")

print("\n=== Regla E510 (intentos) tras fallos consecutivos ===")
call("/__reset", {})
s("ALTA;A"); s("ALTA;B")
s("DEPOSITO;AC-0001;9000000000")
for i in range(1, 9):
    st, r = s("TRANSFER;AC-0001;AC-0002;999999999")
    print(f"  intento {i}: {st} {r}")

print("\n=== ¿Un éxito resetea los intentos? ===")
call("/__reset", {})
s("ALTA;A"); s("ALTA;B")
s("DEPOSITO;AC-0001;9000000000")
for i in range(1, 4):
    st, r = s("TRANSFER;AC-0001;AC-0002;999999999")
    print(f"  fallo {i}: {st} {r}")
st, r = s("TRANSFER;AC-0001;AC-0002;100")
print(f"  exito pequeño: {st} {r}")
for i in range(1, 4):
    st, r = s("TRANSFER;AC-0001;AC-0002;999999999")
    print(f"  fallo post-exito {i}: {st} {r}")
