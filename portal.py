"""Etapa E1: portal com HTTPS, 2FA, BPO e filtros.

Cada cliente entra com email, senha e o codigo de 6 digitos
do celular, e ve so a propria empresa (RLS no banco). A
conexao e cifrada (HTTPS) e cada acesso vai para o log.
Uso: .venv/bin/python portal.py [IP_da_rede_local]
"""
import hashlib
import hmac
import html as h
import ipaddress
import os
import secrets
import sys
import time

import uvicorn
from fastapi import FastAPI, Form, Request
from fastapi.responses import (HTMLResponse, Response,
                               RedirectResponse)

import dados
import dois
from extras import CTX
from login import tela
from painel import bloqueado, erros, ip_local, pagina
from relatorio import relatorio
from visual import CSS, exportar, grade, render
from bpo import rotas

A = "<"
PORTA = 8789
SESSAO_S = 30 * 60
CERT, CHAVE = "cert.pem", "chave.pem"
sessoes = {}  # token -> (empresa_id, email, expira_em)
meio = {}  # token -> [empresa, email, totp, expira, erros]
usado = {}  # email -> ultimo passo do 2FA aceito
CAB = {"Cache-Control": "no-store",
       "X-Frame-Options": "DENY",
       "X-Content-Type-Options": "nosniff",
       "Referrer-Policy": "no-referrer",
       "Content-Language": "pt-BR",
       "Content-Security-Policy":
       "default-src 'none'; style-src 'unsafe-inline'; "
       "form-action 'self'"}
FORM = (f"{A}form method=post action=/login>"
        f"{A}input type=email name=email required "
        "autocomplete=username placeholder='Seu email' "
        "style='margin-bottom:10px'>"
        f"{A}input type=password name=senha required "
        "autocomplete=current-password "
        "placeholder='Sua senha'>"
        f"{A}button>Continuar</button></form>")
FORM2 = (f"{A}form method=post action=/codigo>"
         f"{A}p class=sub style='margin:0 0 12px'>"
         "Abra o app autenticador e digite o código "
         "de 6 dígitos do Portal.</p>"
         f"{A}input name=codigo required autofocus "
         "inputmode=numeric autocomplete=one-time-code "
         "maxlength=7 placeholder='000000' "
         "style='text-align:center;font-size:1.4em;"
         "letter-spacing:.3em'>"
         f"{A}button>Entrar no painel</button></form>"
         f"{A}p class=sub style='margin:12px 0 0'>"
         f"{A}a href=/logout>Voltar</a></p>")
FALSO = "300000$" + "00" * 16 + "$" + "00" * 32
SAIR = "href=/logout>Sair</a>"
ACOES = {"LOGIN_OK": "Entrou", "LOGIN_FALHA":
         "Senha errada", "CODIGO_FALHA": "Código errado",
         "SAIU": "Saiu", "EXPORTOU": "Exportou",
         "CLASSIFICOU": "BPO classificou",
         "CRIOU_LOGIN": "BPO criou login",
         "CRIOU_EMPRESA": "BPO criou empresa",
         "CONECTOU_ERP": "BPO ligou o ERP",
         "SINCRONIZOU": "Dados do ERP atualizados",
         "SYNC_FALHA": "Falha ao buscar o ERP",
         "CONECTOU_PSP": "BPO ligou o Asaas",
         "COBRANCA": "Cobrança criada",
         "PAGO_PSP": "Asaas avisou: pago"}
VAZIO = (f"{A}div class=cd>{A}h3>Ainda sem dados</h3>"
         f"{A}p class=sub>O BPO ainda está ligando o ERP "
         "desta empresa.</p></div>"
         f"{A}div class=rod>{A}span></span>{A}span>"
         f"{A}a class=tg href=/logout>Sair</a>"
         "</span></div>")

app = FastAPI(docs_url=None, redoc_url=None,
              openapi_url=None)
app.include_router(rotas)


@app.middleware("http")
async def protege(req: Request, chamar):
    ip = ipaddress.ip_address(req.client.host)
    if not (ip.is_private or ip.is_loopback):
        return Response("proibido", 403)
    r = await chamar(req)
    for k, v in CAB.items():
        r.headers[k] = v
    return r


