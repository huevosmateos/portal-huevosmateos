# Proyecto: Portal de pedidos B2B — Huevos Mateos

Documento de seguimiento. Resume todas las decisiones tomadas para poder
retomar el proyecto más adelante sin perder el hilo.

---

## 1. Qué estamos construyendo

Un **portal de pedidos B2B** (no una tienda de pago) para clientes
profesionales. Los clientes entran con su email, ven el catálogo con SUS
precios, y hacen pedidos/encargos. El importe es **estimado**; el importe
final lo sigue poniendo el ERP al pesar/facturar (como ahora).

- Clientes: ~100-200
- Productos: ~400
- No hay pago online: es pedido/encargo a confirmar.

## 2. Decisión de arquitectura

**Opción elegida: B — Web actual + backend a medida.**

Motivo: lo más importante es que **encaje exacto** como trabajan, y hay
capacidad de tocar código con guía. WooCommerce se descartó porque obligaría
a forzar la herramienta (desactivar pago, varios plugins) para algo que no es
su propósito.

La seguridad de los datos (preocupación principal) se resuelve usando
**Supabase** (base de datos PostgreSQL + login de usuarios gestionado).
Plan gratuito suficiente para este volumen. La parte sensible (contraseñas,
autenticación) la mantiene Supabase, no el usuario.

## 3. Modelo de datos del ERP (origen, en Access)

- **Articulos**: cada producto tiene 4 precios de tarifa:
  - `PrecioVenta` = tarifa 0
  - `PrecioVentasinIVA1` = tarifa 1
  - `PrecioVentasinIVA2` = tarifa 2
  - `PrecioVentasinIVA3` = tarifa 3
- **Clientes**: campo `TarifaPrecio` indica qué tarifa (0-3) le toca al cliente.
  También hay un **Dto. Cliente** (ej. 10%) que se resta al final del pedido.
- **ArticuloCliente** (tabla de ofertas):
  - `Automatico = 0`  -> el cliente tiene precio especial; se aplica `PrecioOferta`.
  - `Automatico = -1` -> NO hay precio especial; se ignora la fila (el PrecioOferta
    que aparezca es residual). Se aplica el precio de tarifa del cliente.
- Códigos con ceros a la izquierda (cliente `1117`, artículo `0510`): se tratan
  como **texto** para conservarlos.
- Artículos 9999 / 9990 / 5005: comentarios u obsoletos -> se marcan inactivos.

## 4. Regla de precio (cómo se calcula el precio de un cliente para un artículo)

1. ¿Existe fila en ofertas (Automatico=0) para ese cliente + artículo?
   - Sí -> usar `precio_oferta`.
   - No -> usar la columna de tarifa del artículo según la tarifa del cliente.
2. Al final del pedido se resta el **descuento de cliente** (%).

## 5. Formas de pedir (variantes)

- Normalmente se pide **por CAJA** (forma principal).
- **Solo algunos** productos tienen variantes: además de caja, se pueden pedir
  por **unidad** o por **kilo**.
- La **unidad monetaria** es la base del importe: importe = unidades_reales × precio.
  Ejemplo (pollo 0510): se factura por **kg**; la caja "tiene 8 pollos" es solo
  informativo; el peso es variable (15,50 kg, 16,28 kg...).
- El cliente puede pedir: 1 caja (normal), 4 pollos (variante), o 10 kg (variante).

### Regla importante de precios en variantes
- El **precio de oferta** (cliente-artículo) **solo aplica a la forma CAJA**.
- El resto de variantes (unidad, kilo) reciben **solo el precio de tarifa** del cliente.

### Importe ESTIMADO con peso medio
- Para productos por peso, SÍ se usará un **peso medio orientativo** (por caja y
  por unidad) para mostrar un importe estimado en todas las formas de pedir.
- El importe mostrado es **orientativo**; el definitivo lo pone el ERP al pesar.
  Esto debe quedar claro en la web (etiqueta tipo "importe estimado").

## 5-BIS. MODELO REAL DE ARTÍCULOS (del Excel TABLA_ARTICULOS_EXPLICADA.xls)

El usuario documentó cada campo del ERP. Significado real de cada columna:

