"""Etapa C2: le do Postgres os dados de 1 empresa.

Entra como o usuario do Linux (sem senha no codigo) e marca
a empresa na transacao; o banco (RLS) so devolve as linhas
dela. Monta o mesmo resumo que o painel ja sabe desenhar.
"""
import time
from datetime import date

import psycopg

HOJE = date(2026, 9, 26)  # os dados falsos param aqui
FAIXAS = ["a_vencer", "1-30", "31-60", "60+"]


def filtrado(nome, cats, tits, ccs, cc, cat):
    """Resumo + opcoes do filtro para a tela."""
    ctx, d = montar(nome, cats, tits)
    ctx["hoje"] = HOJE  # ate quando vao os dados
    ctx["filtro"] = {
        "cc": cc, "cat": cat, "ccs": ccs,
        "cats": sorted(((k, n) for k, n, _ in cats),
                       key=lambda x: x[1])}
    return ctx, d


def faixa(venc):
    atraso = (HOJE - venc).days
    if atraso <= 0:
        return "a_vencer"
    if atraso <= 30:
        return "1-30"
    return "31-60" if atraso <= 60 else "60+"


def abre(cur, eid):
    cur.execute("SELECT set_config('app.empresa', %s, true)",
                (str(eid) if eid else "",))


def montar(nome, cats, tits):
    """cats: (codigo, nome, grupo); tits: linhas do banco."""
    nm = {c: n for c, n, _ in cats}
    meses, cs, prev, lin = {}, {}, {}, []
    ab = {k: dict.fromkeys(FAIXAS, 0) for k in "RP"}
    venc_r = atraso_r = 0
    proj = {"entra": 0, "sai": 0}
    for nat, cod, dep, venc, pago, c in tits:
        cat = nm.get(cod, cod)
        pv = prev.setdefault(venc.strftime("%m/%Y"),
                             {"entra": 0, "sai": 0})
        pv["entra" if nat == "R" else "sai"] += c
        if nat == "R" and venc <= HOJE:
            venc_r += c
            atraso_r += 0 if pago else c
        if not pago:
            ab[nat][faixa(venc)] += c
            if venc > HOJE and venc.month != HOJE.month:
                proj["entra" if nat == "R" else "sai"] += c
            continue
        mm = meses.setdefault(pago.strftime("%m/%Y"), {
            "entra": 0, "sai_empresa": 0, "sai_pessoal": 0})
        if nat == "R":
            mm["entra"] += c
        elif dep == "SOCIOS":
            mm["sai_pessoal"] -= c
        else:
            mm["sai_empresa"] -= c
        s = c if nat == "R" else -c
        cs[cat] = cs.get(cat, 0) + s
        lin.append((pago, cat, s))
    lista = []
    for k in sorted(meses, key=lambda x: x[3:] + x[:2]):
        mm = meses[k]
        mm["saldo"] = sum(mm.values())
        lista.append({"mes": k, **mm})
    d = {"categorias": dict(sorted(cs.items())),
         "meses": lista,
         "abertos": {"receber": ab["R"], "pagar": ab["P"]},
         "inadimplencia_pct": round(
             100 * atraso_r / (venc_r or 1), 1),
         "projetado": proj,
         "previsto": dict(sorted(
             prev.items(),
             key=lambda kv: kv[0][3:] + kv[0][:2]))}
    ctx = {"empresa": nome, "lin": sorted(lin),
           "grupos": {n: g for _, n, g in cats if g},
           "at": time.time()}
    return ctx, d


def carregar(eid, cc=None, cat=None):
    """(ctx, resumo) da empresa eid, direto do banco.
    cc e cat: filtro de centro de custo e categoria
    (so aceita valores que existem na empresa)."""
    with psycopg.connect("dbname=portal") as c:
        cur = c.cursor()
        abre(cur, eid)
        cur.execute("SELECT nome FROM empresa")
        nome = cur.fetchone()[0]
        cur.execute("SELECT codigo, nome, grupo "
                    "FROM categoria")
        cats = cur.fetchall()
        cur.execute("SELECT DISTINCT depto FROM titulo")
        ccs = [x[0] for x in cur.fetchall()]
        cc = cc if cc in ccs else None
        cat = cat if cat in {x[0] for x in cats} else None
        # pago no Asaas vale ate o ERP dar a baixa
        cur.execute("SELECT natureza, categoria, depto, "
                    "vencimento, coalesce(pagamento, "
                    "paga_em), t.valor FROM titulo t "
                    "LEFT JOIN cobranca c ON c.empresa_id "
                    "= t.empresa_id AND c.titulo_id = t.id"
                    " AND c.status = 'paga' WHERE "
                    "(%(cc)s::text IS NULL OR "
                    "depto = %(cc)s) AND "
                    "(%(cat)s::text IS NULL OR "
                    "categoria = %(cat)s)",
                    {"cc": cc, "cat": cat})
        tits = cur.fetchall()
        cur.execute("SELECT erp_ultima_sync()")
        sync = cur.fetchone()[0]
    ctx, d = filtrado(nome, cats, tits, ccs, cc, cat)
    ctx["at"] = sync.timestamp() if sync else 0
    return ctx, d


def busca(email):
    """(id, empresa_id, hash, totp) ou None."""
    with psycopg.connect("dbname=portal") as c:
        return c.execute("SELECT * FROM login_busca(%s)",
                         (email,)).fetchone()


def registra(eid, usuario, ip, acao, detalhe=""):
    """Log de auditoria: acessos e exportacoes."""
    with psycopg.connect("dbname=portal") as c:
        cur = c.cursor()
        abre(cur, eid)
        cur.execute("INSERT INTO auditoria (empresa_id, "
                    "usuario, ip, acao, detalhe) VALUES "
                    "(%s, %s, %s, %s, %s)",
                    (eid, usuario[:200], ip, acao, detalhe))


def acessos(eid, n=40):
    """Ultimos eventos desta empresa (o banco filtra)."""
    with psycopg.connect("dbname=portal") as c:
        cur = c.cursor()
        abre(cur, eid)
        cur.execute("SELECT quando, usuario, ip, acao, "
                    "detalhe FROM auditoria ORDER BY id "
                    "DESC LIMIT %s", (n,))
        return cur.fetchall()
