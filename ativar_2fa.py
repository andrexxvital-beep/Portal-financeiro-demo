"""Etapa C3: liga o codigo do celular (2FA) de um login.

Gera um segredo novo, mostra para colar no app autenticador
e so grava depois que o codigo do app confere. Grava pelo
usuario postgres (sudo): o app nao escreve em usuario.
"""
import subprocess

import dois

email = input("Email do login: ").strip().lower()
seg = dois.novo_segredo()
print()
print("No app autenticador: + > Inserir chave")
print("Nome : Portal", email)
print("Chave:", seg)
print("Tipo : baseado em tempo (TOTP), 6 digitos, 30 s")
print()
print("Ou abra este link no celular:")
print(dois.link(seg, email))
print()
for _ in range(3):
    c = input("Codigo que o app mostra agora: ")
    if dois.confere(seg, c):
        break
    print("Nao confere. Espere o proximo codigo.")
else:
    raise SystemExit("ERRO: 2FA nao ligado. Confira a "
                     "chave e o relogio (timedatectl).")
sql = ("UPDATE usuario SET totp = :'seg' "
       "WHERE email = :'email';\n")
r = subprocess.run(["sudo", "-u", "postgres", "psql",
                    "-d", "portal", "-v", "ON_ERROR_STOP=1",
                    "-v", f"email={email}", "-v",
                    f"seg={seg}"], input=sql, text=True,
                   capture_output=True)
if r.stdout.strip() != "UPDATE 1":
    raise SystemExit("ERRO: email nao encontrado "
                     + r.stderr.strip())
print("OK 2FA ligado:", email)
