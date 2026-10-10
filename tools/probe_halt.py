#!/usr/bin/env python3
"""Caracteriza el comando oculto HALT."""
import json
import urllib.error
import urllib.request

TOKEN = "REDACTED_TEAM_TOKEN"
BASE = "https://caja-negra-production-c64f.up.railway.app"
UA = "Mozilla/5.0 Frontier-HALT-Probe/1.0"


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


def call(path, body=None, method="POST", token=TOKEN):
    headers = {"User-Agent": UA}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    headers["Content-Type"] = "application/json"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(f"{BASE}{path}", data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        txt = e.read().decode()
        try:
            return e.code, json.loads(txt)
        except json.JSONDecodeError:
            return e.code, txt


def send(payload):
    return call("/msg", {"m": f"{payload};{cc(payload)}"})


print("=== Aridad de HALT ===")
for p in ["HALT", "HALT;X", "HALT;X;Y", "HALT;X;Y;Z", "HALT;X;Y;Z;W"]:
    st, r = send(p)
    print(f"{p:20s} -> {st} {json.dumps(r, ensure_ascii=False)}")

print("\n=== Efecto de HALT (reset + estado) ===")
call("/__reset", {})
print("ALTA A:", send("ALTA;A"))
print("ALTA B:", send("ALTA;B"))
print("DEPOSITO AC-0001 500:", send("DEPOSITO;AC-0001;500"))
print("CONSULTA AC-0001:", send("CONSULTA;AC-0001"))
print("HALT;AC-0001:", send("HALT;AC-0001"))
print("CONSULTA AC-0001 tras HALT:", send("CONSULTA;AC-0001"))
print("DEPOSITO AC-0001 100 tras HALT:", send("DEPOSITO;AC-0001;100"))
print("TRANSFER AC-0001->AC-0002 100 tras HALT:", send("TRANSFER;AC-0001;AC-0002;100"))
print("HALT;AC-0001 (2a vez):", send("HALT;AC-0001"))
print("HALT;AC-9999:", send("HALT;AC-9999"))
print("HALT;op-0001:", send("HALT;op-0001"))
print("HALT;OP-0001:", send("HALT;OP-0001"))
print("CONSULTA AC-0002:", send("CONSULTA;AC-0002"))
