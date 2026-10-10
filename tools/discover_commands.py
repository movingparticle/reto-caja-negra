#!/usr/bin/env python3
"""Descubre comandos ocultos del oráculo. Un comando conocido NO responde E301
(comando desconocido), sino otra cosa (éxito o aridad inválida E302)."""
import json
import urllib.error
import urllib.request

TOKEN = "REDACTED_TEAM_TOKEN"
URL = "https://caja-negra-production-c64f.up.railway.app/msg"
UA = "Mozilla/5.0 Frontier-Cmd-Discovery/1.0"

CANDIDATES = [
    # conocidos de referencia
    "PING", "ALTA", "CONSULTA", "DEPOSITO", "TRANSFER", "ANULA",
    # sospechosos descubiertos
    "HALT", "STOP", "KILL", "SHUTDOWN", "PAUSE",
    # banco / dominio
    "SALDO", "SALDOS", "LISTA", "LISTAR", "RETIRO", "RETIRAR", "EXTRACTO",
    "HISTORIAL", "ESTADO", "STATUS", "INFO", "CUENTAS", "OPERACIONES",
    "CREAR", "ABRIR", "CERRAR", "CIERRA", "BORRAR", "ELIMINAR", "BLOQUEAR",
    "DESBLOQUEAR", "ACTIVAR", "DESACTIVAR", "REVERTIR", "REVERSO", "REEMBOLSO",
    "PAGO", "PAGAR", "COBRO", "COBRAR", "DEBITO", "CREDITO", "INTERES",
    "COMISION", "LIMITE", "RESET", "REINICIAR", "AYUDA", "HELP", "VERSION",
    "DEBUG", "ADMIN", "CONFIG", "ECHO", "PONG", "VER", "MOSTRAR", "DAME",
]

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


print(f"{'CMD':14s} {'ST':4s} RESPONSE")
print("-" * 80)
known = []
for c in CANDIDATES:
    payload = f"{c}"          # aridad 0 -> conocido da E302, desconocido da E301
    body = json.dumps({"m": f"{payload};{cc(payload)}"}).encode()
    req = urllib.request.Request(URL, data=body, headers={
        "Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json", "User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            st, resp = r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        st, resp = e.code, json.loads(e.read().decode())
    is_unknown = isinstance(resp, dict) and resp.get("error") == "E301"
    tag = "" if is_unknown else "   <<< KNOWN / NO-E301"
    if not is_unknown:
        known.append(c)
    print(f"{c:14s} {st:<4} {json.dumps(resp, ensure_ascii=False)}{tag}")

print("\nComandos que NO son E301:", known)
