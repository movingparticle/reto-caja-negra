#!/usr/bin/env python3
"""
Arnés diferencial (Paso 4) — Reto 2 Caja Negra.

Ejecuta la misma batería contra el ORÁCULO original y el REEMPLAZO y reporta
la primera divergencia por caso. Nunca asume que la respuesta del reemplazo es
la correcta: solo compara.

Uso:
    python tools/diff_battery.py
    python tools/diff_battery.py --oracle URL --replica URL --token TOKEN
    python tools/diff_battery.py --replica-only   # solo replica (sin oráculo)

Variables de entorno: ORACLE_URL, REPLICA_URL, TEAM_TOKEN, UA
Salida: tools/diff_report.json  (transcripción completa por caso)
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

ORACLE_URL = os.environ.get("ORACLE_URL", "https://caja-negra-production-c64f.up.railway.app")
REPLICA_URL = os.environ.get("REPLICA_URL", "https://caja-negra-reemplazo.parsec-ai-labs.workers.dev")
TOKEN = os.environ.get("TEAM_TOKEN", "REDACTED_TEAM_TOKEN")
UA = os.environ.get("UA", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Frontier-Diff/1.0")

MAX_BODY_BYTES = 8192


def calc_control(payload: str) -> int:
    """ISO 7064 Mod 97-10 variante observada: CD = 98 - ((N*100) mod 97)."""
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


def raw(base, method, path, body=None, token=TOKEN, extra_headers=None, raw_body=None):
    """Envía una petición y devuelve dict normalizado."""
    headers = {"User-Agent": UA}
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    headers["Content-Type"] = "application/json"
    if extra_headers:
        headers.update(extra_headers)

    data = None
    if raw_body is not None:
        data = raw_body if isinstance(raw_body, bytes) else raw_body.encode("utf-8")
    elif body is not None:
        data = json.dumps(body).encode("utf-8")

    req = urllib.request.Request(f"{base}{path}", data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=20) as res:
            text = res.read().decode("utf-8", "replace")
            return _norm(res.status, text, res.headers)
    except urllib.error.HTTPError as e:
        text = e.read().decode("utf-8", "replace")
        return _norm(e.code, text, e.headers)
    except Exception as e:  # noqa: BLE001
        return {"status": None, "body": None, "xreq": None, "error": f"{type(e).__name__}: {e}"}


def _norm(status, text, headers):
    try:
        body = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        body = text
    return {
        "status": status,
        "body": body,
        "xreq": headers.get("X-Req") if headers else None,
    }


def reset(base):
    return raw(base, "POST", "/__reset", body={})


# ---------------------------------------------------------------------------
# Batería: cada caso es (id, familia, callable(base) -> transcript)
# El callable hace reset y luego la secuencia. Devuelve lista de respuestas.
# ---------------------------------------------------------------------------

def case_protocol_health(base):
    return [raw(base, "GET", "/health")]


def case_protocol_health_unauth(base):
    return [raw(base, "GET", "/health", token=None)]


def case_protocol_health_wrong_method(base):
    return [raw(base, "POST", "/health", body={})]


def case_protocol_msg_get(base):
    return [raw(base, "GET", "/msg")]


def case_protocol_reset_get(base):
    return [raw(base, "GET", "/__reset")]


def case_protocol_options(base):
    return [raw(base, "OPTIONS", "/msg", token=None)]


def case_protocol_trailing_slash(base):
    return [raw(base, "POST", "/msg/", body={"m": msg("PING")})]


def case_protocol_unknown(base):
    return [raw(base, "GET", "/does-not-exist")]


def case_protocol_unknown_unauth(base):
    return [raw(base, "GET", "/does-not-exist", token=None)]


def case_protocol_msg_no_auth(base):
    return [raw(base, "POST", "/msg", body={"m": msg("PING")}, token=None)]


def case_protocol_msg_bad_token(base):
    return [raw(base, "POST", "/msg", body={"m": msg("PING")}, token="totally-wrong")]


def case_protocol_bearer_lowercase(base):
    return [raw(base, "POST", "/msg", body={"m": msg("PING")},
                extra_headers={"Authorization": f"bearer {TOKEN}"}, token=None)]


def case_protocol_bearer_extra_space(base):
    return [raw(base, "POST", "/msg", body={"m": msg("PING")},
                extra_headers={"Authorization": f"Bearer  {TOKEN}"}, token=None)]


def case_protocol_query_token(base):
    return [raw(base, "GET", f"/health?token={TOKEN}", token=None)]


def case_protocol_query_key(base):
    return [raw(base, "GET", f"/health?key={TOKEN}", token=None)]


def case_json_empty(base):
    return [raw(base, "POST", "/msg", raw_body=b"")]


def case_json_whitespace(base):
    return [raw(base, "POST", "/msg", raw_body=b"   \n\t  ")]


def case_json_malformed(base):
    return [raw(base, "POST", "/msg", raw_body=b'{"m": "PING;64"')]


def case_json_string(base):
    return [raw(base, "POST", "/msg", raw_body=b'"just a string"')]


def case_json_array(base):
    return [raw(base, "POST", "/msg", raw_body=b"[1,2,3]")]


def case_json_null(base):
    return [raw(base, "POST", "/msg", raw_body=b"null")]


def case_json_number(base):
    return [raw(base, "POST", "/msg", raw_body=b"12345")]


def case_json_bool(base):
    return [raw(base, "POST", "/msg", raw_body=b"true")]


def case_json_missing_m(base):
    return [raw(base, "POST", "/msg", body={"other": 1})]


def case_json_m_int(base):
    return [raw(base, "POST", "/msg", body={"m": 1234})]


def case_json_m_null(base):
    return [raw(base, "POST", "/msg", body={"m": None})]


def case_json_m_array(base):
    return [raw(base, "POST", "/msg", body={"m": ["PING", "64"]})]


def case_json_m_object(base):
    return [raw(base, "POST", "/msg", body={"m": {"c": "PING"}})]


def case_json_extra_fields(base):
    return [raw(base, "POST", "/msg", body={"m": msg("PING"), "extra": 1})]


def case_size_exact_8192(base):
    # rellena con espacios dentro de una clave extra hasta exactamente 8192 bytes
    base_body = '{"m":"' + msg("PING") + '","pad":"'
    closing = '"}'
    pad_len = MAX_BODY_BYTES - len(base_body) - len(closing)
    body = (base_body + (" " * pad_len) + closing).encode()
    assert len(body) == MAX_BODY_BYTES, len(body)
    return [raw(base, "POST", "/msg", raw_body=body)]


def case_size_over_8192(base):
    base_body = '{"m":"' + msg("PING") + '","pad":"'
    closing = '"}'
    pad_len = MAX_BODY_BYTES + 1 - len(base_body) - len(closing)
    body = (base_body + (" " * pad_len) + closing).encode()
    assert len(body) == MAX_BODY_BYTES + 1, len(body)
    return [raw(base, "POST", "/msg", raw_body=body)]


def case_control_valid(base):
    reset(base)
    return [raw(base, "POST", "/msg", body={"m": msg("ALTA;Lucia")})]


def case_control_invalid(base):
    return [raw(base, "POST", "/msg", body={"m": "ALTA;Lucia;83"})]


def case_control_malformed(base):
    return [raw(base, "POST", "/msg", body={"m": "ALTA;Lucia;5X"})]


def case_control_missing(base):
    return [raw(base, "POST", "/msg", body={"m": "ALTA"})]


def case_control_empty_segment(base):
    return [raw(base, "POST", "/msg", body={"m": "ALTA;;82"})]


def case_control_leading_zero(base):
    return [raw(base, "POST", "/msg", body={"m": "ALTA;Mateo;03"})]


def case_control_three_digits(base):
    return [raw(base, "POST", "/msg", body={"m": "ALTA;Mateo;100"})]


def case_control_zero(base):
    return [raw(base, "POST", "/msg", body={"m": "ALTA;Mateo;0"})]


def case_control_one(base):
    return [raw(base, "POST", "/msg", body={"m": "ALTA;Mateo;1"})]


def case_ping_no_checksum(base):
    return [raw(base, "POST", "/msg", body={"m": "PING;999"})]


def case_ping_wrong_checksum(base):
    return [raw(base, "POST", "/msg", body={"m": "PING;00"})]


def case_business_full_flow(base):
    reset(base)
    return [
        raw(base, "POST", "/msg", body={"m": msg("ALTA;Alice")}),
        raw(base, "POST", "/msg", body={"m": msg("ALTA;Bob")}),
        raw(base, "POST", "/msg", body={"m": msg("DEPOSITO;AC-0001;500")}),
        raw(base, "POST", "/msg", body={"m": msg("TRANSFER;AC-0001;AC-0002;400")}),
        raw(base, "POST", "/msg", body={"m": msg("CONSULTA;AC-0001")}),
        raw(base, "POST", "/msg", body={"m": msg("CONSULTA;AC-0002")}),
        raw(base, "POST", "/msg", body={"m": msg("ANULA;OP-0001")}),
        raw(base, "POST", "/msg", body={"m": msg("CONSULTA;AC-0001")}),
    ]


def case_transfer_exact_limit(base):
    reset(base)
    return [
        raw(base, "POST", "/msg", body={"m": msg("ALTA;A")}),
        raw(base, "POST", "/msg", body={"m": msg("ALTA;B")}),
        raw(base, "POST", "/msg", body={"m": msg("DEPOSITO;AC-0001;100000")}),
        raw(base, "POST", "/msg", body={"m": msg("TRANSFER;AC-0001;AC-0002;100000")}),
    ]


def case_transfer_over_limit(base):
    reset(base)
    return [
        raw(base, "POST", "/msg", body={"m": msg("ALTA;A")}),
        raw(base, "POST", "/msg", body={"m": msg("ALTA;B")}),
        raw(base, "POST", "/msg", body={"m": msg("DEPOSITO;AC-0001;200000")}),
        raw(base, "POST", "/msg", body={"m": msg("TRANSFER;AC-0001;AC-0002;100001")}),
    ]


def case_deposit_over_limit(base):
    reset(base)
    return [
        raw(base, "POST", "/msg", body={"m": msg("ALTA;A")}),
        raw(base, "POST", "/msg", body={"m": msg("DEPOSITO;AC-0001;9999999999")}),
        raw(base, "POST", "/msg", body={"m": msg("CONSULTA;AC-0001")}),
    ]


def case_precedence(base):
    reset(base)
    return [
        raw(base, "POST", "/msg", body={"m": msg("TRANSFER;AC-0001;AC-0001;0")}),      # E303
        raw(base, "POST", "/msg", body={"m": msg("TRANSFER;AC-0001;AC-0001;150000")}),  # E304
        raw(base, "POST", "/msg", body={"m": msg("TRANSFER;AC-9999;AC-8888;150000")}),  # E401
    ]


def case_ids_not_consumed(base):
    reset(base)
    return [
        raw(base, "POST", "/msg", body={"m": msg("ALTA;A")}),          # AC-0001
        raw(base, "POST", "/msg", body={"m": msg("DEPOSITO;AC-0001;0")}),  # E303 fail
        raw(base, "POST", "/msg", body={"m": msg("ALTA;B")}),          # must be AC-0002
        raw(base, "POST", "/msg", body={"m": msg("DEPOSITO;AC-0001;10")}),  # OP-0001
    ]


def case_negative_balance(base):
    reset(base)
    return [
        raw(base, "POST", "/msg", body={"m": msg("ALTA;A")}),
        raw(base, "POST", "/msg", body={"m": msg("ALTA;B")}),
        raw(base, "POST", "/msg", body={"m": msg("ALTA;C")}),
        raw(base, "POST", "/msg", body={"m": msg("DEPOSITO;AC-0001;1000")}),      # OP-0001
        raw(base, "POST", "/msg", body={"m": msg("TRANSFER;AC-0001;AC-0002;1000")}),  # OP-0002
        raw(base, "POST", "/msg", body={"m": msg("TRANSFER;AC-0002;AC-0003;1000")}),  # OP-0003
        raw(base, "POST", "/msg", body={"m": msg("ANULA;OP-0002")}),
        raw(base, "POST", "/msg", body={"m": msg("CONSULTA;AC-0002")}),
        raw(base, "POST", "/msg", body={"m": msg("TRANSFER;AC-0002;AC-0001;100")}),  # E507
    ]


def case_unknown_command(base):
    reset(base)
    return [raw(base, "POST", "/msg", body={"m": msg("FOO;123")})]


def case_arity(base):
    reset(base)
    return [
        raw(base, "POST", "/msg", body={"m": msg("ALTA")}),
        raw(base, "POST", "/msg", body={"m": msg("PING;x")}),
    ]


def case_lowercase_account(base):
    reset(base)
    return [
        raw(base, "POST", "/msg", body={"m": msg("ALTA;A")}),
        raw(base, "POST", "/msg", body={"m": msg("CONSULTA;ac-0001")}),
    ]


def case_xreq_after_reset(base):
    reset(base)
    a = raw(base, "POST", "/msg", body={"m": msg("PING")})
    reset(base)
    b = raw(base, "POST", "/msg", body={"m": msg("PING")})
    return [a, b]


def case_xreq_on_error(base):
    reset(base)
    return [
        raw(base, "POST", "/msg", body={"m": msg("PING")}),
        raw(base, "POST", "/msg", raw_body=b"not json"),
        raw(base, "POST", "/msg", body={"m": msg("PING")}),
    ]


def case_duplicate_names(base):
    reset(base)
    return [
        raw(base, "POST", "/msg", body={"m": msg("ALTA;Dup")}),
        raw(base, "POST", "/msg", body={"m": msg("ALTA;Dup")}),
    ]


# --- Extensión: protocolo avanzado, auth y bordes ---

def case_options_health(base):
    return [raw(base, "OPTIONS", "/health", token=None)]


def case_options_reset(base):
    return [raw(base, "OPTIONS", "/__reset", token=None)]


def case_head_health(base):
    return [raw(base, "HEAD", "/health")]


def case_put_msg(base):
    return [raw(base, "PUT", "/msg", body={"m": msg("PING")})]


def case_delete_msg(base):
    return [raw(base, "DELETE", "/msg")]


def case_auth_no_bearer(base):
    return [raw(base, "POST", "/msg", body={"m": msg("PING")},
                extra_headers={"Authorization": TOKEN}, token=None)]


def case_auth_bearer_empty(base):
    return [raw(base, "POST", "/msg", body={"m": msg("PING")},
                extra_headers={"Authorization": "Bearer "}, token=None)]


def case_auth_bearer_leading_space(base):
    return [raw(base, "POST", "/msg", body={"m": msg("PING")},
                extra_headers={"Authorization": f" Bearer {TOKEN}"}, token=None)]


def case_health_trailing_slash(base):
    return [raw(base, "GET", "/health/")]


def case_msg_with_query(base):
    return [raw(base, "POST", "/msg?x=1", body={"m": msg("PING")})]


def case_content_type_missing(base):
    return [raw(base, "POST", "/msg", body={"m": msg("PING")},
                extra_headers={"Content-Type": ""})]


def case_content_type_text(base):
    return [raw(base, "POST", "/msg", body={"m": msg("PING")},
                extra_headers={"Content-Type": "text/plain"})]


def case_unicode_name(base):
    reset(base)
    return [raw(base, "POST", "/msg", body={"m": msg("ALTA;José-Ñ")})]


def case_monto_plus(base):
    reset(base)
    return [
        raw(base, "POST", "/msg", body={"m": msg("ALTA;A")}),
        raw(base, "POST", "/msg", body={"m": msg("DEPOSITO;AC-0001;+5")}),
    ]


def case_monto_space(base):
    reset(base)
    return [
        raw(base, "POST", "/msg", body={"m": msg("ALTA;A")}),
        raw(base, "POST", "/msg", body={"m": msg("DEPOSITO;AC-0001; 5")}),
    ]


def case_control_plus(base):
    return [raw(base, "POST", "/msg", body={"m": "ALTA;A;+14"})]


def case_control_98_valid(base):
    reset(base)
    return [raw(base, "POST", "/msg", body={"m": "ALTA;N16;98"})]


def case_control_2_valid(base):
    reset(base)
    return [raw(base, "POST", "/msg", body={"m": "ALTA;N48;2"})]


def case_control_99(base):
    return [raw(base, "POST", "/msg", body={"m": "ALTA;A;99"})]


def case_leading_space_command(base):
    reset(base)
    return [raw(base, "POST", "/msg", body={"m": msg(" ALTA;A")})]


def case_trailing_space_command(base):
    reset(base)
    return [raw(base, "POST", "/msg", body={"m": msg("ALTA;A ")})]


def case_ping_empty_control(base):
    return [raw(base, "POST", "/msg", body={"m": "PING;"})]


def case_double_semicolon(base):
    return [raw(base, "POST", "/msg", body={"m": msg("ALTA;A;;B")})]


def case_m_empty_string(base):
    return [raw(base, "POST", "/msg", body={"m": ""})]


def case_transfer_exact_balance(base):
    reset(base)
    return [
        raw(base, "POST", "/msg", body={"m": msg("ALTA;A")}),
        raw(base, "POST", "/msg", body={"m": msg("ALTA;B")}),
        raw(base, "POST", "/msg", body={"m": msg("DEPOSITO;AC-0001;1000")}),
        raw(base, "POST", "/msg", body={"m": msg("TRANSFER;AC-0001;AC-0002;1000")}),
        raw(base, "POST", "/msg", body={"m": msg("CONSULTA;AC-0001")}),
    ]


def case_anula_transfer_after_spend(base):
    reset(base)
    return [
        raw(base, "POST", "/msg", body={"m": msg("ALTA;A")}),
        raw(base, "POST", "/msg", body={"m": msg("ALTA;B")}),
        raw(base, "POST", "/msg", body={"m": msg("DEPOSITO;AC-0001;1000")}),
        raw(base, "POST", "/msg", body={"m": msg("TRANSFER;AC-0001;AC-0002;1000")}),
        raw(base, "POST", "/msg", body={"m": msg("TRANSFER;AC-0002;AC-0001;1000")}),
        raw(base, "POST", "/msg", body={"m": msg("ANULA;OP-0002")}),
        raw(base, "POST", "/msg", body={"m": msg("CONSULTA;AC-0001")}),
        raw(base, "POST", "/msg", body={"m": msg("CONSULTA;AC-0002")}),
    ]


def case_reset_no_body(base):
    return [raw(base, "POST", "/__reset")]


def case_lowercase_command_valid(base):
    reset(base)
    return [raw(base, "POST", "/msg", body={"m": msg("pInG")})]


def case_get_msg_with_auth(base):
    return [raw(base, "GET", "/msg")]


def case_control_spaces(base):
    return [raw(base, "POST", "/msg", body={"m": "ALTA;A;1 4"})]


# --- HALT (comando destructivo) y sugerencias ---

def case_halt_arity(base):
    reset(base)
    return [
        raw(base, "POST", "/msg", body={"m": msg("HALT")}),
        raw(base, "POST", "/msg", body={"m": msg("HALT;1;2")}),
    ]


def case_halt_warn(base):
    reset(base)
    a = raw(base, "POST", "/msg", body={"m": msg("HALT;AC-0001")})
    b = raw(base, "POST", "/msg", body={"m": msg("PING")})
    reset(base)
    return [a, b]


def case_halt_confirm_state(base):
    reset(base)
    a = raw(base, "POST", "/msg", body={"m": msg("PING")})
    b = raw(base, "POST", "/msg", body={"m": msg("HALT;1")})
    c = raw(base, "POST", "/msg", body={"m": msg("PING")})
    d = raw(base, "GET", "/health")
    reset(base)
    e = raw(base, "POST", "/msg", body={"m": msg("PING")})
    return [a, b, c, d, e]


def case_suggestion_near(base):
    return [raw(base, "POST", "/msg", body={"m": msg("ALTAX;A")})]


def case_suggestion_far(base):
    return [raw(base, "POST", "/msg", body={"m": msg("FOO;1")})]


def case_suggestion_halt(base):
    return [raw(base, "POST", "/msg", body={"m": msg("AALT;A")})]




BATTERY = [
    # P0-A protocolo
    ("P0-A-01", "protocolo", case_protocol_health),
    ("P0-A-02", "protocolo", case_protocol_health_unauth),
    ("P0-A-03", "protocolo", case_protocol_health_wrong_method),
    ("P0-A-04", "protocolo", case_protocol_msg_get),
    ("P0-A-05", "protocolo", case_protocol_reset_get),
    ("P0-A-06", "protocolo", case_protocol_options),
    ("P0-A-07", "protocolo", case_protocol_trailing_slash),
    ("P0-A-08", "protocolo", case_protocol_unknown),
    ("P0-A-09", "protocolo", case_protocol_unknown_unauth),
    ("P0-A-10", "protocolo", case_protocol_msg_no_auth),
    ("P0-A-11", "protocolo", case_protocol_msg_bad_token),
    ("P0-A-12", "protocolo", case_protocol_bearer_lowercase),
    ("P0-A-13", "protocolo", case_protocol_bearer_extra_space),
    ("P0-A-14", "protocolo", case_protocol_query_token),
    ("P0-A-15", "protocolo", case_protocol_query_key),
    # P0-B entrada
    ("P0-B-01", "entrada", case_json_empty),
    ("P0-B-02", "entrada", case_json_whitespace),
    ("P0-B-03", "entrada", case_json_malformed),
    ("P0-B-04", "entrada", case_json_string),
    ("P0-B-05", "entrada", case_json_array),
    ("P0-B-06", "entrada", case_json_null),
    ("P0-B-07", "entrada", case_json_number),
    ("P0-B-08", "entrada", case_json_bool),
    ("P0-B-09", "entrada", case_json_missing_m),
    ("P0-B-10", "entrada", case_json_m_int),
    ("P0-B-11", "entrada", case_json_m_null),
    ("P0-B-12", "entrada", case_json_m_array),
    ("P0-B-13", "entrada", case_json_m_object),
    ("P0-B-14", "entrada", case_json_extra_fields),
    ("P0-B-15", "entrada", case_size_exact_8192),
    ("P0-B-16", "entrada", case_size_over_8192),
    # P0-C integridad
    ("P0-C-01", "integridad", case_control_valid),
    ("P0-C-02", "integridad", case_control_invalid),
    ("P0-C-03", "integridad", case_control_malformed),
    ("P0-C-04", "integridad", case_control_missing),
    ("P0-C-05", "integridad", case_control_empty_segment),
    ("P0-C-06", "integridad", case_control_leading_zero),
    ("P0-C-07", "integridad", case_control_three_digits),
    ("P0-C-08", "integridad", case_control_zero),
    ("P0-C-09", "integridad", case_control_one),
    ("P0-C-10", "integridad", case_ping_no_checksum),
    ("P0-C-11", "integridad", case_ping_wrong_checksum),
    # P0-D negocio
    ("P0-D-01", "negocio", case_business_full_flow),
    ("P0-D-02", "negocio", case_transfer_exact_limit),
    ("P0-D-03", "negocio", case_transfer_over_limit),
    ("P0-D-04", "negocio", case_deposit_over_limit),
    ("P0-D-05", "negocio", case_precedence),
    ("P0-D-06", "negocio", case_negative_balance),
    ("P0-D-07", "negocio", case_unknown_command),
    ("P0-D-08", "negocio", case_arity),
    ("P0-D-09", "negocio", case_lowercase_account),
    ("P0-D-10", "negocio", case_duplicate_names),
    # P0-E secuencias
    ("P0-E-01", "secuencia", case_ids_not_consumed),
    ("P0-E-02", "secuencia", case_xreq_after_reset),
    ("P0-E-03", "secuencia", case_xreq_on_error),
    # P0-F extensión protocolo/auth
    ("P0-F-01", "protocolo", case_options_health),
    ("P0-F-02", "protocolo", case_options_reset),
    ("P0-F-03", "protocolo", case_head_health),
    ("P0-F-04", "protocolo", case_put_msg),
    ("P0-F-05", "protocolo", case_delete_msg),
    ("P0-F-06", "protocolo", case_auth_no_bearer),
    ("P0-F-07", "protocolo", case_auth_bearer_empty),
    ("P0-F-08", "protocolo", case_auth_bearer_leading_space),
    ("P0-F-09", "protocolo", case_health_trailing_slash),
    ("P0-F-10", "protocolo", case_msg_with_query),
    ("P0-F-11", "protocolo", case_content_type_missing),
    ("P0-F-12", "protocolo", case_content_type_text),
    ("P0-F-13", "protocolo", case_get_msg_with_auth),
    ("P0-F-14", "protocolo", case_reset_no_body),
    # P0-G extensión integridad/negocio
    ("P0-G-01", "integridad", case_control_98_valid),
    ("P0-G-02", "integridad", case_control_2_valid),
    ("P0-G-03", "integridad", case_control_plus),
    ("P0-G-04", "integridad", case_control_99),
    ("P0-G-05", "integridad", case_control_spaces),
    ("P0-G-06", "integridad", case_ping_empty_control),
    ("P0-G-07", "integridad", case_double_semicolon),
    ("P0-G-08", "integridad", case_m_empty_string),
    ("P0-G-09", "negocio", case_unicode_name),
    ("P0-G-10", "negocio", case_monto_plus),
    ("P0-G-11", "negocio", case_monto_space),
    ("P0-G-12", "negocio", case_leading_space_command),
    ("P0-G-13", "negocio", case_trailing_space_command),
    ("P0-G-14", "negocio", case_lowercase_command_valid),
    ("P0-G-15", "negocio", case_transfer_exact_balance),
    ("P0-G-16", "negocio", case_anula_transfer_after_spend),
    # P0-H HALT y sugerencias
    ("P0-H-01", "halt", case_halt_arity),
    ("P0-H-02", "halt", case_halt_warn),
    ("P0-H-03", "halt", case_halt_confirm_state),
    ("P0-H-04", "sugerencia", case_suggestion_near),
    ("P0-H-05", "sugerencia", case_suggestion_far),
    ("P0-H-06", "sugerencia", case_suggestion_halt),
]


def run_case(fn, base):
    try:
        return fn(base)
    except Exception as e:  # noqa: BLE001
        return [{"status": None, "body": None, "xreq": None, "error": f"{type(e).__name__}: {e}"}]


def _strip_xreq(transcript):
    if transcript is None:
        return None
    return [{k: v for k, v in step.items() if k != "xreq"} for step in transcript]


def compare(oracle_base, replica_base, battery, ignore_xreq=False):
    report = []
    divergences = []
    for cid, family, fn in battery:
        o = run_case(fn, oracle_base) if oracle_base else None
        r = run_case(fn, replica_base)
        oc = _strip_xreq(o) if ignore_xreq else o
        rc = _strip_xreq(r) if ignore_xreq else r
        match = (oc == rc) if o is not None else None
        entry = {"id": cid, "family": family, "oracle": o, "replica": r, "match": match}
        report.append(entry)
        if match is False:
            divergences.append(entry)
        flag = "SKIP" if match is None else ("OK" if match else "DIFF")
        print(f"[{flag}] {cid} ({family})")
        if match is False:
            for i, (oo, rr) in enumerate(zip(oc, rc)):
                if oo != rr:
                    print(f"    step {i}:")
                    print(f"      oracle : {json.dumps(oo, ensure_ascii=False)}")
                    print(f"      replica: {json.dumps(rr, ensure_ascii=False)}")
    return report, divergences


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--oracle", default=ORACLE_URL)
    ap.add_argument("--replica", default=REPLICA_URL)
    ap.add_argument("--replica-only", action="store_true")
    ap.add_argument("--ignore-xreq", action="store_true")
    ap.add_argument("--out", default="tools/diff_report.json")
    args = ap.parse_args()

    oracle_base = None if args.replica_only else args.oracle
    print(f"Oracle : {oracle_base or '(omitido)'}")
    print(f"Replica: {args.replica}")
    print(f"Casos  : {len(BATTERY)}   ignore-xreq={args.ignore_xreq}\n")

    report, divergences = compare(oracle_base, args.replica, BATTERY, args.ignore_xreq)

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\n=== RESUMEN ===")
    if oracle_base:
        total = len(report)
        ok = sum(1 for e in report if e["match"] is True)
        diff = len(divergences)
        print(f"Coinciden: {ok}/{total}   Divergencias: {diff}")
        for e in divergences:
            print(f"  - {e['id']} ({e['family']})")
    else:
        print(f"Casos ejecutados contra réplica: {len(report)}")
    print(f"Reporte: {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
