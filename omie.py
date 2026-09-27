"""Etapa F1: cliente da API do Omie (so leitura).

Busca categorias, departamentos e titulos (ListarMovimentos)
e devolve no formato do banco. So usa a biblioteca padrao.
Limites do Omie: 100 registros por pagina, mesma consulta
so 1x por minuto, 10 erros seguidos = bloqueio de 30 min;
conta de teste: 100 chamadas por dia.
Modo demonstracao: app_key "demo" e app_secret com o nome
de um JSON local (omie_*.json), sem internet.
"""
import json
import re
import time
import urllib.error
import urllib.request
from datetime import datetime

URL = "https://app.omie.com.br/api/v1/"
POR_PAGINA = 100  # maximo do Omie por pagina
PAUSA = 0.4  # segundos entre paginas (limite da API)
DEMO = re.compile(r"omie_[a-z0-9_]{1,40}\.json")


class ErroErp(Exception):
    """Mensagem que pode ir para a tela (sem segredos)."""


def chama(rota, call, param, key, secret):
    corpo = json.dumps({"call": call, "app_key": key,
                        "app_secret": secret,
                        "param": [param]}).encode()
    req = urllib.request.Request(
        URL + rota, corpo, method="POST",
        headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            d = json.load(r)
    except urllib.error.HTTPError as e:
        if e.code == 425:
            raise ErroErp("Omie bloqueou por 30 min depois "
                          "de 10 erros seguidos")
        try:
            d = json.load(e)
        except ValueError:
            raise ErroErp(f"Omie respondeu HTTP {e.code}")
    except (urllib.error.URLError, TimeoutError):
        raise ErroErp("Sem conexão com o Omie")
    if "faultstring" in d:
        raise ErroErp("Omie: " + str(d["faultstring"])[:150])
    return d


def paginas(rota, call, key, secret, lista, total,
            ppag="pagina", preg="registros_por_pagina"):
    """Junta todas as paginas de uma listagem."""
    itens, p = [], 1
    while True:
        d = chama(rota, call, {ppag: p, preg: POR_PAGINA},
                  key, secret)
        itens += d.get(lista) or []
        if p >= int(d.get(total) or 1):
            return itens
        p += 1
        time.sleep(PAUSA)


def dia(s):
    if not s:
        return None
    return datetime.strptime(s, "%d/%m/%Y").strftime(
        "%Y-%m-%d")


def converte(cats, deps, movs):
    """-> (categorias usadas, titulos) para o bpo_carga."""
    nome_dep = {str(x.get("codigo")): x.get("descricao")
                for x in deps}
    nome_cat = {c["codigo"]: c["descricao"] for c in cats}
    tits, usadas = [], set()
    for m in movs:
        t = m["detalhes"]
        ds = m.get("departamentos") or [{}]
        dep = str(ds[0].get("cCodDepartamento") or "SEM")
        cod = t.get("cCodCateg") or "SEM"
        usadas.add(cod)
        tits.append({
            "id": t["nCodTitulo"], "nat": t["cNatureza"],
            "cat": cod,
            "depto": nome_dep.get(dep) or dep,
            "venc": dia(t["dDtVenc"]),
            "pag": dia(t.get("dDtPagamento")),
            "valor": round(float(t["nValorTitulo"]) * 100)})
    out = [{"codigo": c, "nome": nome_cat.get(c, c)}
           for c in sorted(usadas)]
    return out, tits


def baixa(key, secret):
    """Le tudo do Omie (ou do JSON demo) e converte."""
    if key == "demo":
        if not DEMO.fullmatch(secret):
            raise ErroErp("Demo: use o nome de um arquivo "
                          "omie_*.json")
        try:
            with open(secret, encoding="utf-8") as f:
                d = json.load(f)
        except OSError:
            raise ErroErp(f"Demo: {secret} não existe")
        return converte(
            d["categorias"]["categoria_cadastro"], [],
            d["movimentos"]["movimentos"])
    cats = paginas("geral/categorias/", "ListarCategorias",
                   key, secret, "categoria_cadastro",
                   "total_de_paginas")
    try:  # so para mostrar o nome do centro de custo
        deps = paginas("geral/departamentos/",
                       "ListarDepartamentos", key, secret,
                       "departamentos", "total_de_paginas")
    except ErroErp:
        deps = []
    movs = paginas("financas/mf/", "ListarMovimentos", key,
                   secret, "movimentos", "nTotPaginas",
                   "nPagina", "nRegPorPagina")
    return converte(cats, deps, movs)
