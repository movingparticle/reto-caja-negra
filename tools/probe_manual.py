import json
import sys
import urllib.error
import urllib.request

sys.path.insert(0, r"C:\Users\usuario\Desktop\hackthon lab10")
from _tokens import TEAM_TOKEN

B = "https://caja-negra-reemplazo.parsec-ai-labs.workers.dev"


def ctrl(p):
    rem = 0
    for c in p.upper():
        code = ord(c)
        if 65 <= code <= 90:
            v = code - 64
            rem = (rem * 100 + v) % 97 if v >= 10 else (rem * 10 + v) % 97
        elif 48 <= code <= 57:
            rem = (rem * 10 + (code - 48)) % 97
    return 98 - (rem * 3) % 97


def post(m):
    req = urllib.request.Request(
        B + "/msg",
        data=json.dumps({"m": m}).encode(),
        headers={"Authorization": "Bearer " + TEAM_TOKEN, "Content-Type": "application/json", "User-Agent": "Mozilla/5.0 Frontier/1.0"},
        method="POST",
    )
    try:
        r = urllib.request.urlopen(req, timeout=20)
        return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


c = ctrl("ALTA;Carlos")
print("control(ALTA;Carlos) =", c)
reset = urllib.request.Request(
    B + "/__reset", data=b"{}",
    headers={"Authorization": "Bearer " + TEAM_TOKEN, "User-Agent": "Mozilla/5.0 Frontier/1.0"}, method="POST",
)
try:
    urllib.request.urlopen(reset, timeout=20)
except Exception as e:  # noqa: BLE001
    print("reset:", e)
print("ALTA;Carlos      ->", post("ALTA;Carlos"))
print("ALTA;Carlos;%d ->" % c, post("ALTA;Carlos;%d" % c))

