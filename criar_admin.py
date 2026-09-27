"""Etapa D1: cria o login do BPO (admin), com 2FA ja ligado.

Pede email e senha, mostra a chave para o app autenticador
e so grava depois que o codigo confere. Grava pelo usuario
postgres (sudo): o app nao escreve na tabela bpo_admin.
"""
import getpass
import hashlib
import secrets
import subprocess

import dois

email = input("Email do BPO: ").strip().lower()
s1 = getpass.getpass("Senha (min. 12 letras): ")
s2 = getpass.getpass("Repita a senha: ")
if s1 != s2 or len(s1) < 12 or "@" not in email:
    raise SystemExit("ERRO: senhas diferentes, curtas "
                     "ou email invalido")
sal = secrets.token_bytes(16)
h = hashlib.pbkdf2_hmac("sha256", s1.encode(), sal, 300_000)
senha = f"300000${sal.hex()}${h.hex()}"
seg = dois.novo_segredo()
print()
print("No app autenticador: + > Inserir chave")
print("Nome : BPO", email)
print("Chave:", seg)
print()
for _ in range(3):
    if dois.confere(seg, input("Codigo do app agora: ")):
        break
    print("Nao confere. Espere o proximo codigo.")
else:
    raise SystemExit("ERRO: admin nao criado. Confira a "
                     "chave e o relogio (timedatectl).")
sql = ("INSERT INTO bpo_admin (email, senha, totp) "
       "VALUES (:'email', :'senha', :'seg');\n")
r = subprocess.run(["sudo", "-u", "postgres", "psql",
                    "-d", "portal", "-v", "ON_ERROR_STOP=1",
                    "-v", f"email={email}", "-v",
                    f"senha={senha}", "-v", f"seg={seg}"],
                   input=sql, text=True, capture_output=True)
if r.stdout.strip() != "INSERT 0 1":
    raise SystemExit("ERRO: " + r.stderr.strip())
print("OK admin do BPO criado:", email)
