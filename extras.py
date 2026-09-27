"""Etapa 3e: graficos extras (saldo dia a dia etc)."""
import contextvars
import csv
import datetime as dt
import html
import math
import os

A = "<"  # tags montadas assim p/ colar no chat
# Etapa C2: dados da empresa da vez (1 por pedido).
CTX = contextvars.ContextVar("empresa", default=None)


def cfg(chave, padrao):
    c = CTX.get()
    return c[chave] if c and chave in c else padrao


EXTRATO = ("extrato_omie.csv"
           if os.path.exists("extrato_omie.csv")
           else "extrato_falso.csv")
AZUL, LAR, CINZA = "#2a78d6", "#eb6834", "#52514e"
CSS3 = (".dn{display:flex;align-items:center;gap:16px}"
        ".rosca{width:110px;height:110px;border-radius:50%;"
        "flex:none;display:grid;place-items:center}"
        ".rosca b{background:#fff;width:70px;height:70px;"
        "border-radius:50%;display:grid;place-items:center}"
        ".dn p{margin:4px 0;font-size:.9em}"
        ".chips{display:flex;flex-wrap:wrap;gap:6px}"
        ".chip{border:1px solid #ddd;border-radius:14px;"
        "padding:4px 10px;font-size:.85em}"
        ".dn2{color:#b71c1c}.up{color:#1b5e20}"
        ".top5 td{padding:4px 6px}svg{width:100%;"
        "height:auto;display:block}")


def brl(c):
    s = "-" if c < 0 else ""
    r, cent = divmod(abs(int(c)), 100)
    return s + f"R$ {r:,}".replace(",", ".") + f",{cent:02d}"


def mil(c):
    if not c:
        return "0"
    v = c / 100000
    t = f"{v:.1f}".rstrip("0").rstrip(".")
    return t.replace(".", ",") + " mil"


def cent(txt):
    t = txt.strip().replace(".", "").replace(",", ".")
    return round(float(t) * 100)


def ler():
    if CTX.get():
        return CTX.get()["lin"]
    lin = []
    with open(EXTRATO, encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f, delimiter=";"):
            d = dt.datetime.strptime(r["data"], "%d/%m/%Y")
            lin.append((d.date(), r["descricao"],
                        cent(r["valor"])))
    return sorted(lin)


def rosca(meses):
    emp = -sum(m["sai_empresa"] for m in meses)
    pes = -sum(m["sai_pessoal"] for m in meses)
    tot = emp + pes or 1
    p = 100 * pes / tot
    g = (f"conic-gradient({LAR} 0 {p:.2f}%,#fff 0 "
         f"calc({p:.2f}% + .6%),{AZUL} 0 99.4%,#fff 0)")
    pt = f"{p:.1f}%".replace(".", ",")
    return (f"{A}h3>Para onde foi o dinheiro que saiu</h3>"
            f"{A}div class=dn>{A}div class=rosca "
            f"style='background:{g}'>{A}b>{pt}</b></div>"
            f"{A}div>{A}p>{A}i class=sw style='background:"
            f"{LAR};margin-left:0'></i>Pessoal {brl(pes)}"
            f"</p>{A}p>{A}i class=sw style='background:"
            f"{AZUL};margin-left:0'></i>Empresa {brl(emp)}"
            f"</p>{A}p style='color:{CINZA}'>De cada R$ 100"
            f" que sairam, R$ {p:.0f} foram gastos pessoais"
            "</p></div></div>")


def variacao(meses):
    out = [f"{A}h3>Saldo mes a mes</h3>{A}div class=chips>"]
    ant = None
    for m in meses:
        s = m["saldo"]
        txt = f"{html.escape(m['mes'])}: {brl(s)}"
        if ant:
            v = 100 * (s - ant) / abs(ant)
            cl, seta = ("up", "&#9650;") if v >= 0 else \
                ("dn2", "&#9660;")
            vt = f"{abs(v):.1f}%".replace(".", ",")
            txt += f" {A}span class={cl}>{seta} {vt}</span>"
        out.append(f"{A}span class=chip>{txt}</span>")
        ant = s
    return "".join(out) + "</div>"


