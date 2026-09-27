"""Etapa 4d: painel com senha, filtro e CSV.

Uso: python3 painel.py [IP_da_rede_local]
"""
import hashlib
import hmac
import html
import ipaddress
import json
import secrets
import socket
import sys
import time
from http.server import BaseHTTPRequestHandler
from http.server import ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit
from visual import render, exportar
from relatorio import relatorio
from login import tela

PORTA = 8788
RESUMO = "resumo.json"
SENHA = "senha.json"
SESSAO_S = 30 * 60
MAX_ERROS = 5
BLOQUEIO_S = 5 * 60

sessoes = {}   # token -> expira_em
erros = {}     # ip -> [qtd, desde]


def ip_local():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


def confere(senha):
    with open(SENHA) as f:
        d = json.load(f)
    h = hashlib.pbkdf2_hmac("sha256", senha.encode(),
                            bytes.fromhex(d["sal"]),
                            d["iter"])
    return hmac.compare_digest(h.hex(), d["hash"])


def bloqueado(ip):
    q, t = erros.get(ip, (0, 0))
    if q >= MAX_ERROS and time.time() - t < BLOQUEIO_S:
        return True
    if time.time() - t >= BLOQUEIO_S:
        erros.pop(ip, None)
    return False


def tabela(v):
    e = html.escape
    if isinstance(v, dict):
        linhas = "".join(
            f"<tr><th>{e(str(k))}</th>"
            f"<td>{tabela(x)}</td></tr>"
            for k, x in v.items())
        return f"<table>{linhas}</table>"
    if isinstance(v, list):
        itens = "".join(f"<li>{tabela(x)}</li>" for x in v)
        return f"<ul>{itens}</ul>"
    return e(str(v))


CSS = ("body{font-family:sans-serif;max-width:720px;"
       "margin:auto;padding:12px}table{border-collapse:"
       "collapse;width:100%}th,td{border:1px solid #ccc;"
       "padding:4px;text-align:left;vertical-align:top}"
       "th{background:#f3f3f3}")


def pagina(titulo, corpo):
    a = "<"  # tags montadas assim p/ colar no chat
    return (f"{a}!doctype html>{a}html lang=pt-BR "
            f"translate=no>{a}head>"
            f"{a}meta charset=utf-8>"
            f"{a}meta name=google content=notranslate>"
            f"{a}meta name=viewport "
            f"content='width=device-width'>"
            f"{a}title>{titulo}</title>"
            f"{a}style>{CSS}</style></head>"
            f"{a}body>{corpo}</body></html>")


A = "<"
LOGIN = (f"{A}h2>Portal Financeiro</h2>"
         f"{A}form method=post action=/login>"
         f"{A}input type=password name=senha "
         f"autofocus placeholder=Senha> "
         f"{A}button>Entrar</button></form>")


