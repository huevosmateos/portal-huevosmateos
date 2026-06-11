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

## 11. INSTRUCCIONES PARA LA PRÓXIMA SESIÓN: dar de alta Supabase y ejecutar los scripts

Estado al retomar: usuario ya ha descargado `01_crear_tablas.sql` y
`02_seguridad_rls.sql`. Toca crear la cuenta y ejecutarlos.

### Avisos previos (importantes)
- La **contraseña de la BASE DE DATOS** (la pide al crear el proyecto) es DISTINTA
  de la contraseña de la cuenta. Apuntarla bien antes de seguir.
- La **región** no se puede cambiar después. Elegir `West EU (Ireland)` o
  `Central EU (Frankfurt)`.

### Paso 1 — Crear la cuenta
- Ir a `https://supabase.com` y pulsar **"Start your project"**.
- Registrarse con email (recomendado) o con GitHub.
- Si es por email: confirmar el correo desde el enlace recibido.

### Paso 2 — Crear la organización
- Nombre tipo "Huevos Mateos".
- Plan: **Free**.

### Paso 3 — Crear el proyecto
- Botón **"New project"**.
- Project name: `huevosmateos-portal` (u otro claro).
- **Database Password**: contraseña fuerte. **Apuntar antes de seguir**.
- Region: `West EU (Ireland)` o `Central EU (Frankfurt)`.
- Plan: Free.
- Pulsar **"Create new project"**. Tarda 1-2 min, no cerrar la pestaña.

### Paso 4 — Familiarizarse con el panel
- Menú izquierdo. Opciones que importan:
  - **Table Editor**: ver tablas (al principio vacío).
  - **SQL Editor**: ejecutar los scripts (icono `</>` o "SQL").
  - **Authentication**: logins de clientes (más adelante).
  - **Project Settings** (rueda dentada abajo): claves API (NO TOCAR aún).

### Paso 5 — Ejecutar `01_crear_tablas.sql`
- SQL Editor -> **"+ New query"** -> editor en blanco.
- Copiar TODO el contenido del archivo y pegarlo.
- Pulsar **"Run"** (F5 o Ctrl+Enter).
- **Esperado:** mensaje verde "Success. No rows returned".
- Si sale rojo: pegarme el error exacto, NO continuar.

### Paso 6 — Verificar tablas creadas
- Table Editor -> schema `public`.
- Deben aparecer 3 tablas: `articulos`, `clientes`, `ofertas`.

### Paso 7 — Ejecutar `02_seguridad_rls.sql`
- SQL Editor -> **"+ New query"** -> hoja nueva.
- Copiar y pegar TODO el contenido.
- Pulsar **Run**. Esperado: verde.
- Si rojo: pegarme el error, NO continuar.

### Paso 8 — Verificar que RLS está activo
- SQL Editor -> hoja nueva. Ejecutar:
  ```sql
  select tablename, rowsecurity from pg_tables
  where tablename in ('articulos','clientes','ofertas');
  ```
- Debe devolver 3 filas con `rowsecurity = true`.

### Tras completar los 8 pasos
Confirmar a Claude:
- Proyecto creado y se accede sin problema.
- Script 01 ejecutado sin errores.
- 3 tablas visibles en Table Editor.
- Script 02 ejecutado sin errores.
- La consulta del paso 8 devuelve rowsecurity = true en las tres.

Si algo falla, PARARSE y pegar el error tal cual. Es más fácil resolverlo en
ese punto que tras seguir avanzando.

---

## 10. Archivos del proyecto

- `01_crear_tablas.sql` — esquema de tablas para Supabase (pendiente de ejecutar).
- `tiendaconprecio.html` — web actual funcionando (catálogo con precios, login,
  habituales). Base sobre la que se construirá el portal.
- `tienda.html` — versión pública sin precios.
- `actualizar_web.py` — script que genera la web desde el ERP (a adaptar en Fase 3).

---

## 12. AVANCES SESIÓN 2 (cuenta Supabase + migración de datos)

