"""Etapa D1: area do BPO (/bpo), o apicultor das colmeias.

O BPO ve todas as empresas, cria empresa e login, e liga
cada categoria do ERP a um grupo da DRE (uma vez por
cliente). 2FA sempre, cookie so em /bpo, token anti-CSRF
em todo formulario, e tudo vai para o log da empresa.
"""
import hashlib
import hmac
import html
import secrets
import time

import psycopg
from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

import dados
import dois
from login import tela
from painel import bloqueado, erros, pagina
from visual import CSS, ORDEM
import erp
from omie import ErroErp
import json
import cobranca
from cobranca import ErroPsp
from extras import brl

A = "<"
SESSAO_S = 30 * 60
rotas = APIRouter(prefix="/bpo")
sessoes = {}  # token -> (email, expira, csrf)
meio = {}  # token -> [email, totp, expira, erros]
usado = {}
FALSO = "300000$" + "00" * 16 + "$" + "00" * 32
CSS_B = (".bl{display:flex;justify-content:space-between;"
         "align-items:center;gap:8px;padding:8px 0;"
         "border-top:1px solid var(--bd)}"
         ".bl b{display:block}.bl .sub{font-size:.8em}"
         ".bf{display:flex;gap:6px;flex-wrap:wrap;"
         "align-items:center}"
         ".bf select,.bf input{padding:7px 8px;"
         "font-size:.9em;border-radius:8px;"
         "border:1px solid var(--bd);background:var(--bg);"
         "color:var(--tx);max-width:100%}"
         ".msg{background:var(--ruimbg);color:var(--ruim);"
         "border-radius:10px;padding:8px;font-size:.88em}"
         ".bf button,.bt{padding:7px 12px;font-size:.85em;"
         "font-weight:700;border:0;border-radius:8px;"
         "color:#fff;background:var(--h1);"
         "text-decoration:none}"
         ".nc{background:var(--avbg);border-radius:8px;"
         "padding:8px 6px}"
         ".tag{font-size:.75em;padding:2px 8px;"
         "border-radius:10px;border:1px solid var(--bd);"
         "color:var(--tx2);white-space:nowrap}"
         ".tag.av{color:var(--av);border-color:var(--av);"
         "font-weight:700}")
FORM = (f"{A}form method=post action=/bpo/login>"
        f"{A}p class=sub style='margin:0 0 12px'>"
        "Área do BPO</p>"
        f"{A}input type=email name=email required "
        "autocomplete=username placeholder='Email do BPO' "
        "style='margin-bottom:10px'>"
        f"{A}input type=password name=senha required "
        "autocomplete=current-password "
        "placeholder='Senha'>"
        f"{A}button>Continuar</button></form>")
FORM2 = (f"{A}form method=post action=/bpo/codigo>"
         f"{A}p class=sub style='margin:0 0 12px'>"
         "Código de 6 dígitos do app autenticador.</p>"
         f"{A}input name=codigo required autofocus "
         "inputmode=numeric autocomplete=one-time-code "
         "maxlength=7 placeholder='000000' "
         "style='text-align:center;font-size:1.4em;"
         "letter-spacing:.3em'>"
         f"{A}button>Entrar</button></form>")


CSS_B += (".okm{background:var(--okbg);color:var(--ok);"
          "border-radius:10px;padding:8px;font-size:.88em}"
          ".erp .bf input{flex:1 1 140px}")


CSS_B += (".tok{word-break:break-all;font-family:"
          "monospace;background:var(--bg);padding:6px;"
          "border-radius:8px;border:1px dashed var(--av)}"
          ".tag.ok{color:var(--ok);border-color:var(--ok)}")


