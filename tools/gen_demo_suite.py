#!/usr/bin/env python3
"""Genera la suite de demo (demo-suite.json) capturando la verdad del ORÁCULO.

Cada test es una secuencia de pasos (reset / request) con el status y cuerpo
esperados tomados en vivo del oráculo original. El runner del demo replays la
secuencia con un reset previo y compara status+cuerpo en cada paso.
"""
import json
import sys
import time
import os
import urllib.error
import urllib.request

sys.path.insert(0, r"C:\Users\usuario\Desktop\hackthon lab10")
from _tokens import TEAM_TOKEN  # noqa: E402

ORACLE = "https://caja-negra-production-c64f.up.railway.app"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "demo-suite.json")
UA = "Frontier-DemoGen/1.0"


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


_last = [0.0]


def _throttle():
    dt = time.time() - _last[0]
    if dt < 0.12:
        time.sleep(0.12 - dt)
    _last[0] = time.time()


def send(step):
    method = step["method"]
    path = step["path"]
    headers = {"User-Agent": UA}
    headers.update(step.get("headers", {}))
    if "auth" in step and not step.get("headers"):
        tok = step["auth"]
        if tok == "team":
            headers["Authorization"] = "Bearer " + TEAM_TOKEN
        elif tok == "invalid":
            headers["Authorization"] = "Bearer invalid_token_99999999999999999"
        # "none" -> no header
    data = None
    if "raw" in step:
        data = step["raw"].encode("utf-8")
        headers.setdefault("Content-Type", "application/json")
    elif step.get("body") is not None:
        data = json.dumps(step["body"]).encode("utf-8")
        headers.setdefault("Content-Type", "application/json")
    elif "m" in step:
        data = json.dumps({"m": step["m"]}).encode("utf-8")
        headers.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(ORACLE + path, data=data, headers=headers, method=method)
    for attempt in range(4):
        _throttle()
        try:
            with urllib.request.urlopen(req, timeout=25) as res:
                return res.status, json.loads(res.read().decode("utf-8", "replace"))
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")
            try:
                return e.code, json.loads(body)
            except ValueError:
                return e.code, body
        except Exception:  # noqa: BLE001
            time.sleep(0.5 * (attempt + 1))
    return None, None


def R():
    return {"method": "POST", "path": "/__reset", "auth": "team", "body": {}}


TESTS = []


def T(tid, cat, title, steps):
    TESTS.append({"id": tid, "category": cat, "title": title, "steps": steps})


def M(m, auth="team"):
    return {"method": "POST", "path": "/msg", "auth": auth, "m": m}


