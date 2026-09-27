"""Etapa 4f: relatorio em PDF, so com Python (sem libs).

Monta o PDF na mao: fonte Helvetica do proprio leitor,
texto em WinAnsi (acentos ok). Usa os mesmos numeros do
painel (DRE, DFC, previsto x realizado, avisos).
"""
import textwrap
import time

from dono import analise
from visual import (CENTROS, ORDEM, empresa_nome,
                    grupos, juntar, ler_seguro,
                    rotulo, sufixo, de_ate,
                    nome_mes, nu, periodo, sn)
from extras import cfg

AZUL = "0.07 0.14 0.62"
VERM = "0.78 0.16 0.16"
CINZA = "0.4 0.4 0.4"
LARG = {c: 278 for c in " .,:;!|il'"}
LARG.update({c: 556 for c in "0123456789$"})
LARG.update({"-": 333, "(": 333, ")": 333, "%": 889})


def larg(s, tam):
    return sum(LARG.get(c, 556) for c in s) * tam / 1000


def esc(s):
    return (s.replace("\\", "\\\\").replace("(", "\\(")
            .replace(")", "\\)"))


class Doc:
    def __init__(self):
        self.pags = []
        self.nova()

    def nova(self):
        self.c = []
        self.pags.append(self.c)
        self.y = 790

    def cabe(self, h):
        if self.y - h < 60:
            self.nova()

    def t(self, x, s, tam=9, b=False, cor=None, dir=False):
        if dir:
            x -= larg(s, tam)
        op = (f"BT /F{2 if b else 1} {tam} Tf {x:.1f} "
              f"{self.y:.1f} Td ({esc(s)}) Tj ET")
        if cor:
            op = f"q {cor} rg {op} Q"
        self.c.append(op)

    def risco(self, x1=40, x2=555):
        y = self.y - 5
        self.c.append(f"q 0.8 G 0.5 w {x1} {y:.1f} m "
                      f"{x2} {y:.1f} l S Q")

    def desce(self, h=14):
        self.y -= h

    def titulo(self, s):
        self.cabe(60)
        self.desce(10)
        self.t(40, s, 12, True, AZUL)
        self.risco()
        self.desce(18)

    def grade(self, cols, linhas):
        """cols: titulos; linhas: (rot, [val], negrito)."""
        xs = [555 - 80 * (len(cols) - 1 - i)
              for i in range(len(cols))]
        self.cabe(14 * (len(linhas) + 1))
        if any(cols):
            for x, c in zip(xs, cols):
                self.t(x, c, 8, cor=CINZA, dir=True)
            self.desce()
        for rot, vals, b in linhas:
            self.t(40, rot, 9, b)
            for x, v in zip(xs, vals):
                cor = VERM if v.startswith("-") else None
                self.t(x, v, 9, b, cor, True)
            self.desce()

    def bytes(self):
        n = len(self.pags)
        emp = esc(empresa_nome())
        conts = []
        for i, c in enumerate(self.pags, 1):
            c.append(f"q {CINZA} rg BT /F1 7 Tf 40 30 Td "
                     f"(Portal Financeiro · {emp} · "
                     f"página {i} de {n}) Tj ET Q")
            conts.append("\n".join(c).encode("cp1252",
                                                 "replace"))
        objs = [b"<< /Type /Catalog /Pages 2 0 R >>",
                ("<< /Type /Pages /Kids [" + " ".join(
                    f"{5 + 2 * i} 0 R" for i in range(n))
                 + f"] /Count {n} >>").encode()]
        for f in ("Helvetica", "Helvetica-Bold"):
            objs.append(f"<< /Type /Font /Subtype /Type1 "
                        f"/BaseFont /{f} /Encoding "
                        f"/WinAnsiEncoding >>".encode())
        for i, c in enumerate(conts):
            objs.append(
                ("<< /Type /Page /Parent 2 0 R /MediaBox "
                 "[0 0 595 842] /Resources << /Font << "
                 "/F1 3 0 R /F2 4 0 R >> >> /Contents "
                 f"{6 + 2 * i} 0 R >>").encode())
            objs.append(f"<< /Length {len(c)} >>\nstream\n"
                        .encode() + c + b"\nendstream")
        out = bytearray(b"%PDF-1.4\n")
        pos = []
        for i, o in enumerate(objs, 1):
            pos.append(len(out))
            out += f"{i} 0 obj\n".encode() + o + b"\nendobj\n"
        xref = len(out)
        out += (f"xref\n0 {len(objs) + 1}\n"
                "0000000000 65535 f \n").encode()
        for p in pos:
            out += f"{p:010d} 00000 n \n".encode()
        out += (f"trailer\n<< /Size {len(objs) + 1} "
                f"/Root 1 0 R >>\nstartxref\n{xref}\n"
                "%%EOF\n").encode()
        return bytes(out)


def pct(a, b):
    return f"{100 * a / b:.0f}%" if b > 1 else "-"


