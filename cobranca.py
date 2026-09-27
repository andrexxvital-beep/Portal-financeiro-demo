"""Etapa G1: cobranca (Pix/boleto) pelo Asaas DO CLIENTE.

O pagador paga direto na conta do cliente no Asaas; o
portal so pede a cobranca e recebe o aviso de pago
(webhook). Ninguem aqui toca no dinheiro.
- chave da API: cifrada (cofre.py), nunca volta a tela;
- token do aviso: mostrado 1 vez, no banco so o hash;
- aviso so vale se o token bater (comparacao no banco).
Demonstracao: chave "demo" (sem internet).
"""
import hashlib
import json
import secrets
import urllib.error
import urllib.request
from datetime import date

import psycopg

import cofre
from dados import HOJE

URL = "https://api.asaas.com/v3/"
TESTE = "https://api-sandbox.asaas.com/v3/"
TIPOS = ("PIX", "BOLETO")
# Pix e boleto: RECEIVED = dinheiro na conta do cliente
PAGO = {"PAYMENT_RECEIVED", "PAYMENT_CONFIRMED"}
FORA = {"PAYMENT_DELETED", "PAYMENT_REFUNDED"}


class ErroPsp(Exception):
    """Mensagem que pode ir para a tela (sem segredos)."""


def db(sql, args=()):
    with psycopg.connect("dbname=portal") as c:
        return c.execute(sql, args).fetchall()


def hash_tok(tok):
    return hashlib.sha256(tok.encode()).hexdigest()


def salva(eid, chave):
    """Guarda a chave cifrada; devolve o token novo."""
    chave = chave.strip()
    if chave.lower() == "demo":
        chave = "demo"
    tok = secrets.token_urlsafe(32)  # Asaas: 32 a 255
    db("SELECT bpo_salva_psp(%s, %s, %s)",
       (eid, cofre.cifra(chave), hash_tok(tok)))
    return tok


def conexao(eid):
    """(chave aberta, atualizado, hash do token)."""
    r = db("SELECT * FROM bpo_psp(%s)", (eid,))
    if not r:
        return None
    return cofre.decifra(r[0][0]), r[0][1], r[0][2]


def abertos(eid, n=12):
    return db("SELECT * FROM bpo_abertos(%s, %s)",
              (eid, n))


def chama(chave, metodo, rota, corpo=None):
    base = TESTE if "_hmlg_" in chave else URL
    dado = json.dumps(corpo).encode() if corpo else None
    req = urllib.request.Request(
        base + rota, dado, method=metodo, headers={
            "access_token": chave,
            "Content-Type": "application/json",
            "User-Agent": "portal-financeiro"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        try:
            er = json.load(e).get("errors") or [{}]
            msg = er[0].get("description")
        except ValueError:
            msg = None
        raise ErroPsp("Asaas: " + (msg or f"HTTP {e.code}")
                      [:150])
    except (urllib.error.URLError, TimeoutError):
        raise ErroPsp("Sem conexão com o Asaas")


def gera(eid, tid, tipo):
    """Cria a cobranca do titulo tid. Devolve o id."""
    if tipo not in TIPOS:
        raise ErroPsp("Tipo de cobrança inválido")
    c = conexao(eid)
    if not c:
        raise ErroPsp("Asaas ainda não cadastrado")
    t = [x for x in abertos(eid, 500) if x[0] == tid]
    if not t or t[0][5] in ("pendente", "paga"):
        raise ErroPsp("Título já cobrado ou já pago")
    valor = t[0][2]
    if c[0] == "demo":
        pid, link = "demo_" + secrets.token_hex(6), None
    else:
        raise ErroPsp("Asaas real: falta o cliente do "
                      "título (próxima etapa)")
    ok = db("SELECT bpo_cobranca(%s, %s, %s, %s, %s, %s)",
            (eid, tid, pid, tipo, valor, link))[0][0]
    if not ok:
        raise ErroPsp("O título mudou no ERP; sincronize")
    return pid


def simula(eid, pid):
    """So na demonstracao: faz o papel do Asaas."""
    c = conexao(eid)
    if not c or c[0] != "demo":
        raise ErroPsp("Simular só vale na demonstração")
    r = db("SELECT psp_aviso(%s, %s, 'paga', %s)",
           (c[2], pid, min(date.today(), HOJE)))
    return r[0][0] if r else None


def aviso(tok, corpo):
    """Webhook do Asaas. Devolve a empresa ou None."""
    if not tok or len(tok) > 200:
        return None
    ev = corpo.get("event")
    p = corpo.get("payment")
    if not isinstance(p, dict):
        return None
    pid = p.get("id")
    if ev in PAGO:
        st = "paga"
    elif ev in FORA:
        st = "cancelada"
    else:
        return None  # outros avisos: nada a fazer
    if not isinstance(pid, str) or len(pid) > 60:
        return None
    try:
        dia = date.fromisoformat(
            p.get("paymentDate") or p.get("clientPaymentDate")
            or date.today().isoformat())
    except (TypeError, ValueError):
        dia = date.today()
    r = db("SELECT psp_aviso(%s, %s, %s, %s)",
           (hash_tok(tok), pid, st, dia))
    return r[0][0] if r else None
