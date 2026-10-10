import json
import sys
import urllib.error
import urllib.request

sys.path.insert(0, r"C:\Users\usuario\Desktop\hackthon lab10")
from _tokens import TEAM_TOKEN

suite = json.load(open(r"C:\Users\usuario\Desktop\hackthon lab10\reto-caja-negra\demo-suite.json", encoding="utf-8"))
for t in suite:
    if t["id"] == "p_head":
        print("SUITE p_head:", json.dumps(t, ensure_ascii=False))


def head(base):
    req = urllib.request.Request(base + "/health", headers={"Authorization": "Bearer " + TEAM_TOKEN, "User-Agent": "x"}, method="HEAD")
    try:
        r = urllib.request.urlopen(req, timeout=20)
        return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


for name, base in [("ORACLE", "https://caja-negra-production-c64f.up.railway.app"), ("REPLICA", "https://caja-negra-reemplazo.parsec-ai-labs.workers.dev")]:
    st, body = head(base)
    print(name, "HEAD /health ->", st, "body=", body)
