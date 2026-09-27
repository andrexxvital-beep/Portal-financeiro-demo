"""Etapa E1: painel por empresa, filtros e comparacao."""
import html
import math
import os
import time
from extras import brl, cfg, ler
from dono import analise
from urllib.parse import urlencode
from datetime import date, timedelta

A = "<"  # tags montadas assim p/ colar no chat
RESUMO = "resumo.json"
# Nome no topo do painel (vem do cadastro na etapa 4)
EMPRESA = "Loja Modelo Ltda"
# Escolha e ordem dos cartoes (personalize por cliente):
# saldo, resultado, margem, caixa, inadimplencia
DESTAQUES = ["saldo", "resultado", "margem", "caixa"]
# Grupos da DRE: categoria -> grupo (1x por cliente).
# Categoria fora daqui vira "Nao classificada" + aviso.
GRUPOS = {"Vendas Pix": "Receita",
          "Vendas cartao": "Receita",
          "Vendas boleto": "Receita",
          "Fornecedores": "Custos",
          "Aluguel": "Despesas administrativas",
          "Contas da loja": "Despesas administrativas",
          "Banco": "Despesas financeiras",
          "Mercado": "Retiradas", "Familia": "Retiradas",
          "Comida": "Retiradas", "Saude": "Retiradas"}
ORDEM = ["Receita", "Custos", "Despesas administrativas",
         "Despesas financeiras", "Retiradas"]
MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul",
         "ago", "set", "out", "nov", "dez"]
CLARO = ("--bg:#f3f4f6;--card:#fff;--bd:#e3e5e8;"
         "--tx:#1f2328;--tx2:#5f6570;--grid:#e6e8eb;"
         "--e1:#118DFF;--e2:#118DFF;--b1:#3346C9;"
         "--b2:#3346C9;--p1:#E66C37;--p2:#E66C37;"
         "--ok:#1a7f37;--ruim:#c62828;--okbg:#e6f4ea;"
         "--ruimbg:#fdecea;--hero:#eef4ff;--h1:#12239E;"
         "--h2:#12239E;--glow:transparent;"
         "--av:#a15c00;--avbg:#fff4e0")
# tema escuro (nome NEON mantido: login.py importa)
NEON = ("--bg:#16181d;--card:#22252b;--bd:#33363d;"
        "--tx:#f1f2f4;--tx2:#a9adb6;--grid:#33363d;"
        "--e1:#3597EC;--e2:#3597EC;--b1:#5B5BD0;"
        "--b2:#5B5BD0;--p1:#E66C37;--p2:#E66C37;"
        "--ok:#4cc38a;--ruim:#ff6b6b;--okbg:#1d3a2c;"
        "--ruimbg:#3d1f22;--hero:#1f2a3a;--h1:#3597EC;"
        "--h2:#3597EC;--glow:transparent;"
        "--av:#f0b44c;--avbg:#3a2f18")
CSS = (f"body{{{CLARO}}}@media(prefers-color-scheme:dark)"
       f"{{body{{{NEON}}}}}"
       "body{background:var(--bg);"
       "color:var(--tx)}"
       "*{box-sizing:border-box}"
       ".cd{background:var(--card);border:1px solid "
       "var(--bd);border-radius:14px;padding:12px;"
       "margin:10px 0;box-shadow:0 0 14px var(--glow)}"
       ".cd h3{margin:0 0 8px;font-size:1em}"
       ".sub{color:var(--tx2);font-size:.82em}"
       ".top{display:flex;justify-content:space-between;"
       "align-items:center;gap:8px;flex-wrap:wrap}"
       ".st,.tg{display:inline-block;border-radius:20px;"
       "padding:4px 12px;font-size:.82em}"
       ".tg{border:1px solid var(--bd);cursor:pointer;"
       "color:var(--tx2)}.hero{background:var(--hero)}"
       ".big{font-size:2.2em;font-weight:800;margin:2px 0;"
       "background:linear-gradient(90deg,var(--h1),"
       "var(--h2));-webkit-background-clip:text;"
       "background-clip:text;color:transparent}"
       ".hr{display:flex;gap:12px;align-items:center}"
       ".hr svg{width:96px;flex:none}"
       ".kp{display:grid;grid-template-columns:1fr 1fr;"
       "gap:10px}.kp .cd{margin:0}.kp b{display:block;"
       "font-size:1.3em;margin:4px 0}.sp{float:right;"
       "width:54px!important}"
       ".pl{display:inline-block;border-radius:10px;"
       "padding:1px 8px;font-size:.76em;font-weight:600}"
       ".bom{background:var(--okbg);color:var(--ok)}"
       ".mau{background:var(--ruimbg);color:var(--ruim)}"
       ".neu{background:var(--grid);color:var(--tx2)}"
       ".leg{font-size:.8em;color:var(--tx2)}.leg i{"
       "display:inline-block;width:9px;height:9px;"
       "border-radius:50%;margin:0 4px 0 10px}"
       "svg{width:100%;height:auto;display:block}"
       "svg text{fill:var(--tx2);font-size:9px}"
       ".gr{stroke:var(--grid)}.gl{filter:drop-shadow(0 0 "
       "4px var(--glow))}.pct{font-size:20px!important;"
       "font-weight:800;fill:var(--tx)!important}"
       ".fim{fill:var(--tx)!important;font-weight:700;"
       "font-size:10px!important}")
