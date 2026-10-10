#!/usr/bin/env python3
"""Caracteriza el comportamiento ACTUAL del oráculo tras el cambio (incidente)."""
import json
import urllib.error
import urllib.request

TOKEN = "REDACTED_TEAM_TOKEN"
BASE = "https://caja-negra-production-c64f.up.railway.app"
UA = "Mozilla/5.0 Frontier-Incident/1.0"


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


def show(label, p):
    st, r = call("/msg", {"m": m(p)})
    print(f"  {label:38s} -> {st} {json.dumps(r, ensure_ascii=False)!r}")


call("/__reset", {})
print("=== Saldos y formato ===")
show("ALTA;A", "ALTA;A")
show("ALTA;B", "ALTA;B")
show("DEPOSITO;AC-0001;500", "DEPOSITO;AC-0001;500")
show("CONSULTA;AC-0001", "CONSULTA;AC-0001")
show("DEPOSITO;AC-0001;1", "DEPOSITO;AC-0001;1")
show("CONSULTA;AC-0001", "CONSULTA;AC-0001")
show("DEPOSITO;AC-0001;99", "DEPOSITO;AC-0001;99")
show("CONSULTA;AC-0001", "CONSULTA;AC-0001")
show("DEPOSITO;AC-0001;100000", "DEPOSITO;AC-0001;100000")
show("CONSULTA;AC-0001", "CONSULTA;AC-0001")

print("\n=== Límite de transferencia ===")
call("/__reset", {})
call("/msg", {"m": m("ALTA;A")})
call("/msg", {"m": m("ALTA;B")})
call("/msg", {"m": m("DEPOSITO;AC-0001;9000000000")})
for amt in [10000, 10001, 100000, 100001, 1000000, 10000000, 100000000, 999999999, 1000000000]:
    show(f"TRANSFER {amt}", f"TRANSFER;AC-0001;AC-0002;{amt}")

print("\n=== Saldo insuficiente / iguales / inexistente ===")
show("TRANSFER 9999999990 (casi todo)", "TRANSFER;AC-0001;AC-0002;9999999990")
show("CONSULTA;AC-0001", "CONSULTA;AC-0001")
show("TRANSFER iguales", "TRANSFER;AC-0001;AC-0001;1")
show("TRANSFER inexistente", "TRANSFER;AC-9999;AC-0001;1")

print("\n=== E100 / E202 / E104 mensajes (repr) ===")
call("/__reset", {})
st, r = call("/msg", b"not json") if False else (None, None)
# malformed body
req = urllib.request.Request(f"{BASE}/msg", data=b"not json",
                             headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json", "User-Agent": UA}, method="POST")
try:
    with urllib.request.urlopen(req, timeout=15) as x:
        print("  E100 repr:", repr(x.read().decode()))
except urllib.error.HTTPError as e:
    print("  E100 repr:", repr(e.read().decode()))
show("E202", "ALTA;A;99")
show("E104", "ALTA;;1")
