#!/usr/bin/env python3
"""Incidente - parte 4: precedencia de E510 y reglas de reseteo del contador."""
import json
import urllib.error
import urllib.request

TOKEN = "REDACTED_TEAM_TOKEN"
BASE = "https://caja-negra-production-c64f.up.railway.app"
UA = "Mozilla/5.0 Frontier-Incident4/1.0"


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


def fresh(bal=9000000000, accts=3):
    call("/__reset", {})
    for i in range(accts):
        s(f"ALTA;C{i}")
    if bal:
        s(f"DEPOSITO;AC-0001;{bal}")


def block_ac(count=4, amt=99999, dest="AC-0002"):
    for _ in range(count):
        s(f"TRANSFER;AC-0001;{dest};{amt}")


print("=== Precedencia en cuenta bloqueada (AC-0001) ===")
fresh()
block_ac(4)  # bloquea AC-0001 (intentos=1)
print("  monto 0 (E303?):", s("TRANSFER;AC-0001;AC-0002;0"))
print("  iguales (E304?):", s("TRANSFER;AC-0001;AC-0001;1"))
print("  dest inexistente (E401?):", s("TRANSFER;AC-0001;AC-9999;1"))
print("  monto > limite (E506?):", s("TRANSFER;AC-0001;AC-0002;99999"))
print("  valido (E510?):", s("TRANSFER;AC-0001;AC-0002;1"))

print("\n=== Limite: 50000 ok, 50001 no ===")
fresh()
print("  50000:", s("TRANSFER;AC-0001;AC-0002;50000"))
fresh()
print("  50001:", s("TRANSFER;AC-0001;AC-0002;50001"))

print("\n=== ¿DEPOSITO resetea el contador? ===")
fresh()
s("TRANSFER;AC-0001;AC-0002;99999")   # fallo 1
s("TRANSFER;AC-0001;AC-0002;99999")   # fallo 2
s("DEPOSITO;AC-0001;1")               # ¿reset?
s("TRANSFER;AC-0001;AC-0002;99999")   # fallo?
s("TRANSFER;AC-0001;AC-0002;99999")   # fallo?
print("  3er fallo post-deposito (si NO resetea -> E510):", s("TRANSFER;AC-0001;AC-0002;99999"))

print("\n=== ¿El contador es por origen o global? ===")
fresh()
s("TRANSFER;AC-0001;AC-0002;99999")   # fallo AC-0001
s("TRANSFER;AC-0001;AC-0002;99999")   # fallo AC-0001
s("TRANSFER;AC-0001;AC-0002;99999")   # fallo AC-0001 -> bloquea AC-0001
print("  AC-0001 (bloqueada):", s("TRANSFER;AC-0001;AC-0002;1"))
print("  AC-0002 (sana):", s("TRANSFER;AC-0002;AC-0001;1"))

print("\n=== ¿CONSULTA de cuenta bloqueada funciona? ===")
fresh()
block_ac(4)
print("  CONSULTA AC-0001:", s("CONSULTA;AC-0001"))