| Campo ERP | Significado |
|-----------|-------------|
| BloqueoAlbaranVenta | 0 = se puede vender en ERP ; -1 = bloqueado venta |
| PublicarInternet | 0 = se muestra en web ; -1 = bloqueado para web |
| CodigoArticulo | código (texto, zfill 4) |
| DescripcionArticulo | nombre del artículo |
| UnidadMedidaAlternativa_ | FORMATO POR DEFECTO para pedidos (ej. "Cajas","Bandejas","Piezas","Kilos") |
| Descripcion2Articulo | descripción del formato de pedido por defecto |
| **CDunidxcaja** | uds que contiene la caja CUANDO SON UDS FIJAS. **Si =0 -> unidad monetaria VARIABLE (se factura por kilo/peso variable)** |
| PrecioVentasinIVA1 | PRECIO TARIFA 1 |
| **UnidadMedida2_** | UNIDAD MONETARIA (sobre la que se multiplica el precio): KILO, UNIDAD, DOCENA, BRICK, CAJA, LITRO... |
| **StockMinimo** | uds que contiene la caja CUANDO SE PUEDE FRACCIONAR. Si fraccionable debe ser >1 |
| **PuntoPedido** | UNIDADES MÍNIMAS en la fracción de caja |
| UnidadMedidaDefecto_ | descripción de la unidad de pedido en fracciones (ej "docenas","Pollos","1/2 docena") |
| **StockMaximo** | PESO ORIENTATIVO de la caja, SOLO para UnidadMedida2_=KILO (para importe estimado) |
| CodigoFamilia | código de familia |
| MarcaProducto | marca |
| GrupoIva | 1=IVA general 21%, 2=reducido 10%, 3=superreducido |
| PrecioVenta | PRECIO TARIFA 0 |
| PrecioVentasinIVA2 | PRECIO TARIFA 2 |
| PrecioVentasinIVA3 | PRECIO TARIFA 3 |

### Cómo se calcula el importe (CLAVE para el carrito)
**El precio (tarifa u oferta) SIEMPRE está expresado POR la UnidadMedida2_** (la unidad monetaria).
Importe = (nº de unidades monetarias) × precio × (1 − descuento_cliente%).

### TRES TIPOS DE PRODUCTO (según CDunidxcaja y StockMinimo)

**Tipo B — Uds fijas, NO fraccionable** (CDunidxcaja>0, StockMinimo≤1). ~300 productos.
  - Se pide por caja. La caja contiene CDunidxcaja unidades monetarias.
  - Ej. bolsa 0008: caja=200 bolsas, precio por BOLSA. 1 caja -> 200 × precio.
  - Importe exacto (no hay peso variable).

**Tipo C — Uds fijas, FRACCIONABLE** (CDunidxcaja>0 Y StockMinimo>1). ~12 productos.
  - Se puede pedir caja entera o fracción.
  - StockMinimo = uds monetarias por caja ; PuntoPedido = mínimo de fracción.
  - Ej. huevo 0424: UnidadMedida2=DOCENA, caja=24 docenas, fracción mín=12 docenas,
    precio 2,75 POR DOCENA. 1 caja -> 24×2,75 ; fracción de 12 -> 12×2,75.
  - Importe exacto.

**Tipo A — PESO VARIABLE** (CDunidxcaja=0). ~178 productos. UnidadMedida2_=KILO casi siempre.
  - Se factura por KILO, peso real desconocido hasta pesar -> importe ESTIMADO.
  - StockMaximo = peso medio de la caja (kg). StockMinimo = piezas que trae la caja.
    PuntoPedido = mínimo de piezas si se fracciona. UnidadMedidaDefecto_ = nombre pieza.
  - Ej. pollo 0510: precio 3,25/kg, caja pesa ~16 kg (StockMaximo), caja=8 pollos
    (StockMinimo), mín fracción 4 pollos (PuntoPedido), pieza="Pollos".
    * Pedir 1 caja  -> estimado 16 × 3,25
    * Pedir 4 pollos -> estimado (16/8)×4 × 3,25 = peso_medio_pieza × nº × precio
    * Pedir 10 kg    -> 10 × 3,25 (exacto en kg, sigue siendo estimado el total al pesar)

### Notas
- Filtrar a la web por PublicarInternet=0 (mostrar) y BloqueoAlbaranVenta=0 (vendible).
- IVA por producto está en GrupoIva (puede hacer falta para importe con/sin IVA).
- Hay MÁS de 4 unidades monetarias distintas (KILO, UNIDAD, DOCENA, BRICK...); el
  diseño de tablas debe guardar UnidadMedida2_ como texto libre, no enum cerrado.

---

## 6. Acceso de clientes

- Login por **email + contraseña/PIN**.
- Las contraseñas dejarán de estar en el HTML; las gestiona Supabase cifradas.
- **Pendiente de decidir** (fase login): si cada cliente elige su contraseña o
  se le asigna inicialmente; y recuperación por email.
- **Emails: hay que completarlos.** No todos los clientes tienen email todavía.
  Plan: arrancar con los que ya lo tienen e ir añadiendo el resto. El diseño
  permite emails vacíos de momento.

## 7. Datos del ERP -> cómo se extraen

- El ERP es Access. La extracción se hará con el **script Python que ya existe**
  (`actualizar_web.py`), adaptándolo para volcar a Supabase en vez de (o además
  de) generar HTML. El "cerebro" sigue siendo el ERP.

---

## 8. Plan por fases

