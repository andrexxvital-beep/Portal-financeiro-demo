"""Etapa F1: cofre das chaves do ERP (Fernet: AES + HMAC).

O segredo do ERP (app_secret) vai para o banco so cifrado.
A chave que abre o cofre fica em erp.key (permissao 600),
fora do banco: quem copiar so o banco nao le os segredos.
Criar a chave 1 vez: python3 cofre.py nova-chave
"""
import os
import sys

from cryptography.fernet import Fernet, InvalidToken

ARQ = os.environ.get("ERP_CHAVE", "erp.key")


def _f():
    with open(ARQ, "rb") as f:
        return Fernet(f.read().strip())


def cifra(texto):
    return _f().encrypt(texto.encode())


def decifra(dado):
    try:
        return _f().decrypt(bytes(dado)).decode()
    except InvalidToken:
        raise ValueError("chave do cofre nao abre este "
                         "segredo (erp.key trocada?)")


if __name__ == "__main__":
    if sys.argv[1:] != ["nova-chave"]:
        raise SystemExit("uso: python3 cofre.py nova-chave")
    if os.path.exists(ARQ):
        raise SystemExit(f"ERRO: {ARQ} ja existe (trocar "
                         "a chave perde os segredos salvos)")
    fd = os.open(ARQ, os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                 0o600)
    with os.fdopen(fd, "wb") as f:
        f.write(Fernet.generate_key())
    print("OK", ARQ, "criada (so o seu usuario le)")
