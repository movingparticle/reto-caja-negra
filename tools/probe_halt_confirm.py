#!/usr/bin/env python3
"""Descubre el mecanismo de confirmación de HALT (E520)."""
import json
import urllib.error
import urllib.request

TOKEN = "REDACTED_TEAM_TOKEN"
BASE = "https://caja-negra-production-c64f.up.railway.app"
UA = "Mozilla/5.0 Frontier-HALT-Confirm/1.0"


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


def raw(body, headers=None, path="/msg", method="POST"):
    h = {"User-Agent": UA, "Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}
    if headers:
        h.update(headers)
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(f"{BASE}{path}", data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        txt = e.read().decode()
        try:
            return e.code, json.loads(txt)
        except json.JSONDecodeError:
            return e.code, txt


def health():
    st, b = raw(None, path="/health", method="GET")
    return f"{st} {b}"


def m(p):
    return f"{p};{cc(p)}"


def trial(label, body=None, headers=None, path="/msg", method="POST"):
    st, r = raw(body, headers, path, method)
    print(f"{label:55s} -> {st} {json.dumps(r, ensure_ascii=False)}")
    return st, r


print("health antes:", health())
print()

# 1. Campos extra en el JSON
for field in ["confirm", "confirma", "confirmar", "confirmacion", "si", "yes", "force", "token", "ack"]:
    trial(f'body extra {{"{field}":true}}', {"m": m("HALT;AC-0001"), field: True})

# 2. Argumento mágico
for arg in ["CONFIRMA", "CONFIRMAR", "SI", "YES", "CONFIRM", "OK", "1", "TRUE", "ACK"]:
    trial(f'HALT;{arg}', {"m": m(f"HALT;{arg}")})

# 3. Comandos alternativos
for cmd in ["CONFIRMA", "CONFIRM", "CONFIRMAR", "ACK", "HALTCONFIRM", "HALT2"]:
    trial(f'{cmd};AC-0001', {"m": m(f"{cmd};AC-0001")})

# 4. Headers de confirmación
for hk in ["X-Confirm", "Confirm", "X-Confirmation", "Confirmation"]:
    trial(f'header {hk}: true', {"m": m("HALT;AC-0001")}, {hk: "true"})

# 5. Reinicio y verificación
raw({}, path="/__reset")
print()
print("health despues:", health())
