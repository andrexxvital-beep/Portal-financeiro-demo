-- Etapa C1: banco multiempresa com Row Level Security.
-- Cada empresa so enxerga as proprias linhas: o filtro
-- fica no banco, nao depende do codigo lembrar do WHERE.
CREATE TABLE empresa (
  id int PRIMARY KEY,
  nome text NOT NULL);
CREATE TABLE usuario (
  id serial PRIMARY KEY,
  empresa_id int NOT NULL REFERENCES empresa,
  email text UNIQUE NOT NULL,
  senha text NOT NULL,  -- pbkdf2: iter$sal$hash
  totp text);           -- segredo do 2FA (etapa C3)
CREATE TABLE categoria (
  empresa_id int NOT NULL REFERENCES empresa,
  codigo text NOT NULL,
  nome text NOT NULL,
  grupo text,           -- grupo da DRE; vazio = nao class.
  PRIMARY KEY (empresa_id, codigo));
CREATE TABLE titulo (
  empresa_id int NOT NULL REFERENCES empresa,
  id bigint NOT NULL,
  natureza char(1) NOT NULL CHECK (natureza IN ('R','P')),
  categoria text NOT NULL,
  depto text NOT NULL,
  vencimento date NOT NULL,
  pagamento date,
  valor bigint NOT NULL,  -- centavos
  PRIMARY KEY (empresa_id, id));
CREATE TABLE auditoria (
  id bigserial PRIMARY KEY,
  quando timestamptz NOT NULL DEFAULT now(),
  empresa_id int,
  usuario text,
  ip text,
  acao text NOT NULL,
  detalhe text);

-- A empresa da vez vem de app.empresa (setada pelo app a
-- cada transacao). Sem ela, a conta da zero linhas.
CREATE FUNCTION empresa_atual() RETURNS int
  LANGUAGE sql STABLE AS
  $$ SELECT NULLIF(current_setting('app.empresa', true),
                   '')::int $$;

ALTER TABLE empresa ENABLE ROW LEVEL SECURITY;
ALTER TABLE categoria ENABLE ROW LEVEL SECURITY;
ALTER TABLE titulo ENABLE ROW LEVEL SECURITY;
ALTER TABLE auditoria ENABLE ROW LEVEL SECURITY;
CREATE POLICY so_minha ON empresa
  USING (id = empresa_atual());
CREATE POLICY so_minha ON categoria
  USING (empresa_id = empresa_atual());
CREATE POLICY so_minha ON titulo
  USING (empresa_id = empresa_atual());
CREATE POLICY so_minha ON auditoria
  USING (empresa_id = empresa_atual())
  WITH CHECK (empresa_id IS NULL
              OR empresa_id = empresa_atual());

-- Login: o app nao le a tabela usuario; so chama esta
-- funcao, que devolve o hash de 1 email.
CREATE FUNCTION login_busca(e text)
  RETURNS TABLE (id int, empresa_id int, senha text,
                 totp text)
  LANGUAGE sql STABLE SECURITY DEFINER
  SET search_path = public AS
  $$ SELECT id, empresa_id, senha, totp FROM usuario
     WHERE email = lower(e) $$;
REVOKE ALL ON FUNCTION login_busca(text) FROM PUBLIC;

-- O app entra com o usuario do Linux (pl), sem senha no
-- codigo, e so pode ler; auditoria so aceita insert.
GRANT SELECT ON empresa, categoria, titulo TO pl;
GRANT INSERT ON auditoria TO pl;
GRANT USAGE ON SEQUENCE auditoria_id_seq TO pl;
GRANT EXECUTE ON FUNCTION login_busca(text) TO pl;
