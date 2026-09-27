# Portal Financeiro Multiempresa (demonstração)

Portal web para um **BPO financeiro**: cada cliente entra
com login próprio e vê só os números da própria empresa
(substitui planilhas e Power BI). O BPO administra todas
as empresas numa área separada.

> Todos os dados deste repositório são **fictícios**.

## O que tem

**Painel do dono (cliente)**
- Saldo, resultado e margem operacional, caixa projetado
  e inadimplência
- DRE com detalhe (grupo > categoria > lançamento), DFC
  e previsto x realizado
- Filtros: período, centro de custo e categoria;
  comparação com o período anterior e o mesmo do ano
  passado
- Pontos de atenção automáticos; exportar CSV e PDF
- Tema claro/escuro automático, feito para celular

**Área do BPO** (`/bpo`)
- Empresas e logins de clientes
- Liga cada categoria do ERP a um grupo da DRE
- ERP Omie: chave cifrada, sincronização com status
- Cobrança Pix/boleto pelo Asaas **da conta do cliente**
  (o dinheiro nunca passa pelo portal); o aviso de pago
  (webhook) dá baixa e a inadimplência atualiza

## Segurança
- PostgreSQL com **Row Level Security**: o isolamento
  entre empresas é feito pelo banco, não pelo código
- O app só lê; escrita apenas por funções estreitas
  (SECURITY DEFINER)
- Senhas PBKDF2, **2FA (TOTP)**, bloqueio por tentativas,
  sessão de 30 min, anti-CSRF, CSP sem JavaScript
- Chaves de ERP/PSP cifradas (Fernet); a chave do cofre
  fica fora do banco; token do webhook guardado só como
  hash
- HTTPS e log de acessos por empresa

## Como rodar (Ubuntu)

    sudo apt install postgresql python3-venv openssl
    python3 -m venv .venv
    .venv/bin/pip install -r requirements.txt
    sudo -u postgres createuser $USER
    sudo -u postgres createdb portal
    sudo -u postgres psql -d portal < sql/schema.sql
    for t in empresa categoria titulo; do
      sudo -u postgres psql -d portal \
        -c "\copy $t from stdin csv" < carga_$t.csv
    done
    for f in d1 f1 g1; do
      sudo -u postgres psql -d portal < sql/schema_$f.sql
    done
    .venv/bin/python cofre.py nova-chave
    IP=$(hostname -I | cut -d' ' -f1)
    openssl req -x509 -newkey rsa:2048 -nodes -days 365 \
      -keyout chave.pem -out cert.pem -subj "/CN=$IP" \
      -addext "subjectAltName=IP:$IP"
    .venv/bin/python criar_admin.py
    .venv/bin/python criar_usuario.py
    .venv/bin/python portal.py

Os `.sql` dão permissão ao usuário `pl`; troque pelo seu
usuário do Linux se for outro.

Demonstração sem contas externas: no BPO, ERP com
app_key `demo` e segredo `omie_padaria.json`; Asaas com
a chave `demo` e o botão "Simular pago".

## Limites conhecidos
- Asaas real ainda precisa do cadastro do cliente de
  cada título (nome e CNPJ vindos do ERP)
- O portal só atende a rede local; para o aviso do
  Asaas chegar, precisa de um endereço HTTPS público

Stack: Python (FastAPI), PostgreSQL, HTML/CSS sem
JavaScript.