### Cuenta y proyecto creados
- Organización: HUEVOS MATEOS, SL (plan Free)
- Proyecto: `huevo mateos-portal` (nombre interno, no afecta a nada)
- Región: Europa Occidental (Irlanda) - eu-west-1
- URL del proyecto: `https://pkwttturncewwdlpxrxz.supabase.co`
- Estado: Saludable, sin uso significativo de recursos

### Claves API
- Supabase usa formato NUEVO (`sb_publishable_...`, `sb_secret_...`) pero
  la librería Python `supabase 2.6.0` (la última compatible con Python 3.8)
  NO acepta ese formato.
- SOLUCIÓN APLICADA: usamos las claves LEGACY (formato `eyJ...`, 219 caracteres),
  obtenidas en Settings → API Keys → sección Legacy Keys.
- Guardadas como variables de entorno PERMANENTES de Windows con `setx`:
  - `SUPABASE_URL`
  - `SUPABASE_SERVICE_KEY` (secreta, NUNCA en la web)
- Las claves originales están guardadas en archivo `claves_supabase.txt` local.

### Scripts SQL ejecutados en Supabase
- `01_crear_tablas.sql` (v2) ✓ ejecutado → 3 tablas creadas
- `02_seguridad_rls.sql` (v2) ✓ ejecutado → RLS activado, función
  `cliente_actual()` creada, políticas en las 3 tablas
- Verificación: las 3 tablas tienen `rowsecurity = true`

### Script Python de migración: `migrar_a_supabase.py`
Carpeta del usuario: `C:\bot_whatsapp\webhuevosmateos`
- Lee artículos de la TABLA `Articulos` (no de la consulta, que no trae todos los campos)
- Nombre de familia: de la consulta `CONSULTA ARTICULOS POR FAMILIAS`
- Clientes: tabla `Clientes` cruzada con `CONSULTA CLIENTES EMAIL FACTURAS`
- Ofertas: `ArticuloCliente WHERE Automatico = 0`
- FILTRO al subir artículos: SOLO los vendibles (`BloqueoAlbaranVenta = 0`)
- En modo `completo` limpia obsoletos: artículos/clientes/ofertas que ya no están
- Robustez: detección de emails duplicados (vacía email en repetidos), reintento
  fila a fila si un lote falla
- Modos: `prueba` (5 art / 3 cli / 3 oft), `completo`, `contar`

### Resultado migración completa (verificado en Supabase):
- articulos:          491   (164 descartados por bloqueados)
- clientes:           2973  (de 2973 totales, 405 con email único)
- ofertas:            1894  (80 descartadas porque referencian a clientes/articulos no migrados)
- clientes_con_email: 405

### Verificación end-to-end OK:
- Cliente 1117 (BERNAL SANTA ELENA): tarifa 1, descuento 0%, 4 ofertas vinculadas.

---

## 13. DECISIÓN DE LOGIN (importante)

Tras analizar:
- Algunos clientes COMPARTEN email pero son entidades independientes (sucursales).
- Se valoraron 3 opciones (A: email duplicado + contraseña; B: email único Supabase Auth;
  C: código cliente + contraseña).
- **DECISIÓN FINAL: Opción B — email único, Supabase gestiona contraseñas.**
- Auto-registro: SOLO si el email YA está en la tabla `clientes` (control vía Auth Hook).
- Notificación al admin: SOLO en registros NUEVOS (no en cada login), en tiempo real.
- Los clientes con email duplicado NO podrán entrar al portal hasta que se les
  asigne un email único en el ERP (se hará después, no es bloqueante).

### Pendiente: arreglo manual en ERP de emails duplicados
- Hay clientes con el mismo email que deben recibir email único para acceder
  al portal. Script disponible: `informe_emails_duplicados.py` (en la carpeta
  del usuario), genera CSV con la lista por email.

---

## 14. INFRAESTRUCTURA DE EMAIL (pendiente de montar)