CSS += (".tb{display:grid;font-size:.78em;margin-top:6px;"
        "border-top:1px solid var(--grid)}.tb span{padding:"
        "4px 2px;text-align:center;border-bottom:1px solid "
        "var(--grid);white-space:nowrap}.tb .r{text-align:"
        "left;color:var(--tx2)}.tb .ok{color:var(--ok);"
        "font-weight:700}"
        ".dd{display:grid;grid-template-columns:1fr 1fr;"
        "gap:10px}.dd .cd{margin:0;text-align:center}"
        ".cat{margin:8px 0;font-size:.9em}.cat .t{display:"
        "flex;justify-content:space-between}.cat .t span{"
        "color:var(--tx2)}.trk{height:8px;border-radius:4px;"
        "background:var(--grid);margin-top:4px}.trk div{"
        "height:8px;border-radius:4px;background:linear-"
        "gradient(90deg,var(--b1),var(--b2))}"
        ".dica{padding:8px 10px;background:var(--hero);"
        "border-radius:10px;font-size:.82em;color:var(--tx2);"
        "margin-top:10px;line-height:1.45}.dica b{"
        "color:var(--tx)}"
        "details{margin:0}summary{cursor:pointer;"
        "font-weight:700;font-size:1em;padding:0}"
        "summary .sub{font-weight:400;float:right}"
        "details[open] summary{margin-bottom:6px}"
        "table{width:100%;border-collapse:collapse;"
        "font-size:.78em}th,td{border:0;border-bottom:1px "
        "solid var(--grid);background:none;padding:5px 2px;"
        "text-align:left;color:var(--tx)}th{color:var(--tx2)"
        ";font-weight:500}.n{text-align:right;white-space:"
        "nowrap}td.ok{color:var(--ok);font-weight:700}"
        "a{color:var(--b2)}"
        ".av{background:var(--avbg);color:var(--av);"
        "border:1px solid var(--av);border-radius:14px;"
        "padding:10px 12px;margin:10px 0;font-size:.88em}"
        ".av ul{margin:6px 0 0;padding-left:18px;"
        "color:var(--tx)}.av li{margin:4px 0}"
        ".top h2{margin:0;font-size:1.4em}"
        "a.tg{text-decoration:none}"
        ".dg summary{display:flex;justify-content:"
        "space-between;padding:8px 0;margin:0;font-size:"
        ".9em;border-bottom:1px solid var(--grid)}"
        ".dg summary span:first-child::before{content:"
        "'\\25B8  ';color:var(--tx2)}"
        ".dg[open] summary span:first-child::before{"
        "content:'\\25BE  '}"
        ".dl{display:flex;justify-content:space-between;"
        "padding:4px 0 4px 20px;font-size:.82em;"
        "color:var(--tx2)}"
        ".dr{display:flex;justify-content:space-between;"
        "padding:8px 10px;margin:6px 0;border-radius:10px;"
        "background:var(--hero);font-weight:700;"
        "font-size:.9em}.dr.ok span+span{color:var(--ok)}"
        ".dr.ruim span+span{color:var(--ruim)}"
        ".ina{display:flex;align-items:center;gap:10px;"
        "margin:4px 0 8px}.ina b{font-size:1.5em}"
        ".bar{display:flex;gap:2px;height:10px;"
        "border-radius:5px;overflow:hidden;margin-top:4px;"
        "background:var(--grid)}"
        ".neg{color:var(--ruim)!important;"
        "font-weight:700}")


CENTROS = {"LOJA": "Loja física", "DELIVERY": "Delivery",
           "ADM": "Administrativo", "SOCIOS": "Sócios"}


CSS += (".fl{display:grid;grid-template-columns:1fr 1fr;"
        "gap:6px;margin:8px 0 2px}"
        ".fl select{padding:7px 6px;font-size:.82em;"
        "border-radius:8px;border:1px solid var(--bd);"
        "background:var(--card);color:var(--tx);"
        "min-width:0;width:100%}"
        ".fl select[name=p]{grid-column:1/-1;"
        "font-weight:700}"
        ".fl button{padding:7px 12px;font-size:.85em;"
        "font-weight:700;border:0;border-radius:8px;"
        "color:#fff;background:var(--h1);"
        "grid-column:1/-1}"
        ".fa{font-size:.8em;color:var(--av);margin:6px 0 0;"
        "background:var(--avbg);border-radius:8px;"
        "padding:5px 10px}.fa .lp{float:right;"
        "color:var(--av);font-weight:700}"
        ".tb .dv{display:block;font-style:normal;"
        "font-size:.85em;margin-top:1px}"
        ".tb .dv.up{color:var(--ok)}"
        ".tb .dv.dn{color:var(--ruim)}")


def sem_zero(lin):
    """Tira linhas de valores (Receitas, Pago...) que
    estao todas zeradas, como Retiradas no Delivery."""
    fica = ("Saldo", "=", "Resultado", "Margem")
    return [x for x in lin if x[0].startswith(fica)
            or any(v not in ("0", "&#8212;") and
                   not v.startswith(("0" + A, A + "b>0<"))
                   for v in x[1])]


def parcial(mes):
    """'26/09' se o mes 'MM/AAAA' ainda nao fechou."""
    hoje = cfg("hoje", None) or date.today()
    fim = (hoje + timedelta(days=1)).month != hoje.month
    if mes == hoje.strftime("%m/%Y") and not fim:
        return hoje.strftime("%d/%m")
    return ""


def volta(m, k):
    """Mes 'MM/AAAA' k meses para tras."""
    i = int(m[3:]) * 12 + int(m[:2]) - 1 - k
    return f"{i % 12 + 1:02d}/{i // 12}"


def tipo(p):
    p = p or ""
    if p in ("12m", "tudo"):
        return p
    if len(p) == 4 and p.isdigit():
        return "ano"
    if len(p) == 7 and p[0] == "T" and p[1] in "1234" \
            and p[2] == "/" and p[3:].isdigit():
        return "tri"
    if len(p) == 7 and p[2] == "/" and p[:2].isdigit() \
            and p[3:].isdigit() and 1 <= int(p[:2]) <= 12:
        return "mes"
    return ""


def tri_de(m):
    return f"T{(int(m[:2]) - 1) // 3 + 1}/{m[3:]}"


def meses_de(p, ms):
    """Meses (com dados) que o periodo p cobre."""
    t = tipo(p)
    if t == "tudo":
        return list(ms)
    if t == "12m":
        jan = {volta(ms[-1], k) for k in range(12)}
        return [m for m in ms if m in jan]
    if t == "ano":
        return [m for m in ms if m[3:] == p]
    if t == "tri":
        return [m for m in ms if tri_de(m) == p]
    return [p] if p in ms else []


def rotulo(p, curto=False):
    t = tipo(p)
    if t == "tudo":
        return "tudo" if curto else "Todo o período"
    if t == "12m":
        return "12 meses" if curto else "Últimos 12 meses"
    if t == "tri":
        return (nome_mes(p) if curto else
                f"{p[1]}º trimestre {p[3:]}")
    if t == "mes":
        return f"{nome_mes(p)}/{p[-2 if curto else -4:]}"
    return p


def opcoes(ms):
    """Periodos do filtro: [(grupo, [(p, rotulo)])]."""
    tris, anos = [], []
    for m in reversed(ms):
        if tri_de(m) not in tris:
            tris.append(tri_de(m))
        if m[3:] not in anos:
            anos.append(m[3:])
    return [("Trimestre", [(t, rotulo(t)) for t in tris]),
            ("Mês", [(m, rotulo(m)) for m in ms[::-1]]),
            ("Ano", [(a, a) for a in anos]),
            ("Mais", [("12m", rotulo("12m")),
                      ("tudo", rotulo("tudo"))])]


def link(p, arq="/"):
    """URL com o periodo e os filtros da vez."""
    f = cfg("filtro", None) or {}
    q = {"p": p, "cc": f.get("cc"), "cat": f.get("cat")}
    q = urlencode({k: v for k, v in q.items() if v})
    return html.escape(arq + ("?" + q if q else ""))


def margem(luc, ent):
    """% do que entrou que sobrou (sem receita: -)."""
    return f"{100 * luc / ent:.0f}%" if ent > 1 else "&#8212;"


