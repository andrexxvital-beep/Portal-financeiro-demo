"""Etapa C3: codigo de 6 digitos do celular (2FA, TOTP).

Mesmo padrao do Google Authenticator e do Aegis (RFC 6238):
o celular e o notebook guardam o mesmo segredo e, a cada
30 s, calculam o mesmo numero a partir do relogio.
"""
import base64
import hmac
import secrets
import struct
import time
from urllib.parse import quote

PASSO = 30


def novo_segredo():
    return base64.b32encode(secrets.token_bytes(20)).decode()


def codigo(seg, passo):
    k = base64.b32decode(seg)
    h = hmac.new(k, struct.pack(">Q", passo), "sha1").digest()
    o = h[-1] & 15
    n = int.from_bytes(h[o:o + 4], "big") & 0x7FFFFFFF
    return f"{n % 1_000_000:06d}"


def confere(seg, digitado, ultimo=0):
    """Devolve o passo aceito (ou 0). Aceita 30 s de folga
    no relogio e nunca o mesmo codigo duas vezes."""
    digitado = "".join(c for c in digitado if c.isdigit())
    if len(digitado) != 6 or not seg:
        return 0
    agora = int(time.time()) // PASSO
    for p in (agora - 1, agora, agora + 1):
        if p > ultimo and hmac.compare_digest(
                codigo(seg, p), digitado):
            return p
    return 0


def link(seg, email):
    rot = quote(f"Portal Financeiro:{email}")
    return (f"otpauth://totp/{rot}?secret={seg}"
            "&issuer=Portal%20Financeiro")
