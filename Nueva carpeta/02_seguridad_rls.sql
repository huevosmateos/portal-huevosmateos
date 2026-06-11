-- ============================================================
--  HUEVOS MATEOS - Portal de pedidos B2B
--  Script 02: SEGURIDAD (Row Level Security - RLS)   [v2]
--  Plataforma: Supabase (PostgreSQL)
--  -----------------------------------------------------------
--  Se ejecuta DESPUÉS de 01_crear_tablas.sql y ANTES de migrar datos.
--  Cambio v2: eliminada la tabla formas_pedido (ya no existe).
--
--  Objetivo: cada cliente, tras iniciar sesión, solo puede leer SUS datos
--  (su ficha y sus ofertas). El catálogo (articulos) es común a todos.
--
--  Identificación: el usuario entra con su EMAIL; auth.jwt()->>'email' lo
--  devuelve; la tabla clientes enlaza email -> codigo; las ofertas se filtran.
-- ============================================================


-- ------------------------------------------------------------
-- 0) Índices que ayudan al rendimiento de las reglas
-- ------------------------------------------------------------
create index if not exists idx_clientes_email on clientes (lower(email));
-- (idx_ofertas_cliente ya se creó en el script 01)


-- ------------------------------------------------------------
-- 1) Función auxiliar: código del cliente que ha iniciado sesión
--    Devuelve el "codigo" de clientes cuyo email coincide con el del
--    usuario autenticado. NULL si no hay sesión o no se encuentra.
--    SECURITY DEFINER: puede leer clientes sin quedar bloqueada por RLS.
-- ------------------------------------------------------------
create or replace function cliente_actual()
returns text
language sql
stable
security definer
set search_path = public
as $$
  select c.codigo
  from clientes c
  where lower(c.email) = lower( (select auth.jwt() ->> 'email') )
  limit 1;
$$;


-- ------------------------------------------------------------
-- 2) Activar RLS en las tres tablas
--    (por defecto, a partir de aquí NADIE ve nada hasta definir políticas)
-- ------------------------------------------------------------
alter table articulos enable row level security;
alter table clientes  enable row level security;
alter table ofertas   enable row level security;


-- ------------------------------------------------------------
-- 3) ARTICULOS: catálogo común. Cualquier usuario AUTENTICADO puede leer.
--    Además, solo se exponen los que se publican y son vendibles.
-- ------------------------------------------------------------
create policy "articulos_lectura_autenticados"
  on articulos
  for select
  to authenticated
  using ( publicar_web = true and vendible = true );


-- ------------------------------------------------------------
-- 4) CLIENTES: cada uno solo ve SU ficha (la de su email).
-- ------------------------------------------------------------
create policy "clientes_ve_su_ficha"
  on clientes
  for select
  to authenticated
  using ( lower(email) = lower( (select auth.jwt() ->> 'email') ) );


-- ------------------------------------------------------------
-- 5) OFERTAS: cada cliente solo ve SUS ofertas.  *** REGLA CRÍTICA ***
-- ------------------------------------------------------------
create policy "ofertas_solo_propias"
  on ofertas
  for select
  to authenticated
  using ( cliente_codigo = (select cliente_actual()) );


-- ============================================================
--  COMPROBACIONES (opcional)
--    -- tablas con RLS activado:
--    select relname, relrowsecurity from pg_class
--    where relname in ('articulos','clientes','ofertas');
--    -- políticas creadas:
--    select tablename, policyname, cmd from pg_policies
--    where tablename in ('articulos','clientes','ofertas');
-- ============================================================

-- ------------------------------------------------------------
--  MIGRACIÓN: la carga de datos desde Python usará la clave SECRETA
--  "service_role", que SALTA RLS por diseño (tareas administrativas).
--  Esa clave NUNCA se pone en la web; solo en el script local.
-- ------------------------------------------------------------
