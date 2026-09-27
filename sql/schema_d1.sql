-- Etapa D1: area do BPO (o apicultor de todas as colmeias).
-- O admin tem tabela propria, 2FA obrigatorio, e so mexe no
-- banco por funcoes estreitas (nada de SQL solto no app).
CREATE TABLE bpo_admin (
  id serial PRIMARY KEY,
  email text UNIQUE NOT NULL,
  senha text NOT NULL,
  totp text NOT NULL);
REVOKE ALL ON bpo_admin FROM PUBLIC;

CREATE FUNCTION bpo_login(e text)
  RETURNS TABLE (id int, senha text, totp text)
  LANGUAGE sql STABLE SECURITY DEFINER
  SET search_path = public AS
  $$ SELECT id, senha, totp FROM bpo_admin
     WHERE email = lower(e) $$;

CREATE FUNCTION bpo_empresas()
  RETURNS TABLE (id int, nome text, usuarios bigint,
                 titulos bigint, sem_grupo bigint)
  LANGUAGE sql STABLE SECURITY DEFINER
  SET search_path = public AS
  $$ SELECT e.id, e.nome,
       (SELECT count(*) FROM usuario u
        WHERE u.empresa_id = e.id),
       (SELECT count(*) FROM titulo t
        WHERE t.empresa_id = e.id),
       (SELECT count(*) FROM categoria c
        WHERE c.empresa_id = e.id AND c.grupo IS NULL)
     FROM empresa e ORDER BY e.id $$;

CREATE FUNCTION bpo_categorias(eid int)
  RETURNS TABLE (codigo text, nome text, grupo text,
                 titulos bigint)
  LANGUAGE sql STABLE SECURITY DEFINER
  SET search_path = public AS
  $$ SELECT c.codigo, c.nome, c.grupo,
       (SELECT count(*) FROM titulo t
        WHERE t.empresa_id = c.empresa_id
          AND t.categoria = c.codigo)
     FROM categoria c WHERE c.empresa_id = eid
     ORDER BY c.grupo NULLS FIRST, c.codigo $$;

CREATE FUNCTION bpo_usuarios(eid int)
  RETURNS TABLE (email text, com_2fa boolean)
  LANGUAGE sql STABLE SECURITY DEFINER
  SET search_path = public AS
  $$ SELECT email, totp IS NOT NULL FROM usuario
     WHERE empresa_id = eid ORDER BY email $$;

CREATE FUNCTION bpo_classifica(eid int, cod text, g text)
  RETURNS int LANGUAGE plpgsql SECURITY DEFINER
  SET search_path = public AS $$
DECLARE n int;
BEGIN
  IF g IS NULL OR g NOT IN ('Receita', 'Custos',
      'Despesas administrativas', 'Despesas financeiras',
      'Retiradas') THEN
    RAISE EXCEPTION 'grupo invalido';
  END IF;
  UPDATE categoria SET grupo = g
   WHERE empresa_id = eid AND codigo = cod;
  GET DIAGNOSTICS n = ROW_COUNT;
  RETURN n;
END $$;

CREATE FUNCTION bpo_nova_empresa(n text)
  RETURNS int LANGUAGE plpgsql SECURITY DEFINER
  SET search_path = public AS $$
DECLARE novo int;
BEGIN
  IF length(trim(n)) NOT BETWEEN 2 AND 80 THEN
    RAISE EXCEPTION 'nome invalido';
  END IF;
  LOCK TABLE empresa IN EXCLUSIVE MODE;
  INSERT INTO empresa (id, nome)
    SELECT coalesce(max(id), 0) + 1, trim(n) FROM empresa
    RETURNING id INTO novo;
  RETURN novo;
END $$;

CREATE FUNCTION bpo_novo_usuario(eid int, e text, s text)
  RETURNS void LANGUAGE sql SECURITY DEFINER
  SET search_path = public AS
  $$ INSERT INTO usuario (empresa_id, email, senha)
     VALUES (eid, lower(trim(e)), s) $$;

DO $$ DECLARE f text; BEGIN
  FOREACH f IN ARRAY ARRAY['bpo_login(text)',
    'bpo_empresas()', 'bpo_categorias(int)',
    'bpo_usuarios(int)', 'bpo_classifica(int,text,text)',
    'bpo_nova_empresa(text)',
    'bpo_novo_usuario(int,text,text)'] LOOP
    EXECUTE 'REVOKE ALL ON FUNCTION ' || f
            || ' FROM PUBLIC';
    EXECUTE 'GRANT EXECUTE ON FUNCTION ' || f || ' TO pl';
  END LOOP;
END $$;

-- Demo: o ERP da Padaria mandou uma categoria nova, ainda
-- sem grupo na DRE. O BPO classifica uma vez e pronto.
INSERT INTO categoria VALUES (2, '2.01.09', 'Embalagens',
                              NULL);
INSERT INTO titulo VALUES
  (2, 900001, 'P', '2.01.09', 'LOJA', '2026-09-10',
   '2026-09-10', 18500),
  (2, 900002, 'P', '2.01.09', 'LOJA', '2026-09-20',
   '2026-09-20', 12300);