### Problema descubierto
- Supabase trae SMTP por defecto pero limitado a **2 emails/hora** (solo dev).
- Para producción es OBLIGATORIO configurar SMTP propio.
- Además, el remitente por defecto es feo (`noreply@mail.app.supabase.io`).

### Solución elegida: Resend
- Plan gratuito: 3.000 emails/mes, 100/día (sobra para nuestros 405 clientes).
- Permite usar dominio propio como remitente (más profesional, menos spam).
- Configuración sencilla en Supabase (Authentication → SMTP Settings).
- Alternativa de respaldo: Brevo (300/día gratis).

### Requisito clave: dominio propio bajo nuestro control
- El dominio actual `huevosmateos.es` está en una empresa externa con la que
  no hay buena relación. NO se puede acceder al DNS.
- DECISIÓN del usuario: registrar `huevosmateos.net` NUEVO, solo para el portal B2B.
  Así tendrá control total de DNS sin depender de la otra empresa.
- Registradores recomendados (con buen panel DNS): Namecheap, Cloudflare,
  OVH, DonDominio (español).

---

## 15. ESTADO ACTUAL (al cerrar sesión 2)

### HECHO (verificado y funcionando):
- ✓ Supabase: cuenta, proyecto, 3 tablas, RLS activado, función auxiliar.
- ✓ Datos cargados: 491 artículos, 2973 clientes (405 con email), 1894 ofertas.
- ✓ Variables de entorno permanentes con las claves legacy.
- ✓ Script de migración robusto y reutilizable: `migrar_a_supabase.py`.
- ✓ Script de informe de emails duplicados: `informe_emails_duplicados.py`.

### TAREAS DEL USUARIO antes de la próxima sesión:
1. **Registrar dominio `huevosmateos.net`** (un registrador serio: Namecheap,
   Cloudflare, OVH, DonDominio). Sobre 10-15€/año.
2. **Crear cuenta gratuita en Resend** (`resend.com`). Solo registrarse, no
   configurar nada todavía.
3. **Decidir** a qué email recibir las notificaciones de registros nuevos
   (personal o corporativo).
4. **Opcional**: revisar el CSV de emails duplicados (`emails_duplicados.csv`)
   para tenerlos identificados de cara a arreglarlos en el ERP cuando se quiera.

### PRÓXIMA SESIÓN — pasos previstos:
1. Verificar que el dominio nuevo está registrado y accesible (panel DNS).
2. Verificar dominio en Resend (añadir registros SPF, DKIM, DMARC al DNS).
3. Configurar SMTP de Resend en Supabase.
4. Configurar email templates en Supabase (mensajes de bienvenida/confirmación).
5. Crear el Auth Hook en Supabase que valida: "solo permitir registro si el
   email ya existe en la tabla `clientes`".
6. Configurar notificación a admin al registrarse un cliente nuevo (Auth Hook
   o trigger SQL).
7. Probar el flujo end-to-end con un cliente de prueba (autoregistro → recibe
   email → confirma → admin recibe aviso → cliente puede entrar y solo ve SUS datos).
8. Cuando funcione: empezar Fase 3 — adaptar la web (`tiendaconprecio.html`)
   para que use Supabase Auth real en lugar del PIN actual.

### ARCHIVOS ACTUALES del usuario en `C:\bot_whatsapp\webhuevosmateos`:
- `actualizar_web_ultimaversion.py` (sin cambios, sigue generando HTML)
- `migrar_a_supabase.py` (nuevo, para volcar datos a Supabase)
- `informe_emails_duplicados.py` (utilidad de un solo uso)
- `pruebaconexxion.py` y `diag.py` (utilidades de diagnóstico)
- `01_crear_tablas.sql` y `02_seguridad_rls.sql` (ya ejecutados; conservar por si rehay)
- `claves_supabase.txt` (PRIVADO, no compartir)
- HTML de la web actual (sin cambios)


---