def linha_cob(s, eid, x, demo):
    """1 conta a receber em aberto e o que fazer com ela."""
    tid, venc, valor, cat, pid, st, _, pago = x
    e = html.escape
    esq = (f"{A}span>{A}b>{brl(valor)}</b>{A}span "
           f"class=sub>{e(cat)} · vence "
           f"{venc.strftime('%d/%m/%y')}</span></span>")
    base = (f"{oculto(s)}{A}input type=hidden name=eid "
            f"value={eid}>")
    if st == "paga":
        dir_ = (f"{A}span class='tag ok'>pago "
                f"{pago.strftime('%d/%m')}</span>")
    elif st == "pendente":
        dir_ = f"{A}span class=tag>aguardando</span>"
        if demo:
            dir_ += (f"{A}form class=bf method=post "
                     f"action=/bpo/simula>{base}{A}input "
                     f"type=hidden name=pid value='{e(pid)}'>"
                     f"{A}button>Simular pago</button>"
                     "</form>")
        dir_ = f"{A}span class=bf>{dir_}</span>"
    else:
        dir_ = (f"{A}form class=bf method=post "
                f"action=/bpo/cobrar>{base}{A}input "
                f"type=hidden name=tid value={tid}>"
                f"{A}select name=tipo>{A}option>PIX</option>"
                f"{A}option>BOLETO</option></select>"
                f"{A}button>Cobrar</button></form>")
    return f"{A}div class=bl>{esq}{dir_}</div>"


def cartao_psp(s, eid, tok=""):
    """Asaas do cliente: chave, aviso e contas a cobrar."""
    c = cobranca.conexao(eid)
    base = (f"{oculto(s)}{A}input type=hidden name=eid "
            f"value={eid}>")
    form = (f"{A}form class=bf method=post action=/bpo/psp "
            f"style='margin-top:10px'>{base}{A}input "
            "type=password name=chave required "
            "maxlength=300 autocomplete=new-password "
            "placeholder='chave da API do Asaas'>"
            f"{A}button>{'Trocar' if c else 'Salvar'} chave"
            "</button></form>")
    if not c:
        corpo = (f"{A}p class=sub>O cliente cria a conta "
                 "Asaas no CNPJ dele e gera a chave da API. "
                 "O dinheiro cai direto na conta dele; o "
                 "portal só cria a cobrança e recebe o "
                 "aviso de pago. Peça uma chave só com "
                 "permissão de cobrança (transferência só "
                 "leitura). Demonstração: chave demo.</p>"
                 + form)
    else:
        demo = c[0] == "demo"
        amb = ("demonstração" if demo else "teste"
               if "_hmlg_" in c[0] else "produção")
        corpo = (f"{A}div class=bl>{A}span>{A}b>Asaas · "
                 f"{amb}</b>{A}span class=sub>chave salva "
                 f"{quando(c[1])}</span></span>{A}span "
                 "class=tag>cifrada</span></div>")
        if tok:
            corpo += (f"{A}p class=msg>Copie agora (não "
                      "aparece de novo). No Asaas: "
                      "Integrações &gt; Webhooks, URL "
                      "https://SEU-DOMINIO/bpo/webhook e "
                      "token:</p>"
                      f"{A}p class=tok>{html.escape(tok)}"
                      "</p>")
        ab = cobranca.abertos(eid)
        corpo += ("".join(linha_cob(s, eid, x, demo)
                          for x in ab)
                  or f"{A}p class=sub>Nada a receber em "
                  "aberto.</p>") + form
    return (f"{A}div class='cd erp'>{A}div class=top>{A}h3>"
            f"Cobrança (Pix e boleto)</h3>{A}span class=sub>"
            f"a receber em aberto</span></div>{corpo}</div>")


@rotas.post("/psp")
def salva_psp(req: Request, t: str = Form(""),
              eid: int = Form(0), chave: str = Form("")):
    s = sessao(req)
    if not ok_csrf(s, t) or not empresa(eid):
        return volta()
    chave = chave.strip()[:300]
    if not chave:
        return tela_empresa(req, eid, "Cole a chave.")
    tok = cobranca.salva(eid, chave)
    log(eid, s, req, "CONECTOU_PSP", "Asaas")
    return tela_empresa(req, eid, ok="Chave salva e "
                        "cifrada.", tok=tok)


@rotas.post("/cobrar")
def cobrar(req: Request, t: str = Form(""),
           eid: int = Form(0), tid: int = Form(0),
           tipo: str = Form("")):
    s = sessao(req)
    if not ok_csrf(s, t) or not empresa(eid):
        return volta()
    try:
        pid = cobranca.gera(eid, tid, tipo)
    except ErroPsp as x:
        return tela_empresa(req, eid, str(x))
    log(eid, s, req, "COBRANCA", f"{tipo} {pid}")
    return tela_empresa(req, eid, ok=f"{tipo} criado no "
                        "Asaas. Aguardando o pagamento.")