def relatorio(d, p=None):
    """Retorna (nome_do_arquivo, bytes do PDF)."""
    todos = d["meses"]
    d, lin, hist, p = periodo(d, ler_seguro(), p)
    meses, cats = d["meses"], d["categorias"]
    r = analise(d)
    ini = sum(m["saldo"] for m in hist[:-len(meses)])
    jm = juntar(meses)
    m0, m1 = meses[0]["mes"], meses[-1]["mes"]
    per = de_ate(m0, m1)
    doc = Doc()
    doc.t(40, empresa_nome(), 18, True, AZUL)
    doc.desce(20)
    doc.t(40, f"Relatório financeiro · {rotulo(p)} "
          f"({per})", 11)
    doc.desce(14)
    f = cfg("filtro", None) or {}
    fx = [CENTROS.get(f["cc"], f["cc"])] if f.get("cc") \
        else []
    fx += [n for k, n in f.get("cats", [])
           if k == f.get("cat")]
    if fx:
        doc.t(40, "Filtro: " + " · ".join(fx), 9,
              cor=VERM)
        doc.desce(14)
    doc.t(40, "Gerado em " + time.strftime(
        "%d/%m/%Y %H:%M") + " · dados do ERP · valores em R$",
        8, cor=CINZA)
    doc.desce(10)

    sai = r["emp"] + r["pes"]
    doc.titulo("Balanço do período")
    ina = d.get("inadimplencia_pct")
    lin_b = [("Entradas", [nu(r["ent"])], False),
             ("Saídas (inclui retiradas)", [nu(sai)], False),
             ("Resultado", [sn(r["sal"])], True),
             ("Margem operacional",
              [pct(r["ent"] - r["emp"], r["ent"])], False)]
    if ina is not None:
        lin_b.append(("Inadimplência (hoje)",
                      [f"{ina:.1f}%".replace(".", ",")],
                      False))
    doc.grade([""], lin_b)

    doc.titulo("DRE resumida")
    g, nc = grupos(cats)
    rec = sum(v for _, v in g["Receita"]) or 1
    op, dl = 0, []
    for k in ORDEM:
        if k == "Retiradas" or not g[k]:
            continue
        tot = sum(v for _, v in g[k])
        op += tot
        nome = k if k == "Receita" else "(-) " + k
        dl.append((nome, [nu(abs(tot)),
                          pct(abs(tot), rec)], True))
        dl += [("      " + c, [nu(abs(v)), ""], False)
               for c, v in g[k]]
    dl.append(("= Resultado operacional", [sn(op), ""],
               True))
    liq = op + sum(v for _, v in g.get("Retiradas", []))
    if g.get("Retiradas"):
        tr = sum(v for _, v in g["Retiradas"])
        dl.append(("(-) Retiradas dos sócios",
                   [nu(abs(tr)), pct(abs(tr), rec)], True))
    if nc:
        liq += sum(v for _, v in nc)
        dl.append(("(!) Não classificadas",
                   [nu(abs(sum(v for _, v in nc))), ""],
                   True))
    dl.append(("= Resultado líquido", [sn(liq), ""], True))
    doc.grade(["R$", "% receita"], dl)

    doc.titulo("DFC · fluxo de caixa (método direto)")
    ab, s = [], ini
    for m in jm:
        ab.append(s)
        s += m["saldo"]
    doc.grade([nome_mes(m["mes"]) for m in jm], [
        ("Saldo inicial", [sn(x) for x in ab], False),
        ("(+) Recebido", [nu(m["entra"]) for m in jm],
         False),
        ("(-) Pago", [nu(-m["sai_empresa"]) for m in jm],
         False),
        ("(-) Retiradas", [nu(-m["sai_pessoal"])
                           for m in jm], False),
        ("= Geração", [sn(m["saldo"]) for m in jm], True),
        ("Saldo final", [sn(a + m["saldo"])
                         for a, m in zip(ab, jm)], True)])

    pv = d.get("previsto") or {}
    if pv:
        doc.titulo("Previsto x realizado")
        ks = [m.get("ks", [m["mes"]]) for m in jm]
        rp = [sum(pv.get(x, {}).get("entra", 0)
                  for x in k) for k in ks]
        sp = [sum(pv.get(x, {}).get("sai", 0)
                  for x in k) for k in ks]
        rr = [m["entra"] for m in jm]
        sr = [-m["sai_empresa"] - m["sai_pessoal"]
              for m in jm]
        doc.grade([nome_mes(m["mes"]) for m in jm], [
            ("A receber previsto", [nu(x) for x in rp],
             False),
            ("Recebido", [nu(x) for x in rr], False),
            ("% realizado", [pct(a, b)
                             for a, b in zip(rr, rp)], True),
            ("A pagar previsto", [nu(x) for x in sp], False),
            ("Pago", [nu(x) for x in sr], False),
            ("% realizado", [pct(a, b)
                             for a, b in zip(sr, sp)], True)])

    av = [x for c, x in r["alertas"] if c == "av"]
    if nc:
        av.append(f"{len(nc)} categoria(s) sem grupo na DRE")
    doc.titulo("Pontos de atenção")
    for x in av or ["Nenhum ponto de atenção no período."]:
        for i, parte in enumerate(textwrap.wrap(x, 95)):
            doc.cabe(14)
            doc.t(40, ("- " if i == 0 else "  ") + parte, 9)
            doc.desce()
    nome = "relatorio_" + sufixo(p) + ".pdf"
    return nome, doc.bytes()