# ---------------- PROTOCOL ----------------
T("p_health", "protocol", "GET /health con token", [{"method": "GET", "path": "/health", "auth": "team"}])
T("p_health_unauth", "protocol", "GET /health sin token -> 401", [{"method": "GET", "path": "/health", "auth": "none"}])
T("p_health_wrongmethod", "protocol", "POST /health -> 404", [{"method": "POST", "path": "/health", "auth": "team", "body": {}}])
T("p_msg_get", "protocol", "GET /msg -> 404", [{"method": "GET", "path": "/msg", "auth": "team"}])
T("p_reset_get", "protocol", "GET /__reset -> 404", [{"method": "GET", "path": "/__reset", "auth": "team"}])
T("p_options", "protocol", "OPTIONS /msg -> 404", [{"method": "OPTIONS", "path": "/msg", "auth": "none"}])
T("p_trailing_slash", "protocol", "POST /msg/ -> 404", [{"method": "POST", "path": "/msg/", "auth": "team", "m": msg("PING")}])
T("p_unknown", "protocol", "GET ruta desconocida -> 404", [{"method": "GET", "path": "/does-not-exist", "auth": "team"}])
T("p_unknown_unauth", "protocol", "ruta desconocida sin auth -> 404", [{"method": "GET", "path": "/does-not-exist", "auth": "none"}])
T("p_msg_no_auth", "protocol", "POST /msg sin token -> 401", [dict(M(msg("PING")), auth="none")])
T("p_msg_bad_token", "protocol", "POST /msg token inválido -> 401", [dict(M(msg("PING")), auth="invalid")])
T("p_bearer_lower", "protocol", "bearer minúscula -> 401", [{"method": "POST", "path": "/msg", "headers": {"Authorization": "bearer " + TEAM_TOKEN, "Content-Type": "application/json"}, "m": msg("PING")}])
T("p_bearer_2space", "protocol", "Bearer doble espacio -> 401", [{"method": "POST", "path": "/msg", "headers": {"Authorization": "Bearer  " + TEAM_TOKEN, "Content-Type": "application/json"}, "m": msg("PING")}])
T("p_query_token", "protocol", "?token= no autoriza -> 401", [{"method": "GET", "path": "/health?token=" + TEAM_TOKEN, "auth": "none"}])
T("p_query_key", "protocol", "?key= no autoriza -> 401", [{"method": "GET", "path": "/health?key=" + TEAM_TOKEN, "auth": "none"}])
T("p_health_slash", "protocol", "GET /health/ -> 404", [{"method": "GET", "path": "/health/", "auth": "team"}])
T("p_msg_query", "protocol", "POST /msg?x=1", [{"method": "POST", "path": "/msg?x=1", "auth": "team", "m": msg("PING")}])
T("p_ct_missing", "protocol", "Content-Type vacío", [{"method": "POST", "path": "/msg", "headers": {"Authorization": "Bearer " + TEAM_TOKEN, "Content-Type": ""}, "m": msg("PING")}])
T("p_ct_text", "protocol", "Content-Type text/plain", [{"method": "POST", "path": "/msg", "headers": {"Authorization": "Bearer " + TEAM_TOKEN, "Content-Type": "text/plain"}, "m": msg("PING")}])
T("p_reset_nobody", "protocol", "POST /__reset sin cuerpo", [{"method": "POST", "path": "/__reset", "auth": "team"}])
T("p_put", "protocol", "PUT /msg -> 404", [{"method": "PUT", "path": "/msg", "auth": "team", "m": msg("PING")}])
T("p_delete", "protocol", "DELETE /msg -> 404", [{"method": "DELETE", "path": "/msg", "auth": "team"}])
T("p_head", "protocol", "HEAD /health", [{"method": "HEAD", "path": "/health", "auth": "team"}])
T("p_double_slash", "protocol", "POST //msg", [{"method": "POST", "path": "//msg", "auth": "team", "m": msg("PING")}])

# ---------------- INPUT ----------------
T("i_empty", "input", "cuerpo vacío -> E100", [{"method": "POST", "path": "/msg", "auth": "team", "raw": ""}])
T("i_ws", "input", "solo espacios -> E100", [{"method": "POST", "path": "/msg", "auth": "team", "raw": "   \n\t  "}])
T("i_malformed", "input", "JSON malformado -> E100", [{"method": "POST", "path": "/msg", "auth": "team", "raw": '{"m": "PING;64"'}])
T("i_string", "input", "JSON string -> E100", [{"method": "POST", "path": "/msg", "auth": "team", "raw": '"just a string"'}])
T("i_array", "input", "JSON array -> E100", [{"method": "POST", "path": "/msg", "auth": "team", "raw": "[1,2,3]"}])
T("i_null", "input", "JSON null -> E100", [{"method": "POST", "path": "/msg", "auth": "team", "raw": "null"}])
T("i_number", "input", "JSON número -> E100", [{"method": "POST", "path": "/msg", "auth": "team", "raw": "12345"}])
T("i_bool", "input", "JSON bool -> E100", [{"method": "POST", "path": "/msg", "auth": "team", "raw": "true"}])
T("i_missing_m", "input", "falta m -> E102", [{"method": "POST", "path": "/msg", "auth": "team", "body": {"other": 1}}])
T("i_m_int", "input", "m numérico -> E102", [{"method": "POST", "path": "/msg", "auth": "team", "body": {"m": 1234}}])
T("i_m_null", "input", "m null -> E102", [{"method": "POST", "path": "/msg", "auth": "team", "body": {"m": None}}])
T("i_m_array", "input", "m array -> E102", [{"method": "POST", "path": "/msg", "auth": "team", "body": {"m": ["PING", "64"]}}])
T("i_m_object", "input", "m objeto -> E102", [{"method": "POST", "path": "/msg", "auth": "team", "body": {"m": {"c": "PING"}}}])
T("i_extra", "input", "campo extra", [{"method": "POST", "path": "/msg", "auth": "team", "body": {"m": msg("PING"), "extra": 1}}])
T("i_trail_comma", "input", "JSON con coma final -> E100", [{"method": "POST", "path": "/msg", "auth": "team", "raw": '{"m":"PING;64",}'}])
T("i_dup_m", "input", "clave m duplicada", [{"method": "POST", "path": "/msg", "auth": "team", "raw": '{"m":"NOPE;1","m":"PING;64"}'}])
T("i_bom", "input", "JSON con BOM -> E100", [{"method": "POST", "path": "/msg", "auth": "team", "raw": "\ufeff" + json.dumps({"m": "PING;64"})}])
T("i_ctrl", "input", "carácter de control en m -> E301", [{"method": "POST", "path": "/msg", "auth": "team", "body": {"m": "PING\u0000;64"}}])
T("i_bad_utf8", "input", "UTF-8 inválido -> E100", [{"method": "POST", "path": "/msg", "auth": "team", "raw": "{\"m\":\"PING;64\"}\ufffd"}])