- **Fase 1 — Catálogo "pedible"** (frontend, sin datos sensibles): añadir carrito
  de pedido a la web, con selector de forma (caja/unidad/kilo), cantidad e importe
  estimado, panel "Mi pedido" y botón de enviar. Se puede empezar sin tocar servidores.
- **Fase 2 — Seguridad / datos** (EN CURSO): mover clientes, tarifas y ofertas a
  Supabase; login real; cada cliente solo ve SUS precios.
- **Fase 3 — Conectar el ERP**: adaptar `actualizar_web.py` para volcar datos a Supabase.
- **Fase 4 — Recepción de pedidos**: que los pedidos lleguen por email o en un
  formato que el ERP pueda leer para generar el albarán.

---

## 9. ESTADO ACTUAL / por dónde retomar

Estamos en la **Fase 2**, seguridad/datos. Diseño cerrado y reglas RLS escritas.

**HECHO:**
- Modelo de datos cerrado (ver secciones 3-6).
- `01_crear_tablas.sql` escrito (4 tablas). NO ejecutado aún.
- `02_seguridad_rls.sql` escrito (reglas RLS). NO ejecutado aún.
- Revisado `actualizar_web.py`: confirma que los códigos son TEXTO con zfill(4),
  y que ya sabe leer de Access las tablas/consultas necesarias:
  'CONSULTA ARTICULOS POR FAMILIAS', 'ArticuloCliente',
  'CONSULTA CLIENTES EMAIL FACTURAS', 'Clientes'.
  El email del cliente sale de EMail1 (o Domicilio2) y el PIN de ContraseñaLogicNet.

**DECISIONES nuevas de esta sesión:**
- Vinculación cliente<->login POR EMAIL (auth.jwt()->>'email'). Enfoque simple.
- RLS antes de migrar: CONFIRMADO.
- Contraseña de login: DECIDIR MÁS ADELANTE (no bloquea diseño ni RLS).
- Migración de datos se hará con la clave SECRETA "service_role" (salta RLS),
  solo en el script Python local, NUNCA en la web.
- **El Excel TABLA_ARTICULOS_EXPLICADA reveló el modelo real de productos**
  (ver sección 5-BIS). Es más rico que el diseño inicial: el fraccionamiento y el
  peso variable se describen con campos POR ARTÍCULO (CDunidxcaja, StockMinimo,
  PuntoPedido, StockMaximo, UnidadMedida2_), NO con una tabla de variantes cerrada.

**CONSECUENCIA - REDISEÑO (HECHO en esta sesión):**
- `formas_pedido` ELIMINADA. El modo de pedir se deriva de los campos del artículo.
- `articulos` (script 01 v2) AMPLIADA con: unidad_monetaria, formato_defecto,
  desc_formato, uds_por_caja_fija, uds_caja_fraccionable, min_fraccion,
  desc_fraccion, peso_medio_caja, grupo_iva, familia_codigo, familia, marca,
  publicar_web, vendible. (Mapeo a campos ERP documentado en el propio SQL.)
- IVA: precios se muestran SIN IVA, pero se GUARDA grupo_iva por si se necesita
  para valorar pedidos. CONFIRMADO por el usuario.
- Scripts 01 y 02 REGENERADOS (v2) y validados sintácticamente (paréntesis y
  bloque $$ correctos). Listos para ejecutar en Supabase.

**PENDIENTE DE VALIDAR (menor, no bloquea):**
1. Confirmar fórmula importe estimado: precio × cantidad × (1 − descuento%).
2. Cuando se monte el login, decidir contraseña (PIN actual vs nueva por cliente).

**SIGUIENTES PASOS (cuando se retome):**
- Crear cuenta en Supabase (primera vez) + proyecto. Guía de clics pendiente.
- Ejecutar en el SQL Editor de Supabase, EN ORDEN:
    1º  `01_crear_tablas.sql`   (v2 - modelo real, 3 tablas)
    2º  `02_seguridad_rls.sql`  (v2 - RLS sin formas_pedido)
- Luego: adaptar Python para migrar datos (script 03, usando service_role).
  El Python leerá de Access los campos según el mapeo de la sección 5-BIS.
- Después: montar el login en la web y conectar lectura de datos desde Supabase.

**ARCHIVO FUENTE clave:** TABLA_ARTICULOS_EXPLICADA.xls (490 productos, 19 campos
documentados por el usuario). Es la referencia del mapeo ERP -> Supabase.

---

## 10. Archivos del proyecto

- `01_crear_tablas.sql` — esquema de tablas para Supabase (pendiente de ejecutar).
- `tiendaconprecio.html` — web actual funcionando (catálogo con precios, login,
  habituales). Base sobre la que se construirá el portal.
- `tienda.html` — versión pública sin precios.
- `actualizar_web.py` — script que genera la web desde el ERP (a adaptar en Fase 3).