@rotas.post("/simula")
def simula(req: Request, t: str = Form(""),
           eid: int = Form(0), pid: str = Form("")):
    s = sessao(req)
    if not ok_csrf(s, t) or not empresa(eid):
        return volta()
    try:
        ok = cobranca.simula(eid, pid[:60])
    except ErroPsp as x:
        return tela_empresa(req, eid, str(x))
    if ok:
        log(eid, s, req, "PAGO_PSP", pid[:60] + " (demo)")
    return tela_empresa(req, eid, ok="Pagamento simulado: "
                        "o painel do cliente já mostra.")


@rotas.post("/webhook")
async def webhook(req: Request):
    """Aviso do Asaas. Sem cookie: quem prova e o token."""
    tok = req.headers.get("asaas-access-token", "")
    if int(req.headers.get("content-length") or 0) > 20000:
        return HTMLResponse("grande demais", 413)
    try:
        corpo = json.loads(await req.body())
    except ValueError:
        return HTMLResponse("json invalido", 400)
    if not isinstance(corpo, dict):
        return HTMLResponse("json invalido", 400)
    eid = cobranca.aviso(tok, corpo)
    if eid:
        pid = str((corpo.get("payment") or {}).get("id"))
        dados.registra(eid, "asaas", req.client.host,
                       "PAGO_PSP", pid[:60])
    return HTMLResponse("ok")


def quando(t):
    return t.astimezone().strftime("%d/%m %H:%M") if t \
        else "nunca"


def cartao_erp(s, eid):
    """Chave do ERP (so a app_key aparece) e sincronizar."""
    e = html.escape
    c = erp.conexao(eid)
    if c:
        k, _, sync, st = c
        ruim = st.startswith("erro")
        tag = ("tag av'>com erro" if ruim
               else "tag'>" + e(st))
        info = (f"{A}div class=bl>{A}span>{A}b>Omie · "
                f"{e(k[:4])}…</b>{A}span class=sub>última "
                f"sincronização: {quando(sync)}</span>"
                f"</span>{A}span class='{tag}</span></div>")
        if ruim:
            info += (f"{A}p class=msg>Não sincronizou: "
                     f"{e(st[6:])}. Os dados antigos foram "
                     "mantidos.</p>")
        info += (f"{A}form class=bf method=post "
                 f"action=/bpo/sync>{oculto(s)}{A}input "
                 f"type=hidden name=eid value={eid}>"
                 f"{A}button>Sincronizar agora</button>"
                 "</form>")
    else:
        info = (f"{A}p class=sub>Ainda não ligado. Cole a "
                "app_key e o app_secret do Omie do cliente "
                "(Omie &gt; Configurações &gt; API).</p>")
    form = (f"{A}form class=bf method=post action=/bpo/erp "
            f"style='margin-top:10px'>{oculto(s)}{A}input "
            f"type=hidden name=eid value={eid}>{A}input "
            "name=key required maxlength=100 "
            "autocomplete=off placeholder=app_key>"
            f"{A}input type=password name=secret required "
            "maxlength=200 autocomplete=new-password "
            "placeholder=app_secret>"
            f"{A}button>{'Trocar' if c else 'Salvar'} chave"
            "</button></form>"
            f"{A}p class=sub style='margin:6px 0 0'>O "
            "segredo é guardado cifrado e nunca volta para "
            "a tela. Demonstração: app_key demo e segredo "
            "omie_padaria.json.</p>")
    return (f"{A}div class='cd erp'>{A}div class=top>{A}h3>"
            f"ERP do cliente</h3>{A}span class=sub>só leitura"
            f"</span></div>{info}{form}</div>")


@rotas.post("/erp")
def salva_erp(req: Request, t: str = Form(""),
              eid: int = Form(0), key: str = Form(""),
              secret: str = Form("")):
    s = sessao(req)
    if not ok_csrf(s, t) or not empresa(eid):
        return volta()
    key, secret = key.strip()[:100], secret.strip()[:200]
    if not key or not secret:
        return tela_empresa(req, eid, "Preencha app_key "
                            "e app_secret.")
    erp.salva(eid, key, secret)
    log(eid, s, req, "CONECTOU_ERP", f"Omie ({key[:4]}…)")
    return tela_empresa(req, eid, ok="Chave salva e "
                        "cifrada. Agora é só sincronizar.")