## 16. AVANCES SESIÓN 3 (dominio, Resend, Auth Hook y validaciones)

### Dominio registrado
- **`huevosmateos.net`** registrado en **DonDominio** a nombre de HUEVOS MATEOS, S.L.
- Activo. Servidores DNS de DonDominio (ns1/ns2.dondominio.com).
- Expira el 31/05/2027. Renovación manual.
- 4 registros DNS añadidos para Resend:
  - TXT `_dmarc` → `v=DMARC1; p=none;`
  - TXT `send` → `v=spf1 include:amazonses.com ~all`
  - TXT `resend._domainkey` → DKIM (clave pública)
  - MX `send` → `feedback-smtp.eu-west-1.amazonses.com` (priority 10)
- Pendiente futuro: activar "Bloqueo de transferencia" cuando todo esté estable.

### Resend (servicio SMTP)
- Cuenta creada: workspace `huevosmateos`
- Dominio `huevosmateos.net` verificado en Resend (estado: Verified)
- API key generada (almacenada en `claves_supabase.txt` local)
- SMTP configurado en Supabase:
  - Host: `smtp.resend.com`
  - Port: 465
  - Username: `resend`
  - Sender: `correo@huevosmateos.net` (display: "Huevos Mateos")

### Plantillas de email traducidas al español
- Confirm sign up ✓
- Invite user ✓
- Magic link or OTP ✓
- Change email address ✓
- Reset password ✓
- Reauthentication ✓
- Password changed ✓
- Subjects también traducidos por el usuario.
- (Las plantillas de "Security" como cambios de teléfono/MFA quedan en inglés;
  no críticas, traducir si en algún momento se activan.)

### Corrección crítica de migración (convención ERP)
- IMPORTANTE descubierto: en este ERP la convención booleana es `-1 = SÍ` / `0 = NO`.
- Errores que se han corregido en `migrar_a_supabase.py`:
  - `publicar_web` estaba al revés. Ahora: `PublicarInternet != 0`.
  - `vendible` estaba bien (`BloqueoAlbaranVenta = 0` → vendible).
- Datos en Supabase corregidos con `update articulos set publicar_web = not publicar_web;`

### Nueva tabla: campo `puede_acceder`
- Añadida columna a `clientes`:
  ```sql
  alter table clientes
    add column if not exists puede_acceder boolean default false;
  ```
- Lee de `ActivarLogicNet` del ERP. Convención `-1 = SÍ puede acceder`.

### Filtro nuevo de clientes en migración
- Solo se suben clientes con `BloqueoAlbaran = 0` (no bloqueados).
- En modo `completo` se limpian los obsoletos automáticamente.

### Decisión final sobre emails (modelo de acceso)
- **Solo se sube `email` a Supabase si el cliente está autorizado** (`ActivarLogicNet=-1`).
- Los NO autorizados se suben sin email → invisibles para Supabase Auth.
- Si un cliente intenta registrarse y no encuentra email, le sale el mensaje
  genérico "no es posible darte de alta, deja tus datos y contactaremos".
- Detección de duplicados: si dos AUTORIZADOS comparten email, el script
  DESACTIVA a todos los del grupo y avisa por pantalla. El usuario decide en el ERP.
- Script auxiliar creado: `informe_duplicados_autorizados.py` (verifica sin migrar)

### Migración final realizada con números cuadrados ✓
- **articulos:** 491 (332 con `publicar_web=true` para tienda pública)
- **clientes:** 1078 (todos no bloqueados)
- **clientes_con_email:** 386 (todos autorizados a entrar)
- **clientes_acceso (puede_acceder=true):** 393
  - 7 clientes autorizados sin email en el ERP (les falta email asignado)
- **ofertas:** 1674
- Sin emails duplicados detectados entre autorizados ✓

