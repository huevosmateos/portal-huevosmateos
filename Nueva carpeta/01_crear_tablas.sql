-- ============================================================
--  HUEVOS MATEOS - Portal de pedidos B2B
--  Script 01: creación de tablas (esquema de datos)   [v2 - modelo real]
--  Plataforma: Supabase (PostgreSQL)
--  -----------------------------------------------------------
--  Cambios v2 (tras estudiar TABLA_ARTICULOS_EXPLICADA.xls):
--   - articulos AMPLIADA con todos los campos de pedido/fraccionamiento.
--   - tabla formas_pedido ELIMINADA (el modo de pedir se deriva del artículo).
--   - se guarda grupo_iva (no se muestra; precios SIN IVA) por si se necesita.
-- ============================================================

-- Para poder re-ejecutar durante pruebas (orden inverso por dependencias).
drop table if exists ofertas;
drop table if exists clientes;
drop table if exists articulos;


-- ------------------------------------------------------------
-- 1) ARTICULOS
--    Incluye 4 tarifas + los campos que definen CÓMO se pide cada
--    artículo (caja fija / fraccionable / peso variable).
--
--    Tipos de producto que se DERIVAN de estos campos:
--      * Peso variable      : uds_por_caja_fija = 0  (se factura por unidad_monetaria, normalmente KILO)
--      * Uds fijas NO fracc. : uds_por_caja_fija > 0  Y  uds_caja_fraccionable <= 1
--      * Uds fijas fracc.    : uds_por_caja_fija > 0  Y  uds_caja_fraccionable > 1
--
--    El precio (tarifa u oferta) SIEMPRE está expresado POR la unidad_monetaria.
--    Importe = nº_unidades_monetarias × precio × (1 − descuento_cliente%).   (sin IVA)
-- ------------------------------------------------------------
create table articulos (
  codigo                text primary key,            -- CodigoArticulo (texto, ceros a la izq.)
  descripcion           text not null,               -- DescripcionArticulo

  -- precios por tarifa (SIN IVA). El precio es POR unidad_monetaria.
  precio_t0             numeric(10,4) default 0,      -- PrecioVenta        (tarifa 0)
  precio_t1             numeric(10,4) default 0,      -- PrecioVentasinIVA1 (tarifa 1)
  precio_t2             numeric(10,4) default 0,      -- PrecioVentasinIVA2 (tarifa 2)
  precio_t3             numeric(10,4) default 0,      -- PrecioVentasinIVA3 (tarifa 3)

  -- unidad monetaria y formato de pedido
  unidad_monetaria      text,                         -- UnidadMedida2_  (KILO, UNIDAD, DOCENA, BRICK...)
  formato_defecto       text,                         -- UnidadMedidaAlternativa_ (Cajas, Bandejas, Piezas...)
  desc_formato          text,                         -- Descripcion2Articulo (texto del formato por defecto)

  -- reglas de caja / fraccionamiento
  uds_por_caja_fija     numeric(12,4) default 0,      -- CDunidxcaja. 0 => PESO VARIABLE (por kilo)
  uds_caja_fraccionable numeric(12,4) default 0,      -- StockMinimo. >1 => fraccionable
  min_fraccion          numeric(12,4) default 0,      -- PuntoPedido. mínimo de unidades al fraccionar
  desc_fraccion         text,                         -- UnidadMedidaDefecto_ (docenas, Pollos, 1/2 docena...)
  peso_medio_caja       numeric(12,4) default 0,      -- StockMaximo. SOLO si unidad_monetaria=KILO (kg/caja) -> importe estimado

  -- otros
  grupo_iva             smallint,                     -- 1=21%, 2=10%, 3=superreducido (se guarda, no se muestra)
  familia_codigo        text,                         -- CodigoFamilia
  familia               text,                         -- nombre de familia (para agrupar en catálogo)
  marca                 text,                         -- MarcaProducto

  -- visibilidad (filtros del ERP)
  publicar_web          boolean default true,         -- PublicarInternet = 0  -> true (se muestra)
  vendible              boolean default true          -- BloqueoAlbaranVenta = 0 -> true (se puede vender)
);


-- ------------------------------------------------------------
-- 2) CLIENTES
-- ------------------------------------------------------------
create table clientes (
  codigo        text primary key,             -- CodigoCliente (texto, ceros a la izq.)
  nombre        text,                         -- razón social / nombre
  email         text unique,                  -- llave de acceso (puede ir vacío de momento)
  tarifa        smallint not null default 0   -- TarifaPrecio: 0,1,2,3
                check (tarifa between 0 and 3),
  descuento     numeric(5,2) default 0         -- 'Dto. Cliente' en %, se resta al final
);


-- ------------------------------------------------------------
-- 3) OFERTAS  (ArticuloCliente con Automatico = 0)
--    Solo filas que SÍ se aplican. Las de Automatico = -1 NO se suben.
--    Regla: la oferta solo afecta a la CAJA del artículo; las fracciones
--    usan el precio de tarifa (esto se aplica en la lógica del carrito).
-- ------------------------------------------------------------
create table ofertas (
  cliente_codigo  text not null references clientes(codigo) on delete cascade,
  articulo_codigo text not null references articulos(codigo) on delete cascade,
  precio_oferta   numeric(10,4) not null,
  primary key (cliente_codigo, articulo_codigo)
);

-- Índices de apoyo
create index idx_articulos_familia on articulos(familia_codigo);
create index idx_ofertas_cliente   on ofertas(cliente_codigo);

-- ============================================================
--  FIN del script 01 (v2). Tablas creadas y vacías.
-- ============================================================
