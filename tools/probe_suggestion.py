#!/usr/bin/env python3
"""
Sonda del campo `sugerencia` en E301 (comando desconocido) — oráculo.
Caracteriza cuándo el oráculo sugiere un comando cercano y cuál.
"""
import json
import urllib.error
import urllib.request

TOKEN = "REDACTED_TEAM_TOKEN"
URL = "https://caja-negra-production-c64f.up.railway.app/msg"
UA = "Mozilla/5.0 Frontier-Suggestion-Probe/1.0"


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


def send(payload):
    body = json.dumps({"m": f"{payload};{cc(payload)}"}).encode()
    req = urllib.request.Request(URL, data=body, headers={
        "Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json", "User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())


CANDIDATES = [
    "ALTA", "ALTA;A", "ALTAX;A", "ALT;A", "ALTA A", "ALTA;", " ALTA;A", "ALTA ;A",
    "A;A", "AL;A", "ALTAA;A", "ALTE;A", "ALTO;A", "ALTA1;A", "aLtA;A", "ALTA_;A",
    "CONSULTA;AC-0001", "CONSULT;AC-0001", "CONSULTAA;AC-0001", "CONSULTAR;AC-0001",
    "CONSU;AC-0001", "CONSULTAX;AC-0001", "CONSULTA ;AC-0001", "CONSULTA;A",
    "PING", "PING;x", "PINGG;1", "PIN;1", "PINGX;1", "PNG;1",
    "DEPOSITO;AC-0001;10", "DEPOSIT;AC-0001;10", "DEPOSITO;AC-0001;10",
    "DEPOSITOX;AC-0001;10", "DEPOSITAR;AC-0001;10", "DEPO;AC-0001;10",
    "TRANSFER;AC-0001;AC-0002;10", "TRANSFERIR;AC-0001;AC-0002;10",
    "TRANSFERS;AC-0001;AC-0002;10", "TRANSFE;AC-0001;AC-0002;10",
    "ANULA;OP-0001", "ANULAR;OP-0001", "ANUL;OP-0001", "ANULAX;OP-0001",
    "SALDOS;AC-0001", "RETIRO;AC-0001", "FOO;1", "XYZ;1", "CONSULTA2;A",
    "consulta;ac-0001", "Consulta;AC-0001", "PING2", "pingg;1",
]

print(f"{'PAYLOAD':40s} {'ST':4s} {'RESPONSE'}")
print("-" * 100)
for p in CANDIDATES:
    st, body = send(p)
    sug = body.get("sugerencia") if isinstance(body, dict) else None
    mark = f"  >>> SUGERENCIA={sug!r}" if sug is not None else ""
    print(f"{p:40s} {st:<4} {json.dumps(body, ensure_ascii=False)}{mark}")