@rotas.post("/sync")
def sincroniza(req: Request, t: str = Form(""),
               eid: int = Form(0)):
    s = sessao(req)
    if not ok_csrf(s, t) or not empresa(eid):
        return volta()
    try:
        n = erp.sincroniza(eid)
    except ErroErp as x:
        log(eid, s, req, "SYNC_FALHA", str(x))
        return tela_empresa(req, eid)  # erro vai no cartao
    log(eid, s, req, "SINCRONIZOU", f"{n} títulos")
    return tela_empresa(req, eid, ok=f"Sincronizado: {n} "
                        "títulos do ERP.")


def db(sql, args=()):
    with psycopg.connect("dbname=portal") as c:
        return c.execute(sql, args).fetchall()


def confere(senha, guardado):
    it, sal, x = guardado.split("$")
    y = hashlib.pbkdf2_hmac("sha256", senha.encode(),
                            bytes.fromhex(sal), int(it))
    return hmac.compare_digest(y.hex(), x)


def hash_senha(s):
    sal = secrets.token_bytes(16)
    h = hashlib.pbkdf2_hmac("sha256", s.encode(), sal,
                            300_000)
    return f"300000${sal.hex()}${h.hex()}"


def resp(corpo, cod=200):
    return HTMLResponse(pagina("Portal Financeiro · BPO",
                               corpo), cod)


def cookie(r, nome, valor, idade):
    r.set_cookie(nome, valor, max_age=idade, path="/bpo",
                 secure=True, httponly=True,
                 samesite="strict")


def sessao(req):
    t = req.cookies.get("bid", "")
    s = sessoes.get(t)
    if s and s[1] > time.time():
        return s
    sessoes.pop(t, None)
    return None


def ok_csrf(s, tok):
    return s and hmac.compare_digest(s[2], tok)


def log(eid, s, req, acao, det=""):
    dados.registra(eid, "bpo:" + s[0], req.client.host,
                   acao, det[:200])


def falhou(ip, email, acao, form, msg):
    n, t0 = erros.get(ip, (0, time.time()))
    erros[ip] = (n + 1, t0)
    dados.registra(None, "bpo:" + email, ip, acao)
    print(time.strftime("%H:%M:%S"), ip, "BPO", acao, n + 1)
    return resp(tela(msg, form), 401)


def volta(url="/bpo"):
    return RedirectResponse(url, 303)


def casca(titulo, corpo):
    return (f"{A}style>{CSS}{CSS_B}</style>"
            f"{A}div class=emp>{titulo}</div>"
            f"{A}div class=sub style='margin-bottom:10px'>"
            "Área do BPO · todas as empresas</div>" + corpo
            + f"{A}div class=rod>{A}span></span>{A}span>"
            f"{A}a class=tg href=/bpo>Empresas</a>"
            f"{A}a class=tg href=/bpo/sair>Sair</a>"
            "</span></div>")


def oculto(s):
    return f"{A}input type=hidden name=t value='{s[2]}'>"


@rotas.get("")
def inicio(req: Request):
    s = sessao(req)
    if not s:
        return resp(tela("", FORM))
    lin = []
    for eid, nome, us, ts, sg in db(
            "SELECT * FROM bpo_empresas()"):
        tag = (f"{A}span class='tag av'>&#9888; {sg} sem "
               "grupo</span>" if sg else
               f"{A}span class=tag>DRE ok</span>" if ts
               else f"{A}span class=tag>sem ERP</span>")
        lin.append(
            f"{A}div class=bl>{A}span>{A}b>"
            f"{html.escape(nome)}</b>{A}span class=sub>"
            f"{us} login(s) · {ts} títulos</span></span>"
            f"{A}span class=bf>{tag}{A}a class=bt "
            f"href=/bpo/e/{eid}>Abrir</a></span></div>")
    nova = (f"{A}form class=bf method=post "
            f"action=/bpo/empresa>{oculto(s)}"
            f"{A}input name=nome required minlength=2 "
            "maxlength=80 placeholder='Nome da empresa'>"
            f"{A}button>Criar</button></form>")
    return resp(casca(
        "Clientes do BPO",
        f"{A}div class=cd>{A}div class=top>{A}h3>Empresas"
        f"</h3>{A}span class=sub>{len(lin)} no portal"
        "</span></div>" + "".join(lin) + "</div>"
        f"{A}div class=cd>{A}h3>Nova empresa</h3>{nova}"
        "</div>"))


