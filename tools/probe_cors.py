import json
import sys
import urllib.error
import urllib.request

sys.path.insert(0, r"C:\Users\usuario\Desktop\hackthon lab10")
from _tokens import TEAM_TOKEN

B = "https://caja-negra-reemplazo.parsec-ai-labs.workers.dev"


def req(method, path, data=None, headers=None):
    h = {"User-Agent": "x"}
    if headers:
        h.update(headers)
    r = urllib.request.Request(B + path, data=data, headers=h, method=method)
    try:
        res = urllib.request.urlopen(r, timeout=20)
        return res.status, dict(res.headers), res.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read().decode("utf-8", "replace")


pf = req("OPTIONS", "/msg", headers={
    "Origin": "https://caja-negra-demo.pages.dev",
    "Access-Control-Request-Method": "POST",
    "Access-Control-Request-Headers": "authorization,content-type",
})
print("preflight", pf[0], "acao=", pf[1].get("Access-Control-Allow-Origin"), "acam=", pf[1].get("Access-Control-Allow-Methods"))

plain = req("OPTIONS", "/msg")
print("plain OPTIONS", plain[0], plain[2])

post = req("POST", "/msg", data=json.dumps({"m": "PING;64"}).encode(), headers={
    "Authorization": "Bearer " + TEAM_TOKEN,
    "Content-Type": "application/json",
    "Origin": "https://caja-negra-demo.pages.dev",
})
print("POST", post[0], post[2], "acao=", post[1].get("Access-Control-Allow-Origin"))
