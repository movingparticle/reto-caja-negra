#!/usr/bin/env python3
"""
Sonda dedicada de X-Req (Paso 5/6) — determina la semántica exacta del contador
de cabecera X-Req en el oráculo y en el reemplazo.

Preguntas que responde:
  Q1. ¿`POST /__reset` resetea X-Req?
  Q2. ¿`POST /__reset` consume un número de X-Req?
  Q3. ¿X-Req incrementa en errores E100/E101/E102/E201/E202/E301/E302/E303/E401?
  Q4. ¿X-Req incrementa en 401 (no autorizado) y 404 (ruta desconocida)?
  Q5. ¿X-Req es continuo entre /msg y otras rutas?

Uso: python tools/probe_xreq.py [--base URL] [--token TOKEN]
"""

import argparse
import json
import os
import urllib.error
import urllib.request

TOKEN = os.environ.get("TEAM_TOKEN", "REDACTED_TEAM_TOKEN")
UA = "Mozilla/5.0 Frontier-XReq-Probe/1.0"


def calc_control(payload):
    rem = 0
    for c in payload.upper():
        code = ord(c)
        if 65 <= code <= 90:
            val = code - 64
            rem = (rem * 100 + val) % 97 if val >= 10 else (rem * 10 + val) % 97
        elif 48 <= code <= 57:
            rem = (rem * 10 + (code - 48)) % 97
    return 98 - (rem * 3) % 97


def msg(p):
    return f"{p};{calc_control(p)}"


def call(base, method, path, body=None, token=TOKEN, raw_body=None):
    headers = {"User-Agent": UA}
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    headers["Content-Type"] = "application/json"
    data = None
    if raw_body is not None:
        data = raw_body.encode("utf-8") if isinstance(raw_body, str) else raw_body
    elif body is not None:
        data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(f"{base}{path}", data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=20) as res:
            return res.status, res.headers.get("X-Req")
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get("X-Req") if e.headers else None
    except Exception as e:  # noqa: BLE001
        return None, f"ERR:{type(e).__name__}"


def run(base, label):
    print(f"\n=== {label} :: {base} ===")

    # Q1/Q2: reset y su efecto
    call(base, "POST", "/__reset", body={})
    s1, x1 = call(base, "POST", "/msg", body={"m": msg("PING")})
    call(base, "POST", "/__reset", body={})
    s2, x2 = call(base, "POST", "/msg", body={"m": msg("PING")})
    print(f"Q1/Q2 reset->PING xreq: {x1} then {x2}  "
          f"({'reset RESETEA' if x1 == x2 else 'reset NO resetea (delta=' + str((int(x2) - int(x1)) if _int(x1) and _int(x2) else '?') + ')'})")

    # Q2b: ¿reset devuelve X-Req?
    call(base, "POST", "/__reset", body={})
    s, xr = call(base, "POST", "/__reset", body={})
    print(f"Q2b /__reset devuelve X-Req = {xr} (status {s})")

    # Q3: errores de negocio consumen X-Req
    call(base, "POST", "/__reset", body={})
    seq = [
        ("E100", {"raw": "not json"}),
        ("E102", {"body": {"other": 1}}),
        ("E103", {"body": {"m": "ALTA"}}),
        ("E104", {"body": {"m": "ALTA;;82"}}),
        ("E201", {"body": {"m": "ALTA;x;5X"}}),
        ("E202", {"body": {"m": "ALTA;x;99"}}),
        ("E301", {"body": {"m": msg("FOO;1")}}),
        ("E302", {"body": {"m": msg("ALTA")}}),
        ("E303", {"body": {"m": msg("DEPOSITO;AC-0001;0")}}),
        ("E401", {"body": {"m": msg("CONSULTA;AC-9999")}}),
    ]
    print("Q3 X-Req por error:")
    for code, spec in seq:
        if "raw" in spec:
            s, x = call(base, "POST", "/msg", raw_body=spec["raw"])
        else:
            s, x = call(base, "POST", "/msg", body=spec["body"])
        print(f"   {code:5s} -> status {s}  X-Req {x}")

    # Q4: 401 y 404
    s, x = call(base, "POST", "/msg", body={"m": msg("PING")}, token=None)
    print(f"Q4 401 no-auth  -> status {s}  X-Req {x}")
    s, x = call(base, "GET", "/nope")
    print(f"Q4 404 ruta     -> status {s}  X-Req {x}")

    # Q5: OPTIONS y query
    s, x = call(base, "OPTIONS", "/msg", token=None)
    print(f"Q5 OPTIONS /msg -> status {s}  X-Req {x}")
    s, x = call(base, "GET", f"/health?token={TOKEN}", token=None)
    print(f"Q5 GET /health?token= -> status {s}  X-Req {x}")


def _int(v):
    try:
        int(v)
        return True
    except (TypeError, ValueError):
        return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="https://caja-negra-production-c64f.up.railway.app")
    ap.add_argument("--label", default="oráculo")
    args = ap.parse_args()
    run(args.base, args.label)


if __name__ == "__main__":
    main()
