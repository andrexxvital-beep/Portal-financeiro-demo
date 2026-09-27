"""Etapa C1: gera os CSV de carga das 2 empresas falsas.

Le os JSON no formato do Omie e escreve carga_*.csv para o
COPY do Postgres (CSV nao tem risco de injecao de SQL).
"""
import csv
import json
from datetime import datetime

from visual import GRUPOS

EMPRESAS = [(1, "Loja Modelo Ltda", "omie_falso.json"),
            (2, "Padaria Sol Nascente", "omie_padaria.json")]


def dia(s):
    if not s:
        return ""
    return datetime.strptime(s, "%d/%m/%Y").strftime(
        "%Y-%m-%d")


def grava(nome, linhas):
    with open(nome, "w", encoding="utf-8", newline="") as f:
        csv.writer(f).writerows(linhas)
    print(f"{nome}: {len(linhas)} linhas")


emp, cat, tit = [], [], []
for eid, nome, arq in EMPRESAS:
    with open(arq, encoding="utf-8") as f:
        d = json.load(f)
    emp.append((eid, nome))
    for c in d["categorias"]["categoria_cadastro"]:
        g = GRUPOS.get(c["descricao"], "")
        cat.append((eid, c["codigo"], c["descricao"], g))
    for m in d["movimentos"]["movimentos"]:
        t = m["detalhes"]
        tit.append((eid, t["nCodTitulo"], t["cNatureza"],
                    t["cCodCateg"],
                    m["departamentos"][0]["cCodDepartamento"],
                    dia(t["dDtVenc"]), dia(t["dDtPagamento"]),
                    round(t["nValorTitulo"] * 100)))
grava("carga_empresa.csv", emp)
grava("carga_categoria.csv", cat)
grava("carga_titulo.csv", tit)