NADA = (f"{A}div class=cd>{A}h3>Nada neste filtro</h3>"
        f"{A}p class=sub>Sem pagamentos para este "
        "centro de custo ou categoria.</p>"
        f"{A}a class=tg href=/>Limpar filtros</a></div>")


def confere(senha, guardado):
    it, sal, x = guardado.split("$")
    y = hashlib.pbkdf2_hmac("sha256", senha.encode(),
                            bytes.fromhex(sal), int(it))
    return hmac.compare_digest(y.hex(), x)


def sessao(req):
    t = req.cookies.get("sid", "")
    s = sessoes.get(t)
    if s and s[2] > time.time():
        return s
    sessoes.pop(t, None)
    return None


def pagina_(corpo, cod=200):
    return HTMLResponse(pagina("Portal Financeiro", corpo),
                        cod)


def cookie(r, nome, valor, idade):
    r.set_cookie(nome, valor, max_age=idade, secure=True,
                 httponly=True, samesite="strict")


def falhou(ip, eid, email, acao, form, msg):
    n, t0 = erros.get(ip, (0, time.time()))
    erros[ip] = (n + 1, t0)
    dados.registra(eid, email, ip, acao)
    print(time.strftime("%H:%M:%S"), ip, acao, n + 1)
    return pagina_(tela(msg, form), 401)


def abre_sessao(ip, eid, email, extra=""):
    erros.pop(ip, None)
    t = secrets.token_urlsafe(32)
    sessoes[t] = (eid, email, time.time() + SESSAO_S)
    dados.registra(eid, email, ip, "LOGIN_OK", extra)
    print(time.strftime("%H:%M:%S"), ip, "LOGIN OK", email)
    r = RedirectResponse("/", 303)
    cookie(r, "sid", t, SESSAO_S)
    r.delete_cookie("pre")
    return r


def na_empresa(s, faz, cc=None, cat=None):
    """Roda faz(resumo) com os dados so desta empresa."""
    ctx, d = dados.carregar(s[0], cc, cat)
    tk = CTX.set(ctx)
    try:
        return faz(d)
    finally:
        CTX.reset(tk)


@app.get("/")
def inicio(req: Request, p: str | None = None,
           cc: str | None = None,
           cat: str | None = None):
    s = sessao(req)
    if not s:
        return pagina_(tela("", FORM))
    vazio = NADA if cc or cat else VAZIO
    corpo = na_empresa(s, lambda d: render(d, p)
                       if d["meses"] else
                       f"{A}style>{CSS}</style>" + vazio,
                       cc, cat)
    corpo = corpo.replace(
        SAIR, f"href=/acessos>Acessos</a>{A}a class=tg "
        + SAIR, 1)
    return pagina_(corpo)


@app.post("/login")
def entrar(req: Request, email: str = Form(""),
           senha: str = Form("")):
    ip = req.client.host
    if bloqueado(ip):
        return pagina_(tela("Muitas tentativas. Aguarde "
                            "5 min.", False), 429)
    email = email.strip().lower()[:200]
    u = dados.busca(email)
    ok = confere(senha, u[2] if u else FALSO)
    if not (u and ok):
        return falhou(ip, u[1] if u else None, email,
                      "LOGIN_FALHA", FORM,
                      "Email ou senha incorretos.")
    if not u[3]:
        return abre_sessao(ip, u[1], email, "sem 2FA")
    t = secrets.token_urlsafe(32)
    meio[t] = [u[1], email, u[3], time.time() + 300, 0]
    r = pagina_(tela("", FORM2))
    cookie(r, "pre", t, 300)
    return r


