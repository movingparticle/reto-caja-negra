#!/usr/bin/env python3
"""Incidente - parte 3: límite exacto, contador de fallos, alcance del bloqueo."""
import json
import urllib.error
import urllib.request

TOKEN = "REDACTED_TEAM_TOKEN"
BASE = "https://caja-negra-production-c64f.up.railway.app"
UA = "Mozilla/5.0 Frontier-Incident3/1.0"


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
    return call("/msg", {"m": m(p)})


def fresh(bal=9000000000):
    call("/__reset", {})
    s("ALTA;A"); s("ALTA;B")
    if bal:
        s(f"DEPOSITO;AC-0001;{bal}")


print("=== Límite exacto (sweep) ===")
for amt in [50001, 60000, 70000, 80000, 90000, 95000, 99000, 99998, 99999]:
    fresh()
    st, r = s(f"TRANSFER;AC-0001;AC-0002;{amt}")
    print(f"  {amt:<8} -> {st} {r.get('error','OK')}")

print("\n=== ¿Qué cuenta como fallo? (3 fallos -> bloqueo) ===")
# a) E507 saldo insuficiente x3
fresh(bal=10)
for i in range(1, 5):
    st, r = s("TRANSFER;AC-0001;AC-0002;9999")
    print(f"  E507 x{i}: {st} {r}")
# b) E401 cuenta inexistente x3
fresh()
for i in range(1, 5):
    st, r = s("TRANSFER;AC-9999;AC-0002;9999")
    print(f"  E401 x{i}: {st} {r}")
# c) E304 iguales x3
fresh()
for i in range(1, 5):
    st, r = s("TRANSFER;AC-0001;AC-0001;9999")
    print(f"  E304 x{i}: {st} {r}")

print("\n=== ¿Éxito resetea contador? ===")
fresh()
s("TRANSFER;AC-0001;AC-0002;99999")   # fallo 1
s("TRANSFER;AC-0001;AC-0002;99999")   # fallo 2
st, r = s("TRANSFER;AC-0001;AC-0002;100")  # exito
print(f"  exito: {st} {r}")
for i in range(1, 4):
    st, r = s("TRANSFER;AC-0001;AC-0002;99999")
    print(f"  fallo post-exito {i}: {st} {r}")

print("\n=== Alcance del bloqueo (origen bloqueado) ===")
fresh()
for i in range(4):
    s("TRANSFER;AC-0001;AC-0002;99999")   # bloquear AC-0001
print("  DEPOSITO AC-0001:", s("DEPOSITO;AC-0001;100"))
print("  CONSULTA AC-0001:", s("CONSULTA;AC-0001"))
print("  TRANSFER AC-0001->AC-0002:", s("TRANSFER;AC-0001;AC-0002;1"))
print("  TRANSFER AC-0002->AC-0001 (origen sano):", s("TRANSFER;AC-0002;AC-0001;1"))

print("\n=== ¿Reset limpia el bloqueo? ===")
call("/__reset", {})
s("ALTA;A"); s("ALTA;B"); s("DEPOSITO;AC-0001;9000000000")
st, r = s("TRANSFER;AC-0001;AC-0002;100")
print(f"  tras reset: {st} {r}")

print("\n=== Otros errores E508-E519 ===")
fresh()
for probe in ["DEPOSITO;AC-0001;0", "DEPOSITO;AC-0001;10000000000",
              "CONSULTA;AC-9999", "ANULA;OP-9999", "TRANSFER;AC-0001;AC-9999;1"]:
    st, r = s(probe)
    print(f"  {probe:38s} -> {st} {r}")