class H(BaseHTTPRequestHandler):
    server_version = "Painel"
    sys_version = ""

    def enviar(self, cod, corpo, extra=None):
        b = corpo.encode()
        self.send_response(cod)
        self.send_header("Content-Type",
                         "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("X-Content-Type-Options",
                         "nosniff")
        self.send_header("Content-Security-Policy",
                         "default-src 'none'; "
                         "style-src 'unsafe-inline'; "
                         "form-action 'self'")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(b)

    def ir(self, destino, extra=None):
        self.send_response(303)
        self.send_header("Location", destino)
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def rede_ok(self):
        ip = ipaddress.ip_address(self.client_address[0])
        if ip.is_private or ip.is_loopback:
            return True
        self.enviar(403, "proibido")
        return False

    def token(self):
        for p in self.headers.get("Cookie", "").split(";"):
            k, _, v = p.strip().partition("=")
            if k == "sid" and v in sessoes:
                if sessoes[v] > time.time():
                    return v
                sessoes.pop(v, None)
        return None

    def do_GET(self):
        if not self.rede_ok():
            return
        u = urlsplit(self.path)
        p = parse_qs(u.query).get("p", [None])[0]
        if u.path == "/logout":
            sessoes.pop(self.token(), None)
            return self.ir("/", {"Set-Cookie":
                           "sid=; Max-Age=0; Path=/"})
        if not self.token():
            return self.enviar(200, pagina("Login", tela()))
        if u.path == "/exportar.csv":
            return self.csv(p)
        if u.path == "/relatorio.pdf":
            return self.pdf(p)
        try:
            with open(RESUMO, encoding="utf-8") as f:
                dados = json.load(f)
            corpo = render(dados, p)
        except (OSError, ValueError, KeyError,
                TypeError) as e:
            corpo = "<p>Erro lendo resumo.json: " + \
                html.escape(str(e)) + "</p>"
        self.enviar(200, pagina("Resumo",
                    corpo))

    def csv(self, p):
        try:
            with open(RESUMO, encoding="utf-8") as f:
                nome, txt = exportar(json.load(f), p)
        except (OSError, ValueError, KeyError) as e:
            return self.enviar(500, html.escape(str(e)))
        b = txt.encode("utf-8-sig")
        print(time.strftime("%H:%M:%S"),
              self.client_address[0], "EXPORTOU", nome)
        self.send_response(200)
        self.send_header("Content-Type",
                         "text/csv; charset=utf-8")
        self.send_header("Content-Disposition",
                         f'attachment; filename="{nome}"')
        self.send_header("Content-Length", str(len(b)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options",
                         "nosniff")
        self.end_headers()
        self.wfile.write(b)

    def pdf(self, p):
        try:
            with open(RESUMO, encoding="utf-8") as f:
                nome, b = relatorio(json.load(f), p)
        except (OSError, ValueError, KeyError) as e:
            return self.enviar(500, html.escape(str(e)))
        print(time.strftime("%H:%M:%S"),
              self.client_address[0], "EXPORTOU", nome)
        self.send_response(200)
        self.send_header("Content-Type", "application/pdf")
        self.send_header("Content-Disposition",
                         f'attachment; filename="{nome}"')
        self.send_header("Content-Length", str(len(b)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options",
                         "nosniff")
        self.end_headers()
        self.wfile.write(b)

    def do_POST(self):
        if not self.rede_ok():
            return
        ip = self.client_address[0]
        if self.path != "/login":
            return self.enviar(404, "nao encontrado")
        if bloqueado(ip):
            return self.enviar(429, pagina("Bloqueado",
                               tela("Muitas tentativas. "
                               "Aguarde 5 min.", False)))
        n = min(int(self.headers.get("Content-Length", 0)),
                1024)
        campos = parse_qs(self.rfile.read(n).decode())
        senha = campos.get("senha", [""])[0]
        if confere(senha):
            erros.pop(ip, None)
            t = secrets.token_urlsafe(32)
            sessoes[t] = time.time() + SESSAO_S
            ck = (f"sid={t}; HttpOnly; SameSite=Strict; "
                  f"Path=/; Max-Age={SESSAO_S}")
            print(time.strftime("%H:%M:%S"), ip, "LOGIN OK")
            return self.ir("/", {"Set-Cookie": ck})
        q, t0 = erros.get(ip, (0, time.time()))
        erros[ip] = (q + 1, t0)
        print(time.strftime("%H:%M:%S"), ip,
              "SENHA ERRADA", q + 1)
        self.enviar(401, pagina("Login",
                    tela("Senha incorreta.")))

    def log_message(self, fmt, *a):
        pass


if __name__ == "__main__":
    host = sys.argv[1] if len(sys.argv) > 1 else ip_local()
    if not ipaddress.ip_address(host).is_private:
        raise SystemExit("ERRO: IP nao e de rede local")
    srv = ThreadingHTTPServer((host, PORTA), H)
    print(f"Painel em http://{host}:{PORTA}  (Ctrl+C sai)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nencerrado")