def passo_bonito(x):
    p = 10 ** math.floor(math.log10(x or 1))
    for m in (1, 2, 5, 10):
        if m * p >= x:
            return m * p


def linha(lin):
    dia, fim = lin[0][0], lin[-1][0]
    por_dia = {}
    for d, _, v in lin:
        por_dia[d] = por_dia.get(d, 0) + v
    pts, acc = [], 0
    while dia <= fim:
        acc += por_dia.get(dia, 0)
        pts.append((dia, acc))
        dia += dt.timedelta(days=1)
    W, H, L, T, B = 340, 170, 44, 10, 22
    lo = min(0, min(v for _, v in pts))
    hi = max(v for _, v in pts) or 1
    passo = passo_bonito((hi - lo) / 3)
    lo = passo * math.floor(lo / passo)
    hi = passo * math.ceil(hi / passo)
    n = len(pts) - 1 or 1

    def x(i):
        return L + (W - L - 6) * i / n

    def y(v):
        return T + (H - T - B) * (hi - v) / (hi - lo)
    s = [f"{A}h3>Saldo acumulado dia a dia</h3>",
         f"{A}svg viewBox='0 0 {W} {H}' role=img "
         "aria-label='Saldo acumulado'>"]
    for k in range(round((hi - lo) / passo) + 1):
        v = lo + passo * k
        s.append(f"{A}line x1={L} x2={W - 6} y1={y(v):.1f} "
                 f"y2={y(v):.1f} stroke='#e5e5e5'/>"
                 f"{A}text x={L - 4} y={y(v) + 3:.1f} "
                 f"font-size=9 fill='{CINZA}' "
                 f"text-anchor=end>{mil(v)}</text>")
    for i, (d, _) in enumerate(pts):
        if d.day == 1:
            s.append(f"{A}text x={x(i):.1f} y={H - 6} "
                     f"font-size=9 fill='{CINZA}'>"
                     f"{d.strftime('%m/%Y')}</text>")
    xy = " ".join(f"{x(i):.1f},{y(v):.1f}"
                  for i, (_, v) in enumerate(pts))
    s.append(f"{A}polygon fill='{AZUL}' opacity=.12 "
             f"points='{x(0):.1f},{y(lo):.1f} {xy} "
             f"{x(n):.1f},{y(lo):.1f}'/>"
             f"{A}polyline fill=none stroke='{AZUL}' "
             f"stroke-width=2 points='{xy}'/>")
    for i, (d, v) in enumerate(pts):
        s.append(f"{A}rect x={x(i) - 2:.1f} y={T} width=4 "
                 f"height={H - T - B} fill=transparent>"
                 f"{A}title>{d.strftime('%d/%m')}: {brl(v)}"
                 "</title></rect>")
    ul = pts[-1][1]
    s.append(f"{A}circle cx={x(n):.1f} cy={y(ul):.1f} r=4 "
             f"fill='{AZUL}' stroke='#fff' stroke-width=2/>"
             "</svg>")
    s.append(f"{A}p style='font-size:.85em;color:{CINZA}'>"
             f"Termina em {brl(ul)}. Toque no grafico para "
             "ver o saldo de cada dia.</p>")
    return "".join(s)


def top5(lin):
    sai = sorted((c for c in lin if c[2] < 0),
                 key=lambda c: c[2])[:5]
    rows = "".join(
        f"{A}tr>{A}td>{d.strftime('%d/%m')}</td>"
        f"{A}td>{html.escape(n)}</td>"
        f"{A}td class=n style='color:#b71c1c'>{brl(v)}"
        "</td></tr>" for d, n, v in sai)
    return (f"{A}h3>5 maiores saidas</h3>"
            f"{A}table class=top5>{rows}</table>")


def extras(meses):
    out = [f"{A}style>{CSS3}</style>", rosca(meses),
           variacao(meses)]
    try:
        lin = ler()
        out += [linha(lin), top5(lin)]
    except (OSError, ValueError, KeyError) as e:
        out.append(f"{A}p>(extrato indisponivel: "
                   f"{html.escape(str(e))})</p>")
    return "".join(out)
