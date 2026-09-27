-- Etapa F1: conexao de cada empresa com o ERP (Omie).
-- O app_secret so entra cifrado (cofre.py); a chave do
-- cofre fica fora do banco. O app nao le a tabela: usa
-- funcoes estreitas, como na area do BPO (D1).
CREATE TABLE erp_conexao (
  empresa_id int PRIMARY KEY REFERENCES empresa,
  erp text NOT NULL DEFAULT 'omie',
  app_key text NOT NULL,
  segredo bytea NOT NULL,      -- app_secret cifrado
  atualizado timestamptz NOT NULL DEFAULT now(),
  ultima_sync timestamptz,
  status text NOT NULL DEFAULT 'salvo');
REVOKE ALL ON erp_conexao FROM PUBLIC;

CREATE FUNCTION bpo_salva_erp(eid int, k text, s bytea)
  RETURNS void LANGUAGE plpgsql SECURITY DEFINER
  SET search_path = public AS $$
BEGIN
  IF length(k) NOT BETWEEN 1 AND 100 THEN
    RAISE EXCEPTION 'app_key invalida';
  END IF;
  INSERT INTO erp_conexao (empresa_id, app_key, segredo)
    VALUES (eid, k, s)
  ON CONFLICT (empresa_id) DO UPDATE
    SET app_key = k, segredo = s, atualizado = now(),
        status = 'salvo';
END $$;

CREATE FUNCTION bpo_erp(eid int)
  RETURNS TABLE (app_key text, segredo bytea,
                 ultima_sync timestamptz, status text)
  LANGUAGE sql STABLE SECURITY DEFINER
  SET search_path = public AS
  $$ SELECT app_key, segredo, ultima_sync, status
     FROM erp_conexao WHERE empresa_id = eid $$;

CREATE FUNCTION bpo_erp_status(eid int, st text)
  RETURNS void LANGUAGE sql SECURITY DEFINER
  SET search_path = public AS
  $$ UPDATE erp_conexao SET status = left(st, 200)
     WHERE empresa_id = eid $$;

-- Troca os titulos da empresa pelos que vieram do ERP,
-- tudo numa transacao: ou entra tudo, ou nada muda.
-- Categoria nova entra sem grupo (o BPO classifica).
CREATE FUNCTION bpo_carga(eid int, cats jsonb, tits jsonb)
  RETURNS int LANGUAGE plpgsql SECURITY DEFINER
  SET search_path = public AS $$
DECLARE n int;
BEGIN
  INSERT INTO categoria (empresa_id, codigo, nome)
    SELECT eid, c->>'codigo', c->>'nome'
    FROM jsonb_array_elements(cats) c
  ON CONFLICT (empresa_id, codigo) DO UPDATE
    SET nome = EXCLUDED.nome;
  DELETE FROM titulo WHERE empresa_id = eid;
  INSERT INTO titulo
    SELECT eid, (t->>'id')::bigint, t->>'nat',
           t->>'cat', t->>'depto', (t->>'venc')::date,
           (t->>'pag')::date, (t->>'valor')::bigint
    FROM jsonb_array_elements(tits) t;
  GET DIAGNOSTICS n = ROW_COUNT;
  UPDATE erp_conexao SET ultima_sync = now(),
         status = 'ok'
   WHERE empresa_id = eid;
  RETURN n;
END $$;

-- O painel do cliente so ve quando foi a ultima carga.
CREATE FUNCTION erp_ultima_sync() RETURNS timestamptz
  LANGUAGE sql STABLE SECURITY DEFINER
  SET search_path = public AS
  $$ SELECT ultima_sync FROM erp_conexao
     WHERE empresa_id = empresa_atual() $$;

DO $$
DECLARE f text;
BEGIN
  FOREACH f IN ARRAY ARRAY[
      'bpo_salva_erp(int, text, bytea)', 'bpo_erp(int)',
      'bpo_erp_status(int, text)',
      'bpo_carga(int, jsonb, jsonb)',
      'erp_ultima_sync()'] LOOP
    EXECUTE 'REVOKE ALL ON FUNCTION ' || f
            || ' FROM PUBLIC';
    EXECUTE 'GRANT EXECUTE ON FUNCTION ' || f || ' TO pl';
  END LOOP;
END $$;
