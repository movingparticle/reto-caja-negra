#!/usr/bin/env python3
"""Sondeo de huecos no cubiertos por la batería de 91. Compara oráculo vs réplica."""
import json
import os
import sys
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# token desde el repo padre
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from _tokens import TEAM_TOKEN  # noqa: E402

ORACLE = os.environ.get("ORACLE_URL", "https://caja-negra-production-c64f.up.railway.app")
REPLICA = os.environ.get("REPLICA_URL", "https://caja-negra-reemplazo.parsec-ai-labs.workers.dev")
UA = "Mozilla/5.0 Frontier-Gap/1.0"


def calc_control(payload: str) -> int:
    rem = 0
    for c in payload.upper():
        code = ord(c)
        if 65 <= code <= 90:
            val = code - 64
            rem = (rem * 100 + val) % 97 if val >= 10 else (rem * 10 + val) % 97
        elif 48 <= code <= 57:
            rem = (rem * 10 + (code - 48)) % 97
    return 98 - (rem * 3) % 97


def msg(payload: str) -> str:
    return f"{payload};{calc_control(payload)}"


def raw(base, method, path, body=None, raw_body=None, token=TEAM_TOKEN):
    headers = {"User-Agent": UA, "Content-Type": "application/json"}
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    data = None
    if raw_body is not None:
        data = raw_body if isinstance(raw_body, bytes) else raw_body.encode("utf-8")
    elif body is not None:
        data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(f"{base}{path}", data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=20) as res:
            text = res.read().decode("utf-8", "replace")
            return res.status, _body(text)
    except urllib.error.HTTPError as e:
        return e.code, _body(e.read().decode("utf-8", "replace"))
    except Exception as e:  # noqa: BLE001
        return None, f"{type(e).__name__}: {e}"


def _body(text):
    try:
        return json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return text


def reset(base):
    return raw(base, "POST", "/__reset", body={})


def post(base, m):
    return raw(base, "POST", "/msg", body={"m": m})


def run_seq(base, steps):
    out = []
    for step in steps:
        kind = step[0]
        if kind == "reset":
            out.append(("reset", reset(base)))
        elif kind == "msg":
            out.append((step[1], post(base, step[1])))
        elif kind == "raw":
            out.append((step[1], raw(base, step[2], step[3], raw_body=step[4], token=step[5] if len(step) > 5 else TEAM_TOKEN)))
        elif kind == "path":
            out.append((step[1], raw(base, step[2], step[3], body=step[4] if len(step) > 4 else None)))
    return out


CASES = []


def add(name, steps):
    CASES.append((name, steps))


# 1. E510 timing: 3 fallos E506, luego un 4to
add("e510_timing", [
    ("reset",),
    ("msg", msg("ALTA;A")),
    ("msg", msg("ALTA;B")),
    ("msg", msg("DEPOSITO;AC-0001;100")),
    ("msg", msg("TRANSFER;AC-0001;AC-0002;50001")),  # fail 1 E506
    ("msg", msg("TRANSFER;AC-0001;AC-0002;50001")),  # fail 2
    ("msg", msg("TRANSFER;AC-0001;AC-0002;50001")),  # fail 3
    ("msg", msg("TRANSFER;AC-0001;AC-0002;50001")),  # 4th
    ("msg", msg("TRANSFER;AC-0001;AC-0002;1")),      # 5th while blocked, valid amount
])

# 2. deposit / consulta / anula while blocked
add("blocked_ops", [
    ("reset",),
    ("msg", msg("ALTA;A")),
    ("msg", msg("ALTA;B")),
    ("msg", msg("DEPOSITO;AC-0001;100")),
    ("msg", msg("TRANSFER;AC-0001;AC-0002;50001")),
    ("msg", msg("TRANSFER;AC-0001;AC-0002;50001")),
    ("msg", msg("TRANSFER;AC-0001;AC-0002;50001")),
    ("msg", msg("CONSULTA;AC-0001")),
    ("msg", msg("DEPOSITO;AC-0001;50")),
    ("msg", msg("CONSULTA;AC-0001")),
    ("msg", msg("TRANSFER;AC-0001;AC-0002;50001")),
])

# 3. consulta between fails
add("consulta_between_fails", [
    ("reset",),
    ("msg", msg("ALTA;A")),
    ("msg", msg("ALTA;B")),
    ("msg", msg("DEPOSITO;AC-0001;100")),
    ("msg", msg("TRANSFER;AC-0001;AC-0002;50001")),
    ("msg", msg("CONSULTA;AC-0001")),
    ("msg", msg("TRANSFER;AC-0001;AC-0002;50001")),
    ("msg", msg("TRANSFER;AC-0001;AC-0002;50001")),
    ("msg", msg("TRANSFER;AC-0001;AC-0002;50001")),
])