@rotas.post("/login")
def entrar(req: Request, email: str = Form(""),
           senha: str = Form("")):
    ip = req.client.host
    if bloqueado(ip):
        return resp(tela("Muitas tentativas. Aguarde "
                         "5 min.", False), 429)
    email = email.strip().lower()[:200]
    u = db("SELECT * FROM bpo_login(%s)", (email,))
    u = u[0] if u else None
    if not confere(senha, u[1] if u else FALSO) or not u:
        return falhou(ip, email, "BPO_FALHA", FORM,
                      "Email ou senha incorretos.")
    t = secrets.token_urlsafe(32)
    meio[t] = [email, u[2], time.time() + 300, 0]
    r = resp(tela("", FORM2))
    cookie(r, "bpre", t, 300)
    return r


@rotas.post("/codigo")
def codigo(req: Request, codigo: str = Form("")):
    ip = req.client.host
    t = req.cookies.get("bpre", "")
    m = meio.get(t)
    if bloqueado(ip) or not m or m[2] < time.time() \
            or m[3] >= 5:
        meio.pop(t, None)
        return resp(tela("Tempo esgotado ou muitas "
                         "tentativas. Entre de novo.",
                         False), 429)
    p = dois.confere(m[1], codigo, usado.get(m[0], 0))
    if not p:
        m[3] += 1
        return falhou(ip, m[0], "BPO_CODIGO_FALHA", FORM2,
                      "Código errado ou já usado.")
    usado[m[0]] = p
    meio.pop(t, None)
    erros.pop(ip, None)
    tk = secrets.token_urlsafe(32)
    sessoes[tk] = (m[0], time.time() + SESSAO_S,
                   secrets.token_urlsafe(24))
    dados.registra(None, "bpo:" + m[0], ip, "BPO_ENTROU")
    print(time.strftime("%H:%M:%S"), ip, "BPO OK", m[0])
    r = volta()
    cookie(r, "bid", tk, SESSAO_S)
    r.delete_cookie("bpre", path="/bpo")
    return r


@rotas.get("/sair")
def sair(req: Request):
    sessoes.pop(req.cookies.get("bid", ""), None)
    r = volta()
    r.delete_cookie("bid", path="/bpo")
    return r


def empresa(eid):
    for e in db("SELECT id, nome FROM bpo_empresas()"):
        if e[0] == eid:
            return e[1]
    return None


def pendentes(cats):
    """Sem grupo no topo; as ja feitas ficam recolhidas."""
    nc = "".join(h for sem, h in cats if sem)
    ok = [h for sem, h in cats if not sem]
    if not ok:
        return nc
    return (nc + f"{A}details class=dg>{A}summary>"
            f"{A}span>Já classificadas ({len(ok)})</span>"
            f"{A}span>ver</span></summary>" + "".join(ok)
            + "</details>")


@rotas.get("/e/{eid}")
def ver(req: Request, eid: int):
    return tela_empresa(req, eid)