def juntar(meses):
    """Mais de 6 meses: soma por trimestre (ou por ano),
    para caber na tela do celular."""
    if len(meses) <= 6:
        return meses
    tri = len({tri_de(m["mes"]) for m in meses}) <= 6
    out = {}
    for m in meses:
        k = tri_de(m["mes"]) if tri else m["mes"][3:]
        b = out.setdefault(k, {"mes": k, "ks": [],
                               "entra": 0, "sai_empresa": 0,
                               "sai_pessoal": 0, "saldo": 0})
        b["ks"].append(m["mes"])
        for c in ("entra", "sai_empresa", "sai_pessoal",
                  "saldo"):
            b[c] += m[c]
    return list(out.values())


def soma(por, ks):
    """Totais dos meses ks (None se falta algum)."""
    if not ks or any(k not in por for k in ks):
        return None
    t = {c: sum(por[k][c] for k in ks) for c in
         ("entra", "sai_empresa", "sai_pessoal")}
    t["res"] = t["entra"] + t["sai_empresa"]
    return t


def compara(todos, meses, p):
    """Periodo atual x anterior x mesmo periodo do ano
    passado (receitas, despesas, resultado, margem)."""
    t = tipo(p)
    ks = [m["mes"] for m in meses]
    if t == "tudo" or not ks:
        return ""
    por = {m["mes"]: m for m in todos}
    passos = {"mes": [1, 12], "tri": [3, 12]}.get(t, [12])
    cols = [rotulo(p, True)]
    tots = [soma(por, ks)]
    for k in passos:
        vk = [volta(m, k) for m in ks]
        if t == "12m":
            cols.append("12m ant.")
        elif t == "ano":
            cols.append(str(int(p) - 1))
        else:
            cols.append(rotulo(volta(ks[-1], k) if t == "mes"
                               else tri_de(vk[-1]), True))
        tots.append(soma(por, vk))
    a = tots[0]
    corte = parcial(ks[-1])
    if corte:
        cols[0] += "*"

    def cel(chave, sinal, i):
        x = tots[i]
        if x is None:
            return "&#8212;"
        v = sinal * x[chave]
        txt = sn(v)
        if i == 0:
            return f"{A}b>{txt}</b>"
        b0 = sinal * a[chave]
        if not v:
            return txt
        pc = 100 * (b0 - v) / abs(v)
        if round(pc) == 0:
            return f"{txt}{A}i class=dv>= 0%</i>"
        bom = (pc >= 0) == (chave in ("entra", "res"))
        s = "&#9650;" if pc >= 0 else "&#9660;"
        cl = "up" if bom else "dn"
        return (f"{txt}{A}i class='dv {cl}'>{s}"
                f"{abs(pc):.0f}%</i>")

    def mg(i):
        x = tots[i]
        if x is None or not x["entra"]:
            return "&#8212;"
        v = 100 * x["res"] / x["entra"]
        if i == 0:
            return f"{A}b>{v:.0f}%</b>"
        if not a["entra"]:
            return f"{v:.0f}%"
        dif = 100 * a["res"] / a["entra"] - v
        if round(dif) == 0:
            return f"{v:.0f}%{A}i class=dv>= 0 p.p.</i>"
        s = "&#9650;" if dif >= 0 else "&#9660;"
        return (f"{v:.0f}%{A}i class='dv "
                f"{'up' if dif >= 0 else 'dn'}'>{s}"
                f"{abs(dif):.0f} p.p.</i>")
    rg = range(len(tots))
    lin = sem_zero([
        ("Receitas", [cel("entra", 1, i) for i in rg], ""),
        ("Despesas", [cel("sai_empresa", -1, i)
                      for i in rg], ""),
        ("Retiradas", [cel("sai_pessoal", -1, i)
                       for i in rg], ""),
        ("Resultado operac.", [cel("res", 1, i)
                               for i in rg], "rs sep"),
        ("Margem", [mg(i) for i in rg], "")])
    falta = ""
    if None in tots:
        falta = " &#8212; = sem dados no ERP."
    if corte:
        falta += (f" * até {corte}: o mês ainda não "
                  "fechou, o total ainda vai mudar.")
    return (f"{A}div class=cd>{A}div class=top>{A}h3>"
            "Comparação de períodos</h3>"
            f"{A}span class=sub>R$</span></div>"
            + grade(cols, lin, "30%")
            + f"{A}div class=sub style='margin-top:6px'>"
            "A seta mostra quanto o período atual subiu ou "
            f"caiu em relação a cada coluna.{falta}</div>"
            "</div>")


def sufixo(p):
    """Parte do nome do arquivo: 2026-09, 2026-T3..."""
    t = tipo(p)
    s = {"mes": p[3:] + "-" + p[:2],
         "tri": p[3:] + "-" + p[:2]}.get(t, p)
    f = cfg("filtro", None) or {}
    for k in ("cc", "cat"):
        if f.get(k):
            s += "_" + f[k]
    return "".join(c for c in s if c.isalnum() or c in "-_.")


def de_ate(m0, m1):
    """'jul a set/2026' ou 'dez/2025 a set/2026'."""
    fim = f"{nome_mes(m1)}/{m1[-4:]}"
    if m0 == m1:
        return fim
    ini = nome_mes(m0)
    if m0[-4:] != m1[-4:]:
        ini += "/" + m0[-4:]
    return f"{ini} a {fim}"


def grad(id_, c1, c2, vert=True):
    x2, y2 = (0, 1) if vert else (1, 0)
    return (f"{A}linearGradient id={id_} x1=0 y1=0 "
            f"x2={x2} y2={y2}>{A}stop offset=0 style="
            f"'stop-color:var({c1})' />{A}stop offset=1 "
            f"style='stop-color:var({c2})' />"
            "</linearGradient>")


DEFS = (f"{A}svg width=0 height=0 style='position:absolute'>"
        f"{A}defs>" + grad("gE", "--e2", "--e1")
        + grad("gB", "--b2", "--b1")
        + grad("gP", "--p2", "--p1")
        + grad("gL", "--b1", "--b2", False)
        + grad("gH", "--h1", "--h2", False)
        + f"{A}linearGradient id=gA x1=0 y1=0 x2=0 y2=1>"
        f"{A}stop offset=0 style='stop-color:var(--b2);"
        f"stop-opacity:.35' />{A}stop offset=1 style='stop-"
        "color:var(--b2);stop-opacity:0' />"
        "</linearGradient></defs></svg>")


def curto(c):
    """R$ sem centavos: menos numeros na tela."""
    return brl(round(c / 100) * 100)[:-3]


def mil(c):
    if not round(c):
        return "0"
    v = abs(c) / 100000
    t = f"{v:.1f}".rstrip("0").rstrip(".").replace(".", ",")
    return ("-" if c < 0 else "") + t + " mil"


def eixo(lo, hi):
    """Arredonda o eixo para 0, 5 mil, 10 mil..."""
    x = (hi - lo) / 3 or 1
    p = 10 ** math.floor(math.log10(x))
    passo = next(m * p for m in (1, 2, 5, 10) if m * p >= x)
    lo = passo * math.floor(lo / passo)
    hi = passo * math.ceil(hi / passo)
    return lo, hi, passo