# ---------------- INTEGRITY ----------------
T("c_valid", "integrity", "control válido -> ALTA", [R(), M(msg("ALTA;Lucia"))])
T("c_invalid", "integrity", "control inválido -> E202", [M("ALTA;Lucia;83")])
T("c_malformed", "integrity", "control mal formado -> E201", [M("ALTA;Lucia;5X")])
T("c_missing", "integrity", "falta control -> E103/E202", [M("ALTA")])
T("c_empty_seg", "integrity", "segmento vacío -> E104", [M("ALTA;;82")])
T("c_lead_zero", "integrity", "control con cero inicial -> E202", [M("ALTA;Mateo;03")])
T("c_3digits", "integrity", "control de 3 dígitos -> E201", [M("ALTA;Mateo;100")])
T("c_zero", "integrity", "control 0", [M("ALTA;Mateo;0")])
T("c_one", "integrity", "control 1", [M("ALTA;Mateo;1")])
T("c_ping_nock", "integrity", "PING ignora checksum", [M("PING;999")])
T("c_ping_wrongck", "integrity", "PING checksum 00", [M("PING;00")])
T("c_98", "integrity", "control 98 válido", [R(), M("ALTA;N16;98")])
T("c_2", "integrity", "control 2 válido", [R(), M("ALTA;N48;2")])
T("c_plus", "integrity", "control +14 -> E201", [M("ALTA;A;+14")])
T("c_99", "integrity", "control 99 -> E202", [M("ALTA;A;99")])
T("c_spaces", "integrity", "control con espacio -> E201", [M("ALTA;A;1 4")])
T("c_ping_empty", "integrity", "PING; (control vacío)", [M("PING;")])
T("c_dbl_semicolon", "integrity", "doble ; -> E104", [M(msg("ALTA;A;;B"))])
T("c_m_empty", "integrity", "m vacío -> E103", [{"method": "POST", "path": "/msg", "auth": "team", "body": {"m": ""}}])