# 4. anula between fails (need a real op first)
add("anula_between_fails", [
    ("reset",),
    ("msg", msg("ALTA;A")),
    ("msg", msg("ALTA;B")),
    ("msg", msg("DEPOSITO;AC-0001;1000")),
    ("msg", msg("TRANSFER;AC-0001;AC-0002;50001")),
    ("msg", msg("ANULA;OP-0001")),
    ("msg", msg("TRANSFER;AC-0001;AC-0002;50001")),
    ("msg", msg("TRANSFER;AC-0001;AC-0002;50001")),
    ("msg", msg("TRANSFER;AC-0001;AC-0002;1")),
])

# 5. E507 fails also count
add("e507_counts", [
    ("reset",),
    ("msg", msg("ALTA;A")),
    ("msg", msg("ALTA;B")),
    ("msg", msg("TRANSFER;AC-0001;AC-0002;1")),
    ("msg", msg("TRANSFER;AC-0001;AC-0002;1")),
    ("msg", msg("TRANSFER;AC-0001;AC-0002;1")),
    ("msg", msg("TRANSFER;AC-0001;AC-0002;1")),
])

# 6. success transfer resets fails
add("success_resets", [
    ("reset",),
    ("msg", msg("ALTA;A")),
    ("msg", msg("ALTA;B")),
    ("msg", msg("DEPOSITO;AC-0001;200")),
    ("msg", msg("TRANSFER;AC-0001;AC-0002;50001")),
    ("msg", msg("TRANSFER;AC-0001;AC-0002;50001")),
    ("msg", msg("TRANSFER;AC-0001;AC-0002;100")),  # success
    ("msg", msg("TRANSFER;AC-0001;AC-0002;50001")),
    ("msg", msg("TRANSFER;AC-0001;AC-0002;50001")),
    ("msg", msg("TRANSFER;AC-0001;AC-0002;50001")),
])

# 7. first-request edges
add("halt_variants", [
    ("reset",),
    ("msg", msg("HALT;01")),
    ("msg", msg("HALT;1 ")),
    ("msg", "HALT;1"),  # no checksum? will be control missing or invalid
    ("msg", msg("PING")),
])

add("bad_ids", [
    ("reset",),
    ("msg", msg("ALTA;A")),
    ("msg", msg("CONSULTA;AC-1")),
    ("msg", msg("CONSULTA;AC-00001")),
    ("msg", msg("CONSULTA;ac-0001")),
    ("msg", msg("DEPOSITO;ac-0001;10")),
])

add("paths", [
    ("path", "MSG", "POST", "/MSG", {"m": msg("PING")}),
    ("path", "health-case", "GET", "/Health"),
    ("path", "dbl", "POST", "//msg", {"m": msg("PING")}),
    ("path", "msg-space", "POST", "/msg ", {"m": msg("PING")}),
])

add("control_char", [
    ("raw", "nul", "POST", "/msg", b'{"m":"PING\\u0000;64"}'),
    ("raw", "tab-cmd", "POST", "/msg", json.dumps({"m": "PING\t;64"}).encode()),
])

add("json_edges", [
    ("raw", "trail-comma", "POST", "/msg", b'{"m":"PING;64",}'),
    ("raw", "dup-m", "POST", "/msg", b'{"m":"NOPE;1","m":"PING;64"}'),
    ("raw", "bom", "POST", "/msg", b'\xef\xbb\xbf{"m":"PING;64"}'),
])


def main():
    diffs = 0
    for name, steps in CASES:
        print(f"\n== {name} ==")
        try:
            o = run_seq(ORACLE, steps)
        except Exception as e:  # noqa: BLE001
            print(" oracle ERR", e)
            continue
        r = run_seq(REPLICA, steps)
        for (lo, vo), (lr, vr) in zip(o, r):
            mark = "OK" if vo == vr else "DIFF"
            if vo != vr:
                diffs += 1
                print(f"  [{mark}] {lo}")
                print(f"    O {vo}")
                print(f"    R {vr}")
            else:
                print(f"  [OK] {lo} -> {vo[0]} {json.dumps(vo[1], ensure_ascii=False)[:120]}")
    # leave both reset
    reset(ORACLE)
    reset(REPLICA)
    print(f"\nDIFFS={diffs}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