def tela_empresa(req, eid, msg="", ok="", tok=""):
    s = sessao(req)
    nome = empresa(eid) if s else None
    if not nome:
        return volta()
    e = html.escape
    cats = []  # (sem grupo?, html)
    for cod, cn, g, n in db(
            "SELECT * FROM bpo_categorias(%s)", (eid,)):
        op = "".join(
            f"{A}option{' selected' if k == g else ''}>"
            f"{k}</option>" for k in ORDEM)
        if not g:
            op = (f"{A}option value='' selected disabled>"
                  "escolher grupo</option>" + op)
        cats.append((not g,
            f"{A}div class='bl{' nc' if not g else ''}'>"
            f"{A}span>{A}b>{e(cn)}</b>{A}span class=sub>"
            f"{e(cod)} · {n} títulos"
            f"{' · sem grupo' if not g else ''}</span>"
            f"</span>{A}form class=bf method=post "
            f"action=/bpo/classifica>{oculto(s)}"
            f"{A}input type=hidden name=eid value={eid}>"
            f"{A}input type=hidden name=cod "
            f"value='{e(cod)}'>{A}select name=grupo "
            f"required>{op}</select>{A}button>Salvar"
            "</button></form></div>"))
    us = "".join(
        f"{A}div class=bl>{A}span>{e(em)}</span>"
        f"{A}span class='tag{'' if f2 else ' av'}'>"
        f"{'com 2FA' if f2 else 'sem 2FA'}</span></div>"
        for em, f2 in db("SELECT * FROM bpo_usuarios(%s)",
                         (eid,)))
    novo = (f"{A}form class=bf method=post "
            f"action=/bpo/usuario>{oculto(s)}"
            f"{A}input type=hidden name=eid value={eid}>"
            f"{A}input type=email name=email required "
            "placeholder='email do cliente'>"
            f"{A}input type=password name=senha required "
            "minlength=10 autocomplete=new-password "
            "placeholder='senha inicial (10+)'>"
            f"{A}button>Criar login</button></form>")
    aviso = (f"{A}p class=msg>{e(msg)}</p>" if msg else "")
    aviso += (f"{A}p class=okm>{e(ok)}</p>" if ok else "")
    return resp(casca(
        e(nome), aviso + cartao_erp(s, eid) +
        cartao_psp(s, eid, tok) +
        f"{A}div class=cd>{A}div class=top>{A}h3>"
        f"Categorias do ERP → DRE</h3>{A}span class=sub>"
        "uma vez por cliente</span></div>"
        + (pendentes(cats) or f"{A}p class=sub>Nenhuma "
           "categoria ainda (falta ligar o ERP).</p>")
        + f"</div>{A}div class=cd>{A}div class=top>"
        f"{A}h3>Logins</h3>{A}span class=sub>só veem "
        "esta empresa</span></div>" + us
        + f"{A}div style='margin-top:10px'>{novo}</div>"
        "</div>"))


@rotas.post("/classifica")
def classifica(req: Request, t: str = Form(""),
               eid: int = Form(0), cod: str = Form(""),
               grupo: str = Form("")):
    s = sessao(req)
    if not ok_csrf(s, t) or grupo not in ORDEM:
        return volta()
    nomes = {c[0]: c[1] for c in db(
        "SELECT * FROM bpo_categorias(%s)", (eid,))}
    n = db("SELECT bpo_classifica(%s, %s, %s)",
           (eid, cod, grupo))[0][0]
    if n:
        log(eid, s, req, "CLASSIFICOU",
            f"{nomes.get(cod, cod)} → {grupo}")
    return volta(f"/bpo/e/{eid}")


@rotas.post("/empresa")
def nova(req: Request, t: str = Form(""),
         nome: str = Form("")):
    s = sessao(req)
    nome = " ".join(nome.split())[:80]
    if not ok_csrf(s, t) or len(nome) < 2:
        return volta()
    eid = db("SELECT bpo_nova_empresa(%s)", (nome,))[0][0]
    log(eid, s, req, "CRIOU_EMPRESA", nome)
    return volta(f"/bpo/e/{eid}")


@rotas.post("/usuario")
def usuario(req: Request, t: str = Form(""),
            eid: int = Form(0), email: str = Form(""),
            senha: str = Form("")):
    s = sessao(req)
    if not ok_csrf(s, t) or not empresa(eid):
        return volta()
    email = email.strip().lower()[:200]
    if "@" not in email or len(senha) < 10:
        return tela_empresa(req, eid, "Email inválido ou "
                            "senha com menos de 10 letras.")
    try:
        db("SELECT bpo_novo_usuario(%s, %s, %s)",
           (eid, email, hash_senha(senha)))
    except psycopg.errors.UniqueViolation:
        return tela_empresa(req, eid,
                            "Esse email já tem login.")
    log(eid, s, req, "CRIOU_LOGIN", email)
    return volta(f"/bpo/e/{eid}")
