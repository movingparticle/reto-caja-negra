import json
import sys
import urllib.error
import urllib.request

sys.path.insert(0, r"C:\Users\usuario\Desktop\hackthon lab10")
from _tokens import TEAM_TOKEN

ORACLE = "https://caja-negra-production-c64f.up.railway.app"
REPLICA = "https://caja-negra-reemplazo.parsec-ai-labs.workers.dev"


def raw(base, data):
    req = urllib.request.Request(
        base + "/msg",
        data=data,
        headers={
            "Authorization": "Bearer " + TEAM_TOKEN,
            "Content-Type": "application/json",
            "User-Agent": "Frontier-Gap/1.0",
        },
        method="POST",
    )
    try:
        res = urllib.request.urlopen(req, timeout=20)
        return res.status, res.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


cases = []
for cp in (0, 1, 8, 11, 12, 14, 31, 127):
    cases.append((f"u{cp:04x}", json.dumps({"m": "PING" + chr(cp) + ";64"}).encode()))
cases.append(("bom", b"\xef\xbb\xbf" + json.dumps({"m": "PING;64"}).encode()))
cases.append(("badutf", b'{"m":"PING;64"}\xff'))

for name, body in cases:
    print(name)
    print("  O", raw(ORACLE, body))
    print("  R", raw(REPLICA, body))
