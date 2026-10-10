#!/usr/bin/env python3
"""Caracteriza el umbral y la métrica del campo `sugerencia` (E301)."""
import json
import urllib.error
import urllib.request

TOKEN = "REDACTED_TEAM_TOKEN"
URL = "https://caja-negra-production-c64f.up.railway.app/msg"
UA = "Mozilla/5.0 Frontier-Suggestion-Threshold/1.0"
KNOWN = ["PING", "ALTA", "CONSULTA", "DEPOSITO", "TRANSFER", "ANULA"]


def lev(a, b):
    d = [[0] * (len(b) + 1) for _ in range(len(a) + 1)]
    for i in range(len(a) + 1):
        d[i][0] = i
    for j in range(len(b) + 1):
        d[0][j] = j
    for i in range(1, len(a) + 1):
        for j in range(1, len(b) + 1):
            d[i][j] = min(d[i - 1][j] + 1, d[i][j - 1] + 1,
                          d[i - 1][j - 1] + (a[i - 1] != b[j - 1]))
    return d[len(a)][len(b)]


def dam(a, b):
    d = [[0] * (len(b) + 1) for _ in range(len(a) + 1)]
    for i in range(len(a) + 1):
        d[i][0] = i
    for j in range(len(b) + 1):
        d[0][j] = j
    for i in range(1, len(a) + 1):
        for j in range(1, len(b) + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            d[i][j] = min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + cost)
            if i > 1 and j > 1 and a[i - 1] == b[j - 2] and a[i - 2] == b[j - 1]:
                d[i][j] = min(d[i][j], d[i - 2][j - 2] + 1)
    return d[len(a)][len(b)]


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
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return json.loads(e.read().decode())


# Genera variantes conocidas por distancia controlada respecto a ALTA/CONSULTA/PING
TESTS = [
    # (comando a probar, separador extra para que no sea comando válido)
    "ALTAX", "ALTXX", "ALTXXX", "ALTXXXX",       # d1,d2,d3,d4 vs ALTA
    "AL", "A", "ALT",                             # d2,d3,d1
    "CONSUL", "CONSU", "CON",                     # d2,d3,d4 vs CONSULTA
    "PI", "P", "PIN",                             # d2,d3,d1 vs PING
    "ATLA", "ATL", "AALT", "TA",                  # transposiciones
    "DEPOSITOO", "DEPOSITOOO",                    # d1,d2
    "ANULAA", "ANULAAA",                          # d1,d2
    "TRANSFERR", "TRANSFERRR",                    # d1,d2
    "XYZ", "ZZZZZZ",                              # lejanos
]

print(f"{'INPUT':12s} {'>upper':12s} {'sugerencia':12s} {'lev_min':7s} {'dam_min':7s}  closest")
print("-" * 90)
for t in TESTS:
    u = t.upper()
    body = send(t + ";1")
    sug = body.get("sugerencia")
    levs = [(lev(u, k), k) for k in KNOWN]
    dams = [(dam(u, k), k) for k in KNOWN]
    lm = min(levs)
    dm = min(dams)
    print(f"{t:12s} {u:12s} {str(sug):12s} {lm[0]:<7} {dm[0]:<7}  {lm[1]}")