### Auth Hook configurado y funcionando ✓
- Función SQL creada: `public.validar_registro_cliente(event jsonb)`
- Lee el email del evento en `event #>> '{user,email}'`
- Casos:
  - Email NO en clientes → `EMAIL_NO_AUTORIZADO` (HTTP 403)
  - Email sí pero `puede_acceder = false` → `CLIENTE_NO_AUTORIZADO` (HTTP 403)
  - Email autorizado → `{ decision: "continue" }`
- Hook activado en panel: Authentication → Auth Hooks → Before User Created
  - Tipo: Postgres
  - Schema: public
  - Función: `validar_registro_cliente`
- **Pruebas pasadas con éxito:**
  - Email inexistente → rechazado con `EMAIL_NO_AUTORIZADO`
  - Email autorizado (`vicentemateosperal@gmail.com`) → registro permitido,
    email enviado vía Resend, llegado a Gmail (bandeja principal, no spam),
    remitente correcto: `Huevos Mateos <correo@huevosmateos.net>`

### Archivos actualizados del usuario
En `C:\bot_whatsapp\webhuevosmateos`:
- `migrar_a_supabase.py` ✓ (versión final con todos los filtros y reglas)
- `informe_duplicados_autorizados.py` ✓ (utilidad de verificación)
- Resto de archivos sin cambios

---

## 17. ESTADO ACTUAL (al cerrar sesión 3)

### HECHO Y VERIFICADO ✓
- Dominio `.net` registrado.
- Resend configurado y entregando emails al dominio.
- SMTP de Resend conectado a Supabase.
- Plantillas de email en español (con subjects).
- Auth Hook que valida acceso contra `clientes.puede_acceder`.
- Pruebas end-to-end de registro: rechaza no autorizados, permite autorizados.
- Migración con todos los filtros y reglas correctas.

### PRÓXIMO PASO (donde retomar)
**Configurar notificación a admin por email** cuando un cliente nuevo se confirma:
- Estrategia elegida: **Opción A** — Trigger SQL en `auth.users` con `pg_net`
  para llamada HTTP a Resend.
- Activar al confirmar email (no al registrar, sino cuando el usuario clica
  el enlace de confirmación).
- Destinatario: `correo@huevosmateos.es`
- Datos a incluir: **código cliente + nombre (razón social) + nombre comercial
  + email + teléfono**.

### Pasos concretos pendientes para el siguiente chat:
1. **Activar la extensión `pg_net`** en Supabase (Database → Extensions).
   Estaba disponible pero no instalada (versión 0.20.3, installed_version = NULL).
2. **Ampliar `migrar_a_supabase.py`** para incluir `NombreComercial` y `Telefono`
   en la tabla clientes (campo nuevo en Supabase + lectura del ERP).
3. **Crear función SQL `notificar_registro_admin()`** que coge los datos del cliente
   recién confirmado y llama a Resend vía pg_net.
4. **Crear trigger** en `auth.users` que se dispara cuando `email_confirmed_at`
   pasa de NULL a una fecha (= confirmación). Llama a la función.
5. **Probar el flujo completo:** registro → confirmación → llegada de notificación
   a `correo@huevosmateos.es`.

### Decisiones de fondo cerradas (no replantear):
- Opción B de login: email único + Supabase Auth gestiona contraseñas. ✓
- Solo clientes con `ActivarLogicNet=-1` reciben email en Supabase. ✓
- Si un CIF tiene varias tiendas, solo la principal entra al portal. Las
  secundarias deben pedir nuevo email (fuera de banda). ✓
- Identificador único: email (gracias al filtro anterior, no hay duplicados). ✓
- Trigger SQL + pg_net para notificaciones (no Edge Functions). ✓

### NOTAS técnicas para no perder
- El email viene en `event #>> '{user,email}'` en el hook Before User Created.
- Resend usa formato nuevo `sb_secret_...`, pero por compatibilidad con
  Python 3.8 + supabase 2.6.0, usamos claves LEGACY `eyJ...` desde
  Settings → API Keys → Legacy.
- Variables de entorno Windows permanentes: `SUPABASE_URL` y `SUPABASE_SERVICE_KEY`.