def nu(c):
    """Valor curto sem o R$ (para tabelas)."""
    return curto(c).replace("R$ ", "")


def pill(txt, tipo):
    return f"{A}span class='pl {tipo}'>{txt}</span>"


def nome_mes(m, soma=0):
    if m[0] == "T":
        return m[:3] + m[-2:]  # trimestre: T3/26
    if "/" not in m:
        return m  # ano: 2026
    return MESES[(int(m.split("/")[0]) - 1 + soma) % 12]


def prever(vals):
    """Reta simples pelos meses: estimativa do proximo."""
    n = len(vals)
    if n < 2:
        return vals[-1]
    mx, my = (n - 1) / 2, sum(vals) / n
    b = sum((i - mx) * (v - my) for i, v in enumerate(vals))
    b /= sum((i - mx) ** 2 for i in range(n))
    return my + b * (n - mx)


def spark(vals, g):
    mx = max(abs(v) for v in vals) or 1
    w = 54 / len(vals)
    s = [f"{A}svg class=sp viewBox='0 0 54 26'>"]
    for i, v in enumerate(vals):
        h = 24 * abs(v) / mx
        s.append(f"{A}rect x={i * w + 1:.1f} y={26 - h:.1f} "
                 f"width={w - 3:.1f} height={h:.1f} rx=2 "
                 f"fill='url(#{g})' />")
    return "".join(s) + "</svg>"


def varia(a, b):
    """Pill com a variacao de b para a (em %)."""
    p = 100 * (a - b) / (abs(b) or 1)
    s = "&#9650; " if p >= 0 else "&#9660; "
    return pill(f"{s}{abs(p):.0f}% vs mês ant.",
                "bom" if p >= 0 else "mau")


def grupos(cats):
    g = {k: [] for k in ORDEM}
    nc, gr = [], cfg("grupos", GRUPOS)
    for c, v in sorted(cats.items(),
                       key=lambda cv: -abs(cv[1])):
        (g[gr[c]] if gr.get(c) in g else nc).append(
            (c, v))
    return g, nc


def col(x, y, w, base, g, dica):
    r = min(4, w / 2, max(base - y, 0))
    return (f"{A}path fill='url(#{g})' class=gl "
            f"d='M{x:.1f},{base:.1f}V{y + r:.1f}Q{x:.1f},"
            f"{y:.1f} {x + r:.1f},{y:.1f}H{x + w - r:.1f}"
            f"Q{x + w:.1f},{y:.1f} {x + w:.1f},{y + r:.1f}"
            f"V{base:.1f}Z'>{A}title>{html.escape(dica)}"
            "</title></path>")


def neg(v, cl):
    return cl if v >= 0 else "neg"