# ---------------- BUSINESS ----------------
T("b_flow", "business", "flujo completo ALTA/DEPOSITO/TRANSFER/ANULA", [
    R(), M(msg("ALTA;Alice")), M(msg("ALTA;Bob")), M(msg("DEPOSITO;AC-0001;500")),
    M(msg("TRANSFER;AC-0001;AC-0002;400")), M(msg("CONSULTA;AC-0001")), M(msg("CONSULTA;AC-0002")),
    M(msg("ANULA;OP-0001")), M(msg("CONSULTA;AC-0001")),
])
T("b_tx_limit_ok", "business", "TRANSFER límite exacto 50000", [
    R(), M(msg("ALTA;A")), M(msg("ALTA;B")), M(msg("DEPOSITO;AC-0001;50000")), M(msg("TRANSFER;AC-0001;AC-0002;50000")),
])
T("b_tx_over", "business", "TRANSFER sobre límite -> E506", [
    R(), M(msg("ALTA;A")), M(msg("ALTA;B")), M(msg("DEPOSITO;AC-0001;200000")), M(msg("TRANSFER;AC-0001;AC-0002;50001")),
])
T("b_dep_big", "business", "DEPOSITO monto grande", [
    R(), M(msg("ALTA;A")), M(msg("DEPOSITO;AC-0001;9999999999")), M(msg("CONSULTA;AC-0001")),
])
T("b_precedence", "business", "precedencia E303>E304>E401", [
    R(), M(msg("TRANSFER;AC-0001;AC-0001;0")), M(msg("TRANSFER;AC-0001;AC-0001;150000")), M(msg("TRANSFER;AC-9999;AC-8888;150000")),
])
T("b_neg_balance", "business", "saldo negativo por ANULA", [
    R(), M(msg("ALTA;A")), M(msg("ALTA;B")), M(msg("ALTA;C")), M(msg("DEPOSITO;AC-0001;1000")),
    M(msg("TRANSFER;AC-0001;AC-0002;1000")), M(msg("TRANSFER;AC-0002;AC-0003;1000")),
    M(msg("ANULA;OP-0002")), M(msg("CONSULTA;AC-0002")), M(msg("TRANSFER;AC-0002;AC-0001;100")),
])
T("b_unknown_cmd", "business", "comando desconocido -> E301", [R(), M(msg("FOO;123"))])
T("b_arity", "business", "aridad inválida", [R(), M(msg("ALTA")), M(msg("PING;x"))])
T("b_lower_account", "business", "id de cuenta en minúsculas -> E401", [R(), M(msg("ALTA;A")), M(msg("CONSULTA;ac-0001"))])
T("b_dup_names", "business", "nombres duplicados", [R(), M(msg("ALTA;Dup")), M(msg("ALTA;Dup"))])
T("b_ids_kept", "business", "IDs no consumidos por fallo", [
    R(), M(msg("ALTA;A")), M(msg("DEPOSITO;AC-0001;0")), M(msg("ALTA;B")), M(msg("DEPOSITO;AC-0001;10")),
])
T("b_unicode", "business", "nombre unicode", [R(), M(msg("ALTA;José-Ñ"))])
T("b_monto_plus", "business", "monto +5 -> E303", [R(), M(msg("ALTA;A")), M(msg("DEPOSITO;AC-0001;+5"))])
T("b_monto_space", "business", "monto con espacio -> E303", [R(), M(msg("ALTA;A")), M(msg("DEPOSITO;AC-0001; 5"))])
T("b_lead_space_cmd", "business", "comando con espacio inicial", [R(), M(msg(" ALTA;A"))])
T("b_trail_space_cmd", "business", "comando con espacio final", [R(), M(msg("ALTA;A "))])
T("b_lower_cmd", "business", "comando en minúsculas (pInG)", [R(), M(msg("pInG"))])
T("b_eq_balance", "business", "transferir todo el saldo", [
    R(), M(msg("ALTA;A")), M(msg("ALTA;B")), M(msg("DEPOSITO;AC-0001;1000")), M(msg("TRANSFER;AC-0001;AC-0002;1000")), M(msg("CONSULTA;AC-0001")),
])
T("b_anula_after_spend", "business", "ANULA tras gastar (saldo negativo)", [
    R(), M(msg("ALTA;A")), M(msg("ALTA;B")), M(msg("DEPOSITO;AC-0001;1000")),
    M(msg("TRANSFER;AC-0001;AC-0002;1000")), M(msg("TRANSFER;AC-0002;AC-0001;1000")),
    M(msg("ANULA;OP-0002")), M(msg("CONSULTA;AC-0001")), M(msg("CONSULTA;AC-0002")),
])
T("b_bad_ids", "business", "IDs no canónicos -> E401", [
    R(), M(msg("ALTA;A")), M(msg("CONSULTA;AC-1")), M(msg("CONSULTA;AC-00001")), M(msg("CONSULTA;ac-0001")), M(msg("DEPOSITO;ac-0001;10")),
])
T("b_e402", "business", "ANULA operación inexistente -> E402", [R(), M(msg("ANULA;OP-9999"))])

# ---------------- INCIDENT ----------------
def blocked():
    return [M(msg("ALTA;A")), M(msg("ALTA;B")), M(msg("DEPOSITO;AC-0001;100")),
            M(msg("TRANSFER;AC-0001;AC-0002;50001")), M(msg("TRANSFER;AC-0001;AC-0002;50001")),
            M(msg("TRANSFER;AC-0001;AC-0002;50001"))]

