"""Etapa 4a: gera omie_falso.json no formato do Omie.

Imita as respostas de ListarCategorias e ListarMovimentos
(modulo financas). Dados inventados, semente fixa.
"""
import json
import random
from datetime import date, timedelta

random.seed(2026)
HOJE = date(2026, 9, 26)
MESES = [(2026, 7), (2026, 8), (2026, 9)]
# codigo, descricao, natureza, depto, (min, max) R$,
# vezes por mes,
# prazo em dias entre emissao e vencimento
CATS = [
    ("1.01.01", "Vendas Pix", "R", "LOJA", (200, 800), 12, 0),
    ("1.01.02", "Vendas cartao", "R", "LOJA", (200, 800), 12,
     30),
    ("1.01.03", "Vendas boleto", "R", "LOJA", (300, 900), 3,
     28),
    ("2.01.01", "Fornecedores", "P", "LOJA", (500, 1400), 3,
     21),
    ("2.02.01", "Aluguel", "P", "LOJA", (1800, 1800), 1, 10),
    ("2.02.02", "Contas da loja", "P", "LOJA", (90, 260), 4,
     10),
    ("2.02.03", "Banco", "P", "LOJA", (15, 45), 4, 0),
    ("2.03.01", "Mercado", "P", "SOCIOS", (150, 450), 3, 0),
    ("2.03.02", "Familia", "P", "SOCIOS", (100, 250), 5, 0),
    ("2.03.03", "Comida", "P", "SOCIOS", (60, 180), 3, 0),
    ("2.03.04", "Saude", "P", "SOCIOS", (40, 120), 2, 0)]


def br(d):
    return d.strftime("%d/%m/%Y") if d else ""


def titulo(n, cod, nat, depto, emi, venc, valor):
    pago = None
    if venc <= HOJE:
        pago = venc + timedelta(days=random.choice([0, 0, 1]))
        # 1 em 4 boletos de cliente atrasa (inadimplencia)
        if cod == "1.01.03" and random.random() < .25:
            pago = None
        if pago and pago > HOJE:
            pago = None
    if pago:
        st = "RECEBIDO" if nat == "R" else "PAGO"
    elif venc < HOJE:
        st = "ATRASADO"
    elif venc == HOJE:
        st = "VENCE HOJE"
    else:
        st = "A VENCER"
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
        "departamentos": [{"cCodDepartamento": depto,
                           "nDistrPercentual": 100}]}


movs, n = [], 1000
for ano, mes in MESES:
    for cod, _, nat, depto, (a, b), vezes, prazo in CATS:
        for _ in range(vezes):
            dia = 5 if cod == "2.02.01" else random.randint(
                1, 28)
            emi = date(ano, mes, dia)
            if emi > HOJE:
                continue
            valor = round(random.uniform(a, b), 2)
            venc = emi + timedelta(days=prazo)
            movs.append(titulo(n, cod, nat, depto, emi, venc,
                               valor))
            n += 1
# contas de outubro ja lancadas (caixa projetado)
for cod, dia, valor in [("2.02.01", 5, 1800.0),
                        ("2.01.01", 12, 1150.0),
                        ("2.02.02", 10, 240.0)]:
    v = date(2026, 10, dia)
    movs.append(titulo(n, cod, "P", "LOJA", HOJE, v, valor))
    n += 1
movs.sort(key=lambda m: m["detalhes"]["nCodTitulo"])
cad = [{"codigo": c[0], "descricao": c[1],
        "natureza": c[2]} for c in CATS]
dados = {
    "categorias": {"pagina": 1, "total_de_paginas": 1,
                   "registros": len(cad),
                   "categoria_cadastro": cad},
    "movimentos": {"nPagina": 1, "nTotPaginas": 1,
                   "nRegistros": len(movs),
                   "nTotRegistros": len(movs),
                   "movimentos": movs}}
with open("omie_falso.json", "w", encoding="utf-8") as f:
    json.dump(dados, f, ensure_ascii=False, indent=1)
print("OK omie_falso.json:", len(movs), "titulos")
