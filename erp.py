"""Etapa F1: liga cada empresa ao ERP e sincroniza.

Guarda a chave do ERP cifrada (cofre.py), baixa os dados
(omie.py) e troca os titulos da empresa numa transacao so.
Tambem roda sozinho (ex.: todo dia no cron):
  .venv/bin/python erp.py 2      (empresa 2)
"""
import sys
import time

import psycopg
from psycopg.types.json import Jsonb

import cofre
import omie
from omie import ErroErp

ESPERA = 60  # o Omie recusa a mesma consulta em < 60 s
ultima = {}  # empresa -> hora da ultima tentativa


def db(sql, args=()):
    with psycopg.connect("dbname=portal") as c:
        return c.execute(sql, args).fetchall()


def conexao(eid):
    """(app_key, segredo cifrado, ultima_sync, status)."""
    r = db("SELECT * FROM bpo_erp(%s)", (eid,))
    return r[0] if r else None


def salva(eid, key, secret):
    key = key.strip()
    if key.lower() == "demo":  # teclado do celular: Demo
        key = "demo"
    db("SELECT bpo_salva_erp(%s, %s, %s)",
       (eid, key, cofre.cifra(secret.strip())))


def sincroniza(eid):
    """Baixa do ERP e grava. Devolve quantos titulos."""
    c = conexao(eid)
    if not c:
        raise ErroErp("ERP ainda não cadastrado")
    try:
        falta = ultima.get(eid, 0) + ESPERA - time.time()
        if falta > 0 and c[0] != "demo":
            raise ErroErp(f"espere {falta:.0f} s, o Omie "
                          "recusa repetir em menos de 1 min")
        ultima[eid] = time.time()
        cats, tits = omie.baixa(c[0], cofre.decifra(c[1]))
        if not tits:
            raise ErroErp("O ERP não devolveu nenhum título "
                          "(nada foi apagado)")
    except (ErroErp, ValueError, KeyError) as e:
        msg = str(e) if not isinstance(e, KeyError) else \
            f"resposta sem o campo {e}"
        msg = msg.rstrip(". ")  # a tela poe o ponto final
        db("SELECT bpo_erp_status(%s, %s)",
           (eid, "erro: " + msg))
        raise ErroErp(msg)
    return db("SELECT bpo_carga(%s, %s, %s)",
              (eid, Jsonb(cats), Jsonb(tits)))[0][0]


if __name__ == "__main__":
    try:
        n = sincroniza(int(sys.argv[1]))
    except (IndexError, ValueError):
        raise SystemExit("uso: erp.py ID_DA_EMPRESA")
    except ErroErp as e:
        raise SystemExit(f"ERRO: {e}")
    print(f"OK empresa {sys.argv[1]}: {n} titulos")
