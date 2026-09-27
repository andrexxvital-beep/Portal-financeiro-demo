"""Etapa C2: cria o login de um cliente numa empresa.

Pergunta email, empresa e senha (a senha nao aparece),
gera o hash PBKDF2 e grava pelo usuario postgres (sudo).
O app nao tem permissao de escrever na tabela de senhas.
"""
import getpass
import hashlib
import secrets
import subprocess

ITER = 300_000
email = input("Email do cliente: ").strip().lower()
eid = int(input("Empresa (1 = Loja, 2 = Padaria): "))
s1 = getpass.getpass("Senha (min. 10 letras): ")
s2 = getpass.getpass("Repita a senha: ")
if s1 != s2 or len(s1) < 10 or "@" not in email:
    raise SystemExit("ERRO: senhas diferentes, curtas "
                     "ou email invalido")
sal = secrets.token_bytes(16)
h = hashlib.pbkdf2_hmac("sha256", s1.encode(), sal, ITER)
guardado = f"{ITER}${sal.hex()}${h.hex()}"
sql = ("INSERT INTO usuario (empresa_id, email, senha) "
       "VALUES (:eid, :'email', :'senha');\n")
subprocess.run(["sudo", "-u", "postgres", "psql", "-q",
                "-d", "portal", "-v", "ON_ERROR_STOP=1",
                "-v", f"eid={eid}", "-v", f"email={email}",
                "-v", f"senha={guardado}"],
               input=sql, text=True, check=True)
print("OK login criado:", email, "-> empresa", eid)
