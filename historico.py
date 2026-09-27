"""Etapa E1: 18 meses de historico + centros de custo.

Completa o JSON falso do Omie com jan/2025 a jun/2026 (para
comparar periodos) e reparte os titulos em centros de custo:
LOJA, DELIVERY, ADM e SOCIOS. Os titulos de jul a set/2026
ficam iguais; so julho ganha o que foi vendido a prazo em
junho. Uso: python3 historico.py ARQ SEMENTE
"""
import json
import random
import sys
from datetime import date, timedelta

ARQ, SEM = sys.argv[1], int(sys.argv[2])
# codigo: (min, max) R$, vezes por mes, prazo (gerar_omie)
CATS = {"1.01.01": (200, 800, 12, 0),
        "1.01.02": (200, 800, 12, 30),
        "1.01.03": (300, 900, 3, 28),
        "2.01.01": (500, 1400, 3, 21),
        "2.02.01": (1800, 1800, 1, 10),
        "2.02.02": (90, 260, 4, 10),
        "2.02.03": (15, 45, 4, 0),
        "2.03.01": (150, 450, 3, 0),
        "2.03.02": (100, 250, 5, 0),
        "2.03.03": (60, 180, 3, 0),
        "2.03.04": (40, 120, 2, 0)}
ADM = {"2.02.01", "2.02.02", "2.02.03"}
DIVIDE = {"1.01.01", "1.01.02", "1.01.03", "2.01.01"}
FIXO = {"2.02.02", "2.02.03"}
SAZ = [.9, .9, 1, 1, 1.05, 1, 1, 1, 1, 1.05, 1.1, 1.3]

with open(ARQ, encoding="utf-8") as f:
    d = json.load(f)
movs = d["movimentos"]["movimentos"]
if any(m["detalhes"]["nCodTitulo"] >= 5000 for m in movs):
    raise SystemExit(f"{ARQ}: historico ja existe")
rnd = random.Random(SEM)


def cc(cod):
    if cod.startswith("2.03"):
        return "SOCIOS"
    if cod in ADM:
        return "ADM"
    if cod in DIVIDE and rnd.random() < .3:
        return "DELIVERY"
    return "LOJA"


def br(x):
    return x.strftime("%d/%m/%Y") if x else ""


def titulo(n, cod, emi, valor):
    nat = "R" if cod[0] == "1" else "P"
    venc = emi + timedelta(days=CATS[cod][3])
    pago = venc + timedelta(days=rnd.choice([0, 0, 1]))
    if cod == "1.01.03" and rnd.random() < .06:
        pago = None  # calote antigo (inadimplencia 60+)
    st = ("ATRASADO" if not pago else
          "RECEBIDO" if nat == "R" else "PAGO")
    return {
        "detalhes": {
            "nCodTitulo": n, "cCodCateg": cod,
            "cNatureza": nat,
            "cGrupo": ("CONTA_A_RECEBER" if nat == "R"
                       else "CONTA_A_PAGAR"),
            "cStatus": st, "dDtEmissao": br(emi),
            "dDtVenc": br(venc), "dDtPagamento": br(pago),
            "nValorTitulo": valor},
        "resumo": {"nValPago": valor if pago else 0,
                   "nValAberto": 0 if pago else valor},
        "departamentos": [{"cCodDepartamento": cc(cod),
                           "nDistrPercentual": 100}]}


for m in movs:
    m["departamentos"][0]["cCodDepartamento"] = cc(
        m["detalhes"]["cCodCateg"])
meses = [(2024, 12)] + [(2025, i) for i in range(1, 13)]
meses += [(2026, i) for i in range(1, 7)]
INICIO = date(2025, 1, 1)  # dez/2024 so p/ vendas a prazo
n = 5000
for k, (ano, mes) in enumerate(meses):
    cresce = .8 + .2 * k / (len(meses) - 1)
    for cod, (a, b, vezes, _) in CATS.items():
        f = cresce * SAZ[mes - 1]
        if cod in FIXO or cod.startswith("2.03"):
            f = 1
        for _ in range(vezes):
            if cod == "2.02.01":
                emi = date(ano, mes, 5)
                v = 1800.0 if ano == 2026 else 1650.0
            else:
                emi = date(ano, mes, rnd.randint(1, 28))
                v = round(rnd.uniform(a, b) * f, 2)
            t = titulo(n, cod, emi, v)
            if emi + timedelta(days=CATS[cod][3]) >= INICIO:
                movs.append(t)
                n += 1
movs.sort(key=lambda m: m["detalhes"]["nCodTitulo"])
d["movimentos"]["nRegistros"] = len(movs)
d["movimentos"]["nTotRegistros"] = len(movs)
with open(ARQ, "w", encoding="utf-8") as f:
    json.dump(d, f, ensure_ascii=False, indent=1)
print(f"OK {ARQ}: {len(movs)} titulos")
