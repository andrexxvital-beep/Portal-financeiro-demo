-- Etapa G1: cobranca (Pix/boleto) na conta Asaas do
-- CLIENTE. O dinheiro vai do pagador direto para a conta
-- dele; o portal so guarda o pedido e o aviso de pago.
-- A chave do Asaas entra cifrada (cofre.py) e do token
-- do aviso (webhook) so fica o hash.
CREATE TABLE psp_conexao (
  empresa_id int PRIMARY KEY REFERENCES empresa,
  psp text NOT NULL DEFAULT 'asaas',
  chave bytea NOT NULL,        -- chave da API, cifrada
  token text NOT NULL UNIQUE,  -- sha256 do token
  atualizado timestamptz NOT NULL DEFAULT now());
REVOKE ALL ON psp_conexao FROM PUBLIC;

CREATE TABLE cobranca (
  empresa_id int NOT NULL REFERENCES empresa,
  titulo_id bigint NOT NULL,
  psp_id text NOT NULL UNIQUE, -- id da cobranca no Asaas
  tipo text NOT NULL CHECK (tipo IN ('PIX','BOLETO')),
  valor bigint NOT NULL,       -- centavos
  link text,                   -- pagina de pagamento
  status text NOT NULL DEFAULT 'pendente'
    CHECK (status IN ('pendente','paga','cancelada')),
  criada timestamptz NOT NULL DEFAULT now(),
  paga_em date,
  PRIMARY KEY (empresa_id, titulo_id));
ALTER TABLE cobranca ENABLE ROW LEVEL SECURITY;
CREATE POLICY so_minha ON cobranca
  USING (empresa_id = empresa_atual());
GRANT SELECT ON cobranca TO pl;

CREATE FUNCTION bpo_salva_psp(eid int, k bytea, tk text)
  RETURNS void LANGUAGE sql SECURITY DEFINER
  SET search_path = public AS $$
  INSERT INTO psp_conexao (empresa_id, chave, token)
    VALUES (eid, k, tk)
  ON CONFLICT (empresa_id) DO UPDATE
    SET chave = k, token = tk, atualizado = now() $$;

CREATE FUNCTION bpo_psp(eid int)
  RETURNS TABLE (chave bytea, atualizado timestamptz,
                 token text)
  LANGUAGE sql STABLE SECURITY DEFINER
  SET search_path = public AS
  $$ SELECT chave, atualizado, token FROM psp_conexao
     WHERE empresa_id = eid $$;

-- Contas a receber em aberto (as mais atrasadas primeiro)
-- e a cobranca de cada uma, se ja existir.
CREATE FUNCTION bpo_abertos(eid int, n int)
  RETURNS TABLE (id bigint, venc date, valor bigint,
                 cat text, psp_id text, status text,
                 link text, paga_em date)
  LANGUAGE sql STABLE SECURITY DEFINER
  SET search_path = public AS $$
  SELECT t.id, t.vencimento, t.valor,
         coalesce(k.nome, t.categoria), c.psp_id,
         c.status, c.link, c.paga_em
  FROM titulo t
  LEFT JOIN categoria k ON k.empresa_id = t.empresa_id
       AND k.codigo = t.categoria
  LEFT JOIN cobranca c ON c.empresa_id = t.empresa_id
       AND c.titulo_id = t.id
  WHERE t.empresa_id = eid AND t.natureza = 'R'
    AND t.pagamento IS NULL
  ORDER BY coalesce(c.status = 'paga', false),
           t.vencimento, t.id
  LIMIT n $$;

-- Grava a cobranca criada no Asaas. So aceita titulo a
-- receber, em aberto e com o mesmo valor do ERP.
CREATE FUNCTION bpo_cobranca(eid int, tid bigint,
    pid text, tp text, v bigint, lk text)
  RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER
  SET search_path = public AS $$
BEGIN
  PERFORM 1 FROM titulo WHERE empresa_id = eid
    AND id = tid AND natureza = 'R'
    AND pagamento IS NULL AND valor = v;
  IF NOT FOUND THEN
    RETURN false;
  END IF;
  INSERT INTO cobranca (empresa_id, titulo_id, psp_id,
                        tipo, valor, link)
    VALUES (eid, tid, pid, tp, v, lk)
  ON CONFLICT (empresa_id, titulo_id) DO UPDATE
    SET psp_id = pid, tipo = tp, valor = v, link = lk,
        status = 'pendente', criada = now(),
        paga_em = NULL
    WHERE cobranca.status = 'cancelada';
  RETURN FOUND;
END $$;

-- Aviso do Asaas (webhook). Quem prova quem e: o token.
-- Devolve a empresa, ou NULL se o token/cobranca nao
-- bate. Repetir o mesmo aviso nao muda nada.
CREATE FUNCTION psp_aviso(tk text, pid text, st text,
                          dia date)
  RETURNS int LANGUAGE sql SECURITY DEFINER
  SET search_path = public AS $$
  UPDATE cobranca c SET status = st,
         paga_em = CASE WHEN st = 'paga' THEN dia END
  FROM psp_conexao p
  WHERE p.token = tk AND c.empresa_id = p.empresa_id
    AND c.psp_id = pid AND c.status <> 'paga'
    AND st IN ('paga', 'cancelada')
  RETURNING c.empresa_id $$;

DO $$
DECLARE f text;
BEGIN
  FOREACH f IN ARRAY ARRAY[
      'bpo_salva_psp(int, bytea, text)', 'bpo_psp(int)',
      'bpo_abertos(int, int)',
      'bpo_cobranca(int, bigint, text, text, bigint, text)',
      'psp_aviso(text, text, text, date)'] LOOP
    EXECUTE 'REVOKE ALL ON FUNCTION ' || f
            || ' FROM PUBLIC';
    EXECUTE 'GRANT EXECUTE ON FUNCTION ' || f || ' TO pl';
  END LOOP;
END $$;