@app.post("/codigo")
def codigo(req: Request, codigo: str = Form("")):
    ip = req.client.host
    t = req.cookies.get("pre", "")
    m = meio.get(t)
    if bloqueado(ip) or not m or m[3] < time.time() \
            or m[4] >= 5:
        meio.pop(t, None)
        return pagina_(tela("Tempo esgotado ou muitas "
                            "tentativas. Entre de novo.",
                            False), 429)
    p = dois.confere(m[2], codigo, usado.get(m[1], 0))
    if not p:
        m[4] += 1
        return falhou(ip, m[0], m[1], "CODIGO_FALHA", FORM2,
                      "Código errado ou já usado. "
                      "Espere o próximo código do app.")
    usado[m[1]] = p
    meio.pop(t, None)
    return abre_sessao(ip, m[0], m[1], "com 2FA")


@app.get("/logout")
def sair(req: Request):
    s = sessao(req)
    if s:
        sessoes.pop(req.cookies.get("sid"), None)
        dados.registra(s[0], s[1], req.client.host, "SAIU")
    meio.pop(req.cookies.get("pre", ""), None)
    r = RedirectResponse("/", 303)
    r.delete_cookie("sid")
    r.delete_cookie("pre")
    return r


@app.get("/acessos")
def acessos(req: Request):
    s = sessao(req)
    if not s:
        return RedirectResponse("/", 303)
    lin = []
    for q, u, ip, ac, det in dados.acessos(s[0]):
        rot = ACOES.get(ac, ac)
        if det:
            rot += (f"{A}br>{A}span class=sub style="
                    "'overflow-wrap:anywhere'>"
                    f"{h.escape(det)}"
                    "</span>")
        cl = "baixo" if "FALHA" in ac else ""
        u = "BPO" if u.startswith("bpo:") else u
        lin.append((q.astimezone().strftime("%d/%m %H:%M"),
                    [h.escape(u), rot], cl))
    tab = grade(["Quem", "O quê"], lin, "28%") if lin \
        else f"{A}p class=sub>Nenhum registro ainda.</p>"
    return pagina_(
        f"{A}style>{CSS}</style>{A}div class=cd>"
        f"{A}div class=top>{A}h3>Acessos da empresa</h3>"
        f"{A}span class=sub>últimos 40</span></div>{tab}"
        f"{A}p class=sub style='margin-top:10px'>Só "
        "aparecem os acessos desta empresa. Em destaque: "
        "senha ou código errado.</p></div>"
        f"{A}div class=rod>{A}span></span>{A}span>"
        f"{A}a class=tg href=/>Voltar ao painel</a>"
        "</span></div>")


def baixar(req, p, gera, tipo, cc=None, cat=None):
    s = sessao(req)
    if not s:
        return RedirectResponse("/", 303)
    nome, b = na_empresa(s, lambda d: gera(d, p)
                         if d["meses"] else (0, 0),
                         cc, cat)
    if not nome:
        return RedirectResponse("/", 303)
    if isinstance(b, str):
        b = b.encode("utf-8-sig")
    dados.registra(s[0], s[1], req.client.host,
                   "EXPORTOU", nome)
    return Response(b, media_type=tipo, headers={
        "Content-Disposition":
        f'attachment; filename="{nome}"'})


@app.get("/exportar.csv")
def csv(req: Request, p: str | None = None,
        cc: str | None = None, cat: str | None = None):
    return baixar(req, p, exportar,
                  "text/csv; charset=utf-8", cc, cat)


@app.get("/relatorio.pdf")
def pdf(req: Request, p: str | None = None,
        cc: str | None = None, cat: str | None = None):
    return baixar(req, p, relatorio, "application/pdf",
                  cc, cat)


if __name__ == "__main__":
    host = sys.argv[1] if len(sys.argv) > 1 else ip_local()
    if not ipaddress.ip_address(host).is_private and \
            host != "127.0.0.1":
        raise SystemExit("ERRO: IP nao e de rede local")
    if not (os.path.exists(CERT) and os.path.exists(CHAVE)):
        raise SystemExit("ERRO: falta cert.pem/chave.pem")
    print(f"Portal em https://{host}:{PORTA}  (Ctrl+C sai)")
    uvicorn.run(app, host=host, port=PORTA,
                log_level="warning", server_header=False,
                ssl_certfile=CERT, ssl_keyfile=CHAVE)