T("inc_e510_timing", "incident", "E510 tras 3 fallos + intentos", [R()] + blocked() + [
    M(msg("TRANSFER;AC-0001;AC-0002;50001")), M(msg("TRANSFER;AC-0001;AC-0002;1")),
])
T("inc_blocked_ops", "incident", "DEPOSITO desbloquea cuenta", [R()] + blocked() + [
    M(msg("CONSULTA;AC-0001")), M(msg("DEPOSITO;AC-0001;50")), M(msg("CONSULTA;AC-0001")), M(msg("TRANSFER;AC-0001;AC-0002;50001")),
])
T("inc_consulta_mid", "incident", "CONSULTA entre fallos no resetea", [R()] + [
    M(msg("ALTA;A")), M(msg("ALTA;B")), M(msg("DEPOSITO;AC-0001;100")),
    M(msg("TRANSFER;AC-0001;AC-0002;50001")), M(msg("CONSULTA;AC-0001")),
    M(msg("TRANSFER;AC-0001;AC-0002;50001")), M(msg("TRANSFER;AC-0001;AC-0002;50001")), M(msg("TRANSFER;AC-0001;AC-0002;50001")),
])
T("inc_e507_counts", "incident", "E507 también cuenta para bloqueo", [R()] + [
    M(msg("ALTA;A")), M(msg("ALTA;B")), M(msg("TRANSFER;AC-0001;AC-0002;1")),
    M(msg("TRANSFER;AC-0001;AC-0002;1")), M(msg("TRANSFER;AC-0001;AC-0002;1")), M(msg("TRANSFER;AC-0001;AC-0002;1")),
])
T("inc_success_resets", "incident", "TRANSFER exitosa resetea fallos", [R()] + [
    M(msg("ALTA;A")), M(msg("ALTA;B")), M(msg("DEPOSITO;AC-0001;200")),
    M(msg("TRANSFER;AC-0001;AC-0002;50001")), M(msg("TRANSFER;AC-0001;AC-0002;50001")),
    M(msg("TRANSFER;AC-0001;AC-0002;100")),
    M(msg("TRANSFER;AC-0001;AC-0002;50001")), M(msg("TRANSFER;AC-0001;AC-0002;50001")), M(msg("TRANSFER;AC-0001;AC-0002;50001")),
])
T("inc_halt_arity", "incident", "HALT aridad inválida", [R(), M(msg("HALT")), M(msg("HALT;1;2"))])
T("inc_halt_warn", "incident", "HALT sin confirmar -> E520", [R(), M(msg("HALT;AC-0001")), M(msg("PING")), R()])
T("inc_halt_state", "incident", "HALT;1 -> 503 E599 hasta reset", [
    R(), M(msg("PING")), M(msg("HALT;1")), M(msg("PING")),
    {"method": "GET", "path": "/health", "auth": "team"}, R(), M(msg("PING")),
])
T("inc_halt_variants", "incident", "HALT;01 / HALT;1 (espacio)", [R(), M(msg("HALT;01")), M(msg("HALT;1 ")), M("HALT;1"), M(msg("PING"))])
T("inc_sugg_near", "incident", "sugerencia Levenshtein (ALTAX)", [R(), M(msg("ALTAX;A"))])
T("inc_sugg_far", "incident", "sin sugerencia (FOO)", [R(), M(msg("FOO;1"))])
T("inc_sugg_halt", "incident", "sugerencia HALT (AALT)", [R(), M(msg("AALT;A"))])


def main():
    total_steps = 0
    print(f"Capturando {len(TESTS)} tests contra el oráculo...")
    for i, t in enumerate(TESTS, 1):
        for step in t["steps"]:
            st, body = send(step)
            step["expStatus"] = st
            step["expBody"] = body
        total_steps += len(t["steps"])
        if i % 10 == 0:
            print(f"  {i}/{len(TESTS)}")
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(TESTS, f, ensure_ascii=False, indent=1)
    print(f"OK -> {OUT}")
    print(f"tests={len(TESTS)} pasos={total_steps}")


if __name__ == "__main__":
    main()
