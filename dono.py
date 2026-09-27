"""Etapa 3g: resumo do dono + limites ajustaveis."""
import html
from extras import brl, ler


def rs(c):
    """R$ sem centavos, igual ao painel."""
    return brl(round(c / 100) * 100)[:-3]

A = "<"  # tags montadas assim p/ colar no chat
# Ajuste aqui os limites dos alertas (em %):
LIMITES = {"pessoal": 20, "queda_vendas": 5,
           "maior_gasto": 30}
FIXOS = {"Aluguel", "Contas da loja", "Banco"}
DIAS = ["segunda", "terca", "quarta", "quinta",
        "sexta", "sabado", "domingo"]
CSS4 = (".kp{display:grid;grid-template-columns:1fr 1fr;"
        "gap:8px}.k{background:#fff;border:1px solid "
        "#e3e3e3;border-radius:8px;padding:8px}"
        ".k small{display:block;color:#52514e}"
        ".k b{display:block;font-size:1.25em;margin:2px 0}"
        ".al{margin:10px 0 0;padding:0;list-style:none}"
        ".al li{margin:6px 0;padding:6px 8px;"
        "border-radius:6px;font-size:.9em}"
        ".av{background:#fff3e0;border-left:4px solid "
        "#e65100}.in{background:#eef4fc;border-left:4px "
        "solid #2a78d6}")


def pc(x):
    return f"{x:.0f}%"


def kpi(titulo, valor, nota):
    return (f"{A}div class=k>{A}small>{titulo}</small>"
            f"{A}b>{valor}</b>{A}small>{nota}</small></div>")


def analise(d):
    """Calcula os numeros e alertas (sem HTML)."""
    meses = d["meses"]
    r = {"n": len(meses), "m0": meses[0]["mes"],
         "m1": meses[-1]["mes"],
         "ent": sum(m["entra"] for m in meses) or 1,
         "emp": -sum(m["sai_empresa"] for m in meses),
         "pes": -sum(m["sai_pessoal"] for m in meses),
         "sal": sum(m["saldo"] for m in meses),
         "sal_ult": meses[-1]["saldo"]}
    n, ent, emp, pes = r["n"], r["ent"], r["emp"], r["pes"]
    sai = emp + pes or 1
    v0, v1 = meses[0]["entra"], meses[-1]["entra"]
    r["tend"] = 100 * (v1 - v0) / (v0 or 1)
    r["precisa"] = sai / n
    r["cobre"] = (ent / n) / r["precisa"]
    r["fixo"] = -sum(v for c, v in d["categorias"].items()
                     if c in FIXOS) / n
    al = []
    if 100 * pes / sai > LIMITES["pessoal"]:
        al.append(("av", "Retiradas dos sócios: "
                   f"{rs(pes / n)} por mês. Sem elas, o "
                   f"caixa teria {rs(ent - emp)} (real "
                   f"{rs(r['sal'])})."))
    if r["tend"] < -LIMITES["queda_vendas"]:
        al.append(("av", "Receitas caíram "
                   f"{abs(r['tend']):.0f}% de {r['m0']} "
                   f"para {r['m1']}."))
    try:
        vendas = [(x, v) for x, _, v in ler() if v > 0]
    except (OSError, ValueError, KeyError):
        vendas = []
    r["qtd"] = len(vendas)
    if vendas:
        tot = sum(v for _, v in vendas)
        r["ticket"] = tot / len(vendas)
        sem = [0] * 7
        for x, v in vendas:
            sem[x.weekday()] += v
        b = max(range(7), key=lambda i: sem[i])
        al.append(("in", f"{DIAS[b].capitalize()} e o dia "
                   f"que mais vende: {brl(sem[b])} no "
                   f"periodo ({pc(100 * sem[b] / tot)})."))
    gs = sorted(((c, -v) for c, v in d["categorias"].items()
                 if v < 0), key=lambda cv: -cv[1])
    if gs and 100 * gs[0][1] / sai > LIMITES["maior_gasto"]:
        c, v = gs[0]
        al.append(("in", f"{html.escape(c)} e o maior "
                   f"gasto ({pc(100 * v / sai)} das "
                   "saidas): negociar aqui rende mais."))
    al.append(("in", "Custo fixo (aluguel, contas, banco):"
               f" {brl(r['fixo'])} por mes."))
    r["alertas"] = al
    return r


def dono(r):
    n, ent, emp, pes = r["n"], r["ent"], r["emp"], r["pes"]
    seta = "&#9650;" if r["tend"] >= 0 else "&#9660;"
    k = [kpi("Vendas por mes (media)", brl(ent / n),
             f"{seta} {abs(r['tend']):.0f}% de {r['m0']} "
             f"a {r['m1']}"),
         kpi("Lucro da loja", brl(ent - emp),
             f"{pc(100 * (ent - emp) / ent)} das vendas, "
             "antes das retiradas"),
         kpi("Sobrou no caixa", brl(r["sal"]),
             f"{pc(100 * r['sal'] / ent)} das vendas"),
         kpi("Retirada pessoal por mes", brl(pes / n),
             f"{pc(100 * pes / (emp + pes or 1))} de tudo "
             "que saiu"),
         kpi("Precisa vender por mes", brl(r["precisa"]),
             "para pagar tudo; voce vende "
             f"{r['cobre']:.1f}x isso".replace(".", ","))]
    if r["qtd"]:
        k.append(kpi("Ticket medio", brl(r["ticket"]),
                     f"{r['qtd']} vendas no periodo"))
    ic = {"av": "&#9888; ", "in": "&#8226; "}
    lis = "".join(f"{A}li class={c}>{ic[c]}{t}</li>"
                  for c, t in r["alertas"])
    return (f"{A}style>{CSS4}</style>{A}div class=kp>"
            + "".join(k) + f"</div>{A}ul class=al>{lis}"
            "</ul>")