def curva(lin, ini=0):
    por = {}
    for d, _, v in lin:
        por[d] = por.get(d, 0) + v
    dia, fim = min(por), max(por)
    pts, acc = [], ini
    while dia <= fim:
        acc += por.get(dia, 0)
        pts.append((dia, acc))
        dia = dia.fromordinal(dia.toordinal() + 1)
    # periodo longo: 1 ponto por semana (tela leve)
    pulo = max(1, len(pts) // 120)
    pts = pts[::-1][::pulo][::-1]
    if len(pts) == 1:
        pts = pts * 2  # 1 dia so: linha reta
    longo = (pts[-1][0] - pts[0][0]).days > 190
    W, H, L, T, B = 340, 160, 52, 16, 18
    lo = min(0, min(v for _, v in pts))
    hi = max(0, max(v for _, v in pts)) or 1
    lo, hi, passo = eixo(lo, hi)
    n = len(pts) - 1 or 1
    X = [L + (W - L - 8) * i / n for i in range(n + 1)]
    Y = [T + (H - T - B) * (hi - v) / (hi - lo)
         for _, v in pts]
    d = f"M{X[0]:.1f},{Y[0]:.1f}"
    for i in range(1, n + 1):
        a, b = max(i - 2, 0), min(i + 1, n)
        c1x = X[i - 1] + (X[i] - X[a]) / 6
        c1y = Y[i - 1] + (Y[i] - Y[a]) / 6
        c2x = X[i] - (X[b] - X[i - 1]) / 6
        c2y = Y[i] - (Y[b] - Y[i - 1]) / 6
        d += (f"C{c1x:.1f},{c1y:.1f} {c2x:.1f},{c2y:.1f} "
              f"{X[i]:.1f},{Y[i]:.1f}")
    y0 = T + (H - T - B) * hi / (hi - lo)
    s = [f"{A}svg viewBox='0 0 {W} {H}'>"]
    for k in range(round((hi - lo) / passo) + 1):
        v = lo + passo * k
        yy = T + (H - T - B) * (hi - v) / (hi - lo)
        s.append(f"{A}line class=gr x1={L} x2={W - 8} "
                 f"y1={yy:.1f} y2={yy:.1f} />{A}text "
                 f"x={L - 4} y={yy + 3:.1f} "
                 f"text-anchor=end>{mil(v)}</text>")
    ult = None
    for i, (dd, _) in enumerate(pts):
        if dd.month == ult:
            continue
        ult = dd.month
        if longo and dd.month % 3 != 1:
            continue
        rot = MESES[dd.month - 1]
        if longo:
            rot += f"/{dd.year % 100}"
        s.append(f"{A}text x={X[i]:.1f} y={H - 4}>"
                 f"{rot}</text>")
    s.append(f"{A}path d='{d}L{X[-1]:.1f},{y0:.1f}"
             f"L{X[0]:.1f},{y0:.1f}Z' fill='url(#gA)' />"
             f"{A}path d='{d}' fill=none stroke='url(#gL)' "
             "class=gl stroke-width=2.5 "
             "stroke-linecap=round />")
    for i, (dd, v) in enumerate(pts):
        s.append(f"{A}rect x={X[i] - 2:.1f} y={T} width=4 "
                 f"height={H - T - B} fill=transparent>"
                 f"{A}title>{dd.strftime('%d/%m/%y')}: "
                 f"{brl(v)}</title></rect>")
    s.append(f"{A}circle cx={X[-1]:.1f} cy={Y[-1]:.1f} r=4 "
             "fill='var(--b2)' class=gl />"
             f"{A}text x={X[-1]:.1f} y={Y[-1] - 8:.1f} "
             f"class=fim text-anchor=end>{mil(pts[-1][1])}"
             "</text></svg>")
    return "".join(s)


def categorias(cats):
    sai = sorted(((c, -v) for c, v in cats.items() if v < 0),
                 key=lambda cv: -cv[1])
    tot = sum(v for _, v in sai) or 1
    top = sai[:5]
    resto = sum(v for _, v in sai[5:])
    if resto:
        top.append(("Outros", resto))
    if not top:
        return ""
    mx = max(v for _, v in top)
    return "".join(
        f"{A}div class=cat>{A}div class=t>{html.escape(c)}"
        f"{A}span>{curto(v)} &#183; {100 * v / tot:.0f}%"
        f"</span></div>{A}div class=trk>{A}div style='width:"
        f"{100 * v / mx:.1f}%'></div></div></div>"
        for c, v in top)


def caixa(titulo, nota, corpo):
    return (f"{A}div class=cd>{A}details>{A}summary>"
            f"{titulo} {A}span class=sub>{nota}</span>"
            f"</summary>{corpo}</details></div>")


CSS += (".emp{font-size:1.25em;font-weight:800;"
        "color:var(--h1);margin:4px 0 2px;"
        "letter-spacing:.2px}"
        ".cd h3{font-size:.95em}"
        ".kp b{font-size:1.15em!important}"
        ".kp .cd{min-height:94px}"
        ".cha{display:block;margin:8px 0;padding:6px 10px;"
        "border-radius:8px;border-left:3px solid var(--av);"
        "background:var(--avbg);color:var(--av);"
        "font-size:.8em;text-decoration:none}"
        ".mini{display:grid;grid-template-columns:"
        "repeat(3,1fr);gap:8px;margin:4px 0 10px}"
        ".mini div{background:var(--bg);border:1px solid "
        "var(--bd);border-radius:10px;padding:8px 4px;"
        "text-align:center}.mini span{display:block;"
        "font-size:.72em;color:var(--tx2)}"
        ".mini b{font-size:.95em}.mini .ok{color:var(--ok)}"
        ".tb .rs{font-weight:700}"
        ".av h3{color:var(--av);margin:0}"
        ".av{border-left-width:5px}"
        ".rod{display:flex;justify-content:space-between;"
        "align-items:center;font-size:.78em;"
        "color:var(--tx2);margin:14px 0 4px}")


def sn(v):
    """Valor curto com sinal, sem R$."""
    return ("-" if v < 0 else "") + nu(abs(v))


def colunas(meses):
    W, H, L, T, B = 340, 170, 52, 16, 18
    mx = max(max(m["entra"], -m["sai_empresa"]
                 - m["sai_pessoal"]) for m in meses) or 1
    _, mx, passo = eixo(0, mx)
    base = H - B
    y = lambda v: base - (base - T) * v / mx  # noqa: E731
    s = [f"{A}svg viewBox='0 0 {W} {H}'>"]
    for k in range(round(mx / passo) + 1):
        v = passo * k
        s.append(f"{A}line class=gr x1={L} x2={W} "
                 f"y1={y(v):.1f} y2={y(v):.1f} />{A}text "
                 f"x={L - 6} y={y(v) + 3:.1f} "
                 f"text-anchor=end>{mil(v)}</text>")
    gw = (W - L) / len(meses)
    bw = min(30, gw * 0.3)
    for i, m in enumerate(meses):
        cx = L + gw * (i + 0.5)
        e, p = -m["sai_empresa"], -m["sai_pessoal"]
        x1, x2 = cx - bw - 2, cx + 2
        s.append(col(x1, y(m["entra"]), bw, base, "gE",
                     "Receitas " + curto(m["entra"])))
        if e > 0:
            s.append(col(x2, y(e), bw, base, "gB",
                         "Despesas " + curto(e)))
        if p > 0:  # sem retirada: sem risquinho laranja
            s.append(col(x2, y(e + p), bw, y(e) - 2, "gP",
                         "Retiradas " + curto(p)))
        s.append(f"{A}text x={cx:.1f} y={H - 4} "
                 f"text-anchor=middle>{nome_mes(m['mes'])}"
                 "</text>")
    s.append("</svg>")
    # tabela alinhada: 1a coluna = largura do eixo
    cols = f"{100 * L / W:.1f}% repeat({len(meses)},1fr)"
    lin = [("Receitas", [m["entra"] for m in meses]),
           ("Despesas", [-m["sai_empresa"] for m in meses]),
           ("Retiradas", [-m["sai_pessoal"] for m in meses])]
    lin = [x for x in lin if any(x[1])]
    lin.append(("Resultado", [m["saldo"] for m in meses]))
    s.append(f"{A}div class=tb style='grid-template-columns:"
             f"{cols}'>")
    for rot, vals in lin:
        rs = "rs" if rot == "Resultado" else ""
        s.append(f"{A}span class='r {rs}'>{rot}</span>"
                 + "".join(f"{A}span class='{neg(v, rs)}'>"
                           f"{sn(v)}</span>" for v in vals))
    return "".join(s) + "</div>"


def dica(cats, lin):
    vendas = [(d, v) for d, _, v in lin if v > 0]
    if not vendas:
        return ""
    sem = [0] * 7
    for d, v in vendas:
        sem[d.weekday()] += v
    dias = ["segundas", "terças", "quartas", "quintas",
            "sextas", "sábados", "domingos"]
    b = max(range(7), key=lambda i: sem[i])
    tv = sum(sem) or 1
    sai = sorted(((c, -v) for c, v in cats.items() if v < 0),
                 key=lambda cv: -cv[1])
    tot = sum(v for _, v in sai) or 1
    if not sai:
        return ""
    c, v = sai[0]
    return (f"{A}div class=dica>{A}b>Maior receita:</b> "
            f"{dias[b]} ({100 * sem[b] / tv:.0f}% das "
            f"receitas).{A}br>{A}b>Maior despesa:</b> "
            f"{html.escape(c)} ({100 * v / tot:.0f}% das "
            "saídas). Renegociar prazos aqui tem o maior "
            "impacto.</div>")


def tabelas(meses, lin):
    e = html.escape
    t1 = "".join(
        f"{A}tr>{A}td>{nome_mes(m['mes'])}</td>"
        f"{A}td class=n>{nu(m['entra'])}</td>"
        f"{A}td class=n>{nu(abs(m['sai_empresa']))}</td>"
        f"{A}td class=n>{nu(abs(m['sai_pessoal']))}</td>"
        f"{A}td class='n {neg(m['saldo'], '')}'>"
        f"{A}b>{sn(m['saldo'])}</b></td></tr>"
        for m in meses)
    top = sorted((x for x in lin if x[2] < 0),
                 key=lambda x: x[2])[:5]
    t2 = "".join(
        f"{A}tr>{A}td>{d.strftime('%d/%m')}</td>{A}td>"
        f"{e(n.capitalize())}</td>{A}td class=n>{nu(-v)}</td>"
        "</tr>" for d, n, v in top)
    c1 = (f"{A}table>{A}tr>{A}th>Mês</th>{A}th class=n>"
          f"Receitas</th>{A}th class=n>Despesas</th>{A}th "
          f"class=n>Retiradas</th>{A}th class=n>Resultado"
          f"</th></tr>{t1}</table>")
    c2 = (f"{A}table>{A}tr>{A}th>Data</th>{A}th>Pagamento"
          f"</th>{A}th class=n>R$</th></tr>{t2}</table>")
    out = ""  # 4g: repetia o gráfico e a DFC
    if t2:
        out += caixa("5 maiores pagamentos", "no período",
                     c2)
    return out


def aging(d):
    """Contas em aberto por faixa de atraso (aging)."""
    ab = d["abertos"]
    fx = [("a_vencer", "a vencer", "var(--b2)"),
          ("1-30", "1 a 30 dias", "var(--av)"),
          ("31-60", "31 a 60", "var(--p1)"),
          ("60+", "60+", "var(--ruim)")]
    rc = ab["receber"]
    ven = sum(rc[k] for k, _, _ in fx[1:])
    ina = f"{d.get('inadimplencia_pct', 0):.1f}%"
    cl = " class=neg" if ven else ""
    out = [f"{A}div class=cd>{A}div class=top>{A}h3>"
           f"Contas a receber e a pagar</h3>{A}span "
           f"class=sub>em aberto · R$</span></div>"
           f"{A}div class=mini>{A}div>{A}span>"
           f"Inadimplência</span>{A}b{cl}>"
           f"{ina.replace('.', ',')}</b></div>{A}div>"
           f"{A}span>Vencido</span>{A}b{cl}>{nu(ven)}</b>"
           f"</div>{A}div>{A}span>A vencer</span>{A}b>"
           f"{nu(rc['a_vencer'])}</b></div></div>"]
    for rot, k in (("A receber", "receber"),
                   ("A pagar", "pagar")):
        v = ab[k]
        tot = sum(v.values()) or 1
        seg = "".join(
            f"{A}div style='width:{100 * v[c] / tot:.1f}%;"
            f"background:{cor}'>{A}title>{nm}: "
            f"{nu(v[c])}</title></div>"
            for c, nm, cor in fx if v[c])
        out.append(f"{A}div class=cat>{A}div class=t>{rot}"
                   f"{A}span>{nu(sum(v.values()))}</span>"
                   f"</div>{A}div class=bar>{seg}"
                   "</div></div>")
    out.append(f"{A}div class=leg>" + "".join(
        f"{A}i style='background:{cor}'></i>{nm}"
        for _, nm, cor in fx) + "</div></div>")
    return "".join(out)


def atencao(r):
    av = [x for c, x in r["alertas"] if c == "av"]
    if not av:
        return (f"{A}div class=cd id=atencao>{A}span "
                "class=sub>Nenhum ponto de atenção no "
                "período.</span></div>")
    li = "".join(f"{A}li>{html.escape(x)}</li>" for x in av)
    return (f"{A}div class=av id=atencao>{A}h3>&#9888; "
            f"Pontos de atenção</h3>{A}ul>{li}</ul></div>")


CSS += (".fil{display:flex;gap:6px;overflow-x:auto;"
        "margin:8px 0 2px;padding-bottom:2px}"
        ".fil a{flex:none;border:1px solid var(--bd);"
        "border-radius:16px;padding:4px 12px;"
        "font-size:.8em;color:var(--tx2);"
        "text-decoration:none;background:var(--card)}"
        ".fil a.on{background:var(--h1);color:#fff;"
        "border-color:var(--h1);font-weight:700}"
        ".dg .dc summary{padding:4px 0 4px 20px;"
        "font-size:.82em;border:0;font-weight:400;"
        "color:var(--tx2)}"
        ".dg .dc summary span:first-child::before{"
        "content:'\\25B8  '}"
        ".dg .dc[open] summary span:first-child::before{"
        "content:'\\25BE  '}"
        ".lc{display:flex;justify-content:space-between;"
        "padding:2px 0 2px 38px;font-size:.76em;"
        "color:var(--tx2)}"
        ".rod a{margin-left:6px}")


def periodo(d, lin, p):
    """Recorta o periodo p (mes, trimestre, ano, 12m ou
    tudo). Padrao: o trimestre do ultimo mes."""
    todos = d["meses"]
    ms = [m["mes"] for m in todos]
    ks = meses_de(p, ms)
    if not ks:
        p = tri_de(ms[-1])
        ks = meses_de(p, ms)
    i = ms.index(ks[-1])
    lin = [x for x in lin if x[0].strftime("%m/%Y") in ks]
    cats = {}
    for _, c, v in lin:
        cats[c] = cats.get(c, 0) + v
    f = dict(d, meses=[m for m in todos if m["mes"] in ks],
             categorias=cats)
    return f, lin, todos[:i + 1], p


def filtro(todos, p):
    e = html.escape
    f = cfg("filtro", None) or {}

    def op(v, rot, at):
        s = " selected" if v == at else ""
        return (f"{A}option value='{e(v)}'{s}>{e(rot)}"
                "</option>")
    per = "".join(
        f"{A}optgroup label='{g}'>"
        + "".join(op(k, r, p) for k, r in itens)
        + "</optgroup>"
        for g, itens in opcoes([m["mes"] for m in todos]))
    cc = op("", "Todos os centros", f.get("cc") or "")
    ordem = list(CENTROS)
    ccs = sorted(f.get("ccs", []), key=lambda k: (
        ordem.index(k) if k in ordem else 99, k))
    cc += "".join(op(k, CENTROS.get(k, k), f.get("cc"))
                  for k in ccs)
    ct = op("", "Todas as categorias", f.get("cat") or "")
    ct += "".join(op(k, n, f.get("cat"))
                  for k, n in f.get("cats", []))
    limpa = ""
    if f.get("cc") or f.get("cat"):
        q = urlencode({"p": p})
        limpa = f"{A}a class=lp href='/?{e(q)}'>Limpar</a>"
    ativo = [CENTROS.get(f["cc"], f["cc"])] if f.get("cc") \
        else []
    ativo += [n for k, n in f.get("cats", [])
              if k == f.get("cat")]
    nota = ""
    if ativo:
        nota = (f"{A}div class=fa>Filtro: "
                + " · ".join(e(x) for x in ativo)
                + f" {limpa}</div>")
    return (f"{A}form class=fl method=get action=/>"
            f"{A}select name=p aria-label=Período>{per}"
            f"</select>{A}select name=cc aria-label="
            f"'Centro de custo'>{cc}</select>{A}select "
            f"name=cat aria-label=Categoria>{ct}</select>"
            f"{A}button>Filtrar</button></form>{nota}")


def status(r):
    s, m = r["sal_ult"], r["m1"]
    m1 = f"{nome_mes(m)}/{m[-4:]}"
    per = de_ate(r["m0"], m)
    tp, txt = ("mau", "negativo") if s < 0 else (
        "bom", "positivo")
    av = [x for c, x in r["alertas"] if c == "av"]
    ch = ""
    if av:
        q = len(av)
        s_ = "s" if q > 1 else ""
        ch = (f"{A}a class=cha href=#atencao>&#9888; {q} "
              f"ponto{s_} de atenção &#183; ver no fim</a>")
    return (f"{A}div class=emp>{html.escape(empresa_nome())}"
            f"</div>{A}div class=top>{A}span class=sub>"
            f"Resumo financeiro &#183; {per}</span>"
            + pill(f"{m1} fechou {txt}", tp)
            + f"</div>{ch}")


def rodape(p):
    at = cfg("at", 0)
    at = ("atualizado " + time.strftime(
        "%d/%m %H:%M", time.localtime(at)) if at
        else "carga manual")
    return (f"{A}div class=rod>{A}span>Dados do ERP "
            f"&#183; {at}</span>{A}span>"
            f"Exportar {A}a class=tg "
            f"href='{link(p, '/exportar.csv')}'>CSV</a>"
            f"{A}a class=tg "
            f"href='{link(p, '/relatorio.pdf')}'>PDF</a>"
            f"{A}a class=tg href=/logout>Sair</a>"
            "</span></div>")


def kpis(r, meses):
    """meses = historico ate o mes escolhido."""
    n, ent = r["n"], r["ent"]
    sald = [m["saldo"] for m in meses]
    res = [m["entra"] + m["sai_empresa"] for m in meses]
    acum, x = [], 0
    for v in sald:
        x += v
        acum.append(x)
    luc = ent - r["emp"]
    m1 = nome_mes(r["m1"])
    ant = res[-2] if len(res) > 1 else res[-1]
    p = 100 * (res[-1] - ant) / (abs(ant) or 1)
    se = "&#9650;" if p >= 0 else "&#9660;"
    seg = r.get("seg")
    if seg is not None:
        cx = ("Caixa em " + nome_mes(r["m1"], 1),
              curto(acum[-1] + seg), pill("realizado", "neu"),
              spark(acum[-12:] + [acum[-1] + seg], "gB"))
    else:
        prox = prever(sald[-12:])
        pj = r.get("proj")
        if pj:
            prox = pj["entra"] - pj["sai"]
        cx = (f"Caixa projetado {nome_mes(r['m1'], 1)}",
              "~" + curto(acum[-1] + prox),
              pill("títulos lançados" if pj
                   else "estimativa", "neu"),
              spark(acum[-12:] + [acum[-1] + prox], "gB"))
    op = {
        "saldo": ("Saldo em caixa", curto(acum[-1]),
                  pill(f"{sn(sald[-1])} em {m1}", "neu"),
                  spark(acum[-12:], "gB")),
        "resultado": ("Resultado operacional", curto(res[-1]),
                      pill(f"{m1} {se} {abs(p):.0f}% vs mês "
                           "ant.", "neu"),
                      spark(res[-12:], "gE")),
        "margem": ("Margem operacional", margem(luc, ent),
                   pill("no mês" if n == 1
                        else f"em {n} meses", "neu"), ""),
        "caixa": cx}
    if r.get("ina") is not None:
        op["inadimplencia"] = (
            "Inadimplência",
            f"{r['ina']:.1f}%".replace(".", ","),
            pill(f"{curto(r['ven'])} vencido", "neu"), "")
    cards = [op[k] for k in DESTAQUES if k in op]
    return (f"{A}div class=kp>" + "".join(
        f"{A}div class=cd>{sp}{A}span class=sub>{a}</span>"
        f"{A}b>{b}</b>{c}</div>" for a, b, c, sp in cards)
        + "</div>")


def dre(cats, lin):
    g, nc = grupos(cats)
    rec0 = sum(v for _, v in g["Receita"])
    rec = rec0 or 1
    e = html.escape

    def lanc(c):
        return "".join(
            f"{A}div class=lc>{A}span>{d.strftime('%d/%m')}"
            f"</span>{A}span>{nu(abs(v))}</span></div>"
            for d, n, v in lin if n == c)

    def linha(nome, itens):
        tot = sum(v for _, v in itens)
        sub = "".join(
            f"{A}details class=dc>{A}summary>{A}span>{e(c)}"
            f"</span>{A}span>{nu(abs(v))}</span></summary>"
            f"{lanc(c)}</details>" for c, v in itens)
        return (f"{A}details class=dg>{A}summary>{A}span>"
                f"{nome}</span>{A}span>{nu(abs(tot))}"
                + (f" · {100 * abs(tot) / rec:.0f}%"
                   if rec0 else "") + "</span>"
                f"</summary>{sub}</details>")

    def res(nome, v):
        return (f"{A}div class=dr>{A}span>= {nome}</span>"
                f"{A}span class='{neg(v, '')}'>{sn(v)}"
                "</span></div>")

    op, out = 0, []
    for k in ORDEM:
        if k == "Retiradas" or not g[k]:
            continue
        op += sum(v for _, v in g[k])
        nome = k if k == "Receita" else "(-) " + k
        out.append(linha(nome, g[k]))
    out.append(res("Resultado operacional", op))
    liq = op + sum(v for _, v in g.get("Retiradas", []))
    if g.get("Retiradas"):
        out.append(linha("(-) Retiradas dos sócios",
                         g["Retiradas"]))
    if nc:
        liq += sum(v for _, v in nc)
        out.append(linha("&#9888; Não classificadas", nc))
    out.append(res("Resultado líquido", liq))
    return (f"{A}div class=cd>{A}div class=top>{A}h3>"
            f"DRE resumida</h3>{A}span class=sub>grupo > "
            f"categoria > lançamento</span></div>"
            + "".join(out) + "</div>")


def balanco(r):
    sai = r["emp"] + r["pes"]
    s, n = r["sal"], r["n"]
    cl = "ok" if s >= 0 else "neg"
    pe = "1 mês" if n == 1 else f"{n} meses"
    med = "" if n == 1 else (
        f" Média de {curto(s / n)} por mês.")
    return (f"{A}div class=cd>{A}div class=top>{A}h3>"
            f"Balanço do período</h3>{A}span class=sub>"
            f"{pe} · R$</span></div>"
            f"{A}div class=mini>{A}div>{A}span>Entradas"
            f"</span>{A}b>{nu(r['ent'])}</b></div>{A}div>"
            f"{A}span>Saídas</span>{A}b>{nu(sai)}</b></div>"
            f"{A}div>{A}span>Resultado</span>{A}b "
            f"class={cl}>{sn(s)}</b></div></div>"
            f"{A}div class=sub>Saídas incluem "
            f"{curto(r['pes'])} de retiradas dos sócios."
            f"{med}</div></div>")


def ler_seguro():
    try:
        return ler()
    except (OSError, ValueError, KeyError):
        return []


def exportar(d, p):
    """CSV p/ Excel: (nome_do_arquivo, texto)."""
    _, lin, _, p = periodo(d, ler_seguro(), p)
    nome = "lancamentos_" + sufixo(p) + ".csv"
    out = ["Data;Categoria;Grupo DRE;Valor"]
    for dt, c, v in lin:
        g = cfg("grupos", GRUPOS).get(
            c, "Nao classificada")
        c = c.replace(";", ",")
        if c[:1] in "=+-@":
            c = "'" + c  # evita formula no Excel
        val = f"{v / 100:.2f}".replace(".", ",")
        out.append(f"{dt.strftime('%d/%m/%Y')};{c};{g};{val}")
    return nome, "\r\n".join(out) + "\r\n"


def render(d, p=None):
    todos = d["meses"]
    d, lin, hist, p = periodo(d, ler_seguro(), p)
    meses, cats = d["meses"], d["categorias"]
    r = analise(d)
    r["proj"] = d.get("projetado")
    if len(hist) < len(todos):
        r["seg"] = todos[len(hist)]["saldo"]
    ini = sum(m["saldo"] for m in hist[:-len(meses)])
    if d.get("abertos"):
        rc = d["abertos"]["receber"]
        r["ina"] = d.get("inadimplencia_pct", 0)
        r["ven"] = sum(v for k, v in rc.items()
                       if k != "a_vencer")
    _, nc = grupos(cats)
    if nc:
        r["alertas"].append(("av", f"{len(nc)} "
            "categoria(s) sem grupo na DRE: "
            + ", ".join(c for c, _ in nc)))
    jm = juntar(meses)
    por = "trimestre" if jm[0]["mes"][0] == "T" else "ano"
    tit = "mês" if jm is meses else por
    out = [f"{A}style>{CSS}</style>", DEFS, status(r),
           filtro(todos, p), kpis(r, hist),
           compara(todos, meses, p),
           f"{A}div class=cd>{A}h3>Receitas x despesas por "
           f"{tit}</h3>{A}div class=leg>"
           f"{A}i style='background:var(--e1)'></i>Receitas"
           f"{A}i style='background:var(--b1)'></i>Despesas"
           f"{A}i style='background:var(--p1)'></i>Retiradas"
           "</div>" + colunas(jm) + "</div>"]
    if lin:
        out.append(f"{A}div class=cd>{A}h3>Fluxo de caixa "
                   f"diário</h3>{curva(lin, ini)}</div>")
    out.append(dre(cats, lin))
    out.append(dfc(jm, ini))
    out.append(prevreal(d, meses, len(hist) == len(todos)))
    out.append(f"{A}div class=cd>{A}h3>Saídas por "
               f"categoria</h3>{categorias(cats)}"
               f"{dica(cats, lin)}</div>")
    if d.get("abertos"):
        out.append(aging(d))
    out.append(tabelas(meses, lin))
    out.append(balanco(r))
    out.append(atencao(r))
    out.append(rodape(p))
    return "".join(out)


CSS += (".tb .sep{border-top:2px solid var(--bd)}"
        ".tb .fr{color:var(--tx2);font-style:italic}"
        ".tb .baixo{color:var(--av);font-weight:700}")


def grade(cols, linhas, larg="34%"):
    """Tabela alinhada: [(rotulo, [valores], classe)]."""
    s = [f"{A}div class=tb style='grid-template-columns:"
         f"{larg} repeat({len(cols)},1fr)'>"
         f"{A}span class=r></span>"]
    s += [f"{A}span class=fr>{c}</span>" for c in cols]
    for rot, vals, cl in linhas:
        s.append(f"{A}span class='r {cl}'>{rot}</span>")
        s += [f"{A}span class='{cl}'>{x}</span>"
              for x in vals]
    return "".join(s) + "</div>"


def dfc(meses, ini=0):
    """DFC direta: como o caixa andou mes a mes."""
    ab, sai = [], ini
    for m in meses:
        ab.append(sai)
        sai += m["saldo"]
    fe = [ab[i] + m["saldo"] for i, m in enumerate(meses)]
    cols = [nome_mes(m["mes"]) for m in meses]

    def f(vs):
        return [f"{A}b class={neg(v, '')}>{sn(v)}</b>"
                if v < 0 else sn(v) for v in vs]
    lin = sem_zero([("Saldo inicial", f(ab), "fr"),
           ("(+) Recebido", [nu(m["entra"]) for m in meses],
            ""),
           ("(-) Pago", [nu(-m["sai_empresa"])
                         for m in meses], ""),
           ("(-) Retiradas", [nu(-m["sai_pessoal"])
                              for m in meses], ""),
           ("= Geração", f([m["saldo"] for m in meses]),
            "rs sep"),
           ("Saldo final", f(fe), "rs")])
    return (f"{A}div class=cd>{A}div class=top>{A}h3>"
            f"DFC · fluxo de caixa</h3>{A}span class=sub>"
            f"método direto · R$</span></div>"
            + grade(cols, lin) + "</div>")


def prevreal(d, meses, fim):
    """Previsto (vencimentos) x realizado (pagos)."""
    pv = d.get("previsto")
    if not pv:
        return ""
    jm = juntar(meses)
    rm = {m["mes"]: m for m in jm}
    ks = [m["mes"] for m in jm]
    ult = meses[-1]["mes"]
    nx = [k for k in pv if (k[3:] + k[:2])
          > (ult[3:] + ult[:2])]
    if fim and nx and jm is meses:
        ks.append(nx[0])
    cols = [nome_mes(k) + ("*" if k not in rm else "")
            for k in ks]

    def prev(k, c):
        return sum(pv.get(x, {}).get(c, 0)
                   for x in rm.get(k, {}).get("ks", [k]))

    def pc(real, prev):
        if not prev:
            return "&#8212;"
        x = 100 * real / prev
        cl = " class=baixo" if round(x) < 90 else ""
        return f"{A}b{cl}>{x:.0f}%</b>"
    r_p = [prev(k, "entra") for k in ks]
    s_p = [prev(k, "sai") for k in ks]
    r_r = [rm[k]["entra"] if k in rm else None for k in ks]
    s_r = [-rm[k]["sai_empresa"] - rm[k]["sai_pessoal"]
           if k in rm else None for k in ks]

    def v(xs):
        return ["&#8212;" if x is None else nu(x) for x in xs]
    lin = [("A receber previsto", v(r_p), "fr"),
           ("Recebido", v(r_r), ""),
           ("% realizado", [pc(a, b) if a is not None
                            else "&#8212;"
                            for a, b in zip(r_r, r_p)], ""),
           ("A pagar previsto", v(s_p), "fr sep"),
           ("Pago", v(s_r), ""),
           ("% realizado", [pc(a, b) if a is not None
                            else "&#8212;"
                            for a, b in zip(s_r, s_p)], "")]
    nota = (f"{A}div class=sub style='margin-top:6px'>"
            "Previsto = títulos com vencimento no período. "
            "Abaixo de 90% fica em destaque."
            + (" * mês seguinte: só previsto." if
               len(ks) > len(jm) else "") + "</div>")
    return (f"{A}div class=cd>{A}div class=top>{A}h3>"
            f"Previsto x realizado</h3>{A}span class=sub>"
            f"títulos do ERP · R$</span></div>"
            + grade(cols, lin) + nota + "</div>")


CSS += (".rod{flex-wrap:wrap;gap:6px}"
        ".rod>span+span{margin-left:auto;"
        "white-space:nowrap}")


def empresa_nome():
    return cfg("empresa", EMPRESA)
