"""Etapa 3j: tela de login no mesmo tema do painel."""
import html

from visual import CLARO, NEON

A = "<"
CSS_L = (f"body{{{CLARO}}}@media(prefers-color-scheme:dark)"
         f"{{body{{{NEON}}}}}"
         "*{box-sizing:border-box}"
         "body{background:var(--bg);color:var(--tx);"
         "max-width:none;margin:0;padding:16px;"
         "min-height:100vh;display:grid;"
         "place-items:center;"
         "font-family:system-ui,sans-serif}"
         ".lg{width:100%;max-width:340px;"
         "background:var(--card);border:1px solid "
         "var(--bd);border-radius:18px;padding:26px 22px;"
         "text-align:center;box-shadow:0 0 28px "
         "var(--glow)}"
         ".ic{width:64px;height:64px;margin:0 auto 10px;"
         "border-radius:18px;display:grid;"
         "place-items:center;background:linear-gradient("
         "135deg,var(--h1),var(--h2))}"
         ".lg h1{margin:0;font-size:1.25em;"
         "background:linear-gradient(90deg,var(--h1),"
         "var(--h2));-webkit-background-clip:text;"
         "background-clip:text;color:transparent}"
         ".sub{color:var(--tx2);font-size:.85em;"
         "margin:4px 0 18px}"
         ".lg input{width:100%;padding:12px 14px;"
         "font-size:1em;border-radius:12px;border:1px "
         "solid var(--bd);background:var(--bg);"
         "color:var(--tx);outline:none}"
         ".lg input:focus{border-color:var(--h2);"
         "box-shadow:0 0 0 3px var(--glow)}"
         ".lg button{width:100%;margin-top:12px;"
         "padding:12px;font-size:1em;font-weight:700;"
         "border:0;border-radius:12px;color:#fff;"
         "background:linear-gradient(90deg,var(--h1),"
         "var(--h2));box-shadow:0 0 16px var(--glow)}"
         ".msg{background:var(--ruimbg);color:var(--ruim);"
         "border-radius:10px;padding:8px;font-size:.88em;"
         "margin:0 0 12px}"
         ".pe{color:var(--tx2);font-size:.75em;"
         "margin-top:18px;line-height:1.5}"
         ".lg a{color:var(--h2)}")

ICONE = (f"{A}svg width=34 height=34 viewBox='0 0 34 34'>"
         f"{A}rect x=4 y=18 width=6 height=12 rx=2 "
         "fill='#fff' opacity=.7 />"
         f"{A}rect x=14 y=11 width=6 height=19 rx=2 "
         "fill='#fff' opacity=.85 />"
         f"{A}rect x=24 y=4 width=6 height=26 rx=2 "
         "fill='#fff' /></svg>")

FORM = (f"{A}form method=post action=/login>"
        f"{A}input type=password name=senha autofocus "
        "required autocomplete=current-password "
        "placeholder='Digite sua senha'>"
        f"{A}button>Entrar no painel</button></form>")


def tela(msg="", form=True):
    m = ""
    if msg:
        m = f"{A}p class=msg>⚠ {html.escape(msg)}</p>"
    meio = FORM if form is True else form or (
        f"{A}p>{A}a href=/>Tentar de novo</a></p>")
    return (f"{A}style>{CSS_L}</style>"
            f"{A}div class=lg>{A}div class=ic>{ICONE}"
            f"</div>{A}h1>Portal Financeiro</h1>"
            f"{A}p class=sub>Receitas, despesas e "
            f"contas num só lugar</p>{m}{meio}"
            f"{A}p class=pe>🔒 Acesso protegido · "
            f"só rede local{A}br>Sessão expira em "
            f"30 min</p></div>")
