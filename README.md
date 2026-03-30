# 🤖 RPA de Carga Masiva de OC — Coupa + Google Sheets

Sistema de automatización que lee datos de un Google Sheet y crea Órdenes de Compra (OC) de forma masiva en [Coupa](https://natura.coupahost.com) usando Playwright.

## 📁 Estructura del Proyecto

```
OC masiva/
├── main.py                ← Punto de entrada (ejecutar este archivo)
├── config.py              ← Configuración centralizada (IDs, rutas, constantes)
├── google_sheets.py       ← Conexión y lectura/escritura de Google Sheets
├── coupa_session.py       ← Login en Coupa con reutilización de sesión (auth.json)
├── coupa_actions.py       ← Funciones atómicas de automatización en Coupa
├── README.md              ← Esta documentación
├── credentials/           ← Se crea automáticamente
│   └── auth.json          ← Estado de sesión de Coupa (cookies, storage)
├── token/
│   ├── client_secret_*.json  ← Credenciales OAuth de Google Cloud
│   ├── token.json         ← Token de acceso a Google API (se genera automáticamente)
│   └── generar_token.py   ← Script auxiliar para generar token manualmente
└── documentos/            ← Carpeta para archivos adjuntos (futuro)
```

## 🛠️ Requisitos Previos

### 1. Python 3.10+
Verificar instalación:
```bash
python --version
```

### 2. Dependencias de Python
```bash
pip install playwright gspread google-auth google-auth-oauthlib
```

Instalar navegadores de Playwright:
```bash
python -m playwright install chromium
```

### 3. Credenciales de Google API
Ya tienes el archivo `client_secret_*.json` en la carpeta `token/`. ¡No necesitas hacer nada extra!

Al ejecutar por primera vez, se abrirá una ventana del navegador pidiendo autorizar la aplicación. Después de autorizar, se guardará el token automáticamente.

### 4. ID del Google Sheet
Copia el ID de la URL de tu Google Sheet:
```
https://docs.google.com/spreadsheets/d/<<ESTE_ES_EL_ID>>/edit
```
Pégalo en `config.py` en la variable `SHEET_ID`.

## ⚙️ Configuración

### Paso 1: Configurar `config.py`

Abre `config.py` y ajusta:

| Variable | Qué hacer |
|----------|-----------|
| `SHEET_ID` | **OBLIGATORIO**: Pegar el ID del Google Sheet |
| `COUPA_USER_EMAIL` | Verificar que sea tu email de Coupa |
| `COUPA_USER_PASSWORD` | Verificar que sea tu contraseña actual |
| `HEADLESS` | `False` = ver el navegador, `True` = invisible |
| `SLOW_MO` | Milisegundos entre acciones (500 recomendado) |
| `PLANES_DE_PAGO` | Verificar que los values del `<select>` sean correctos |

### Paso 2: Verificar la hoja `CONSOLIDADO OC`

La hoja debe tener exactamente estas columnas (en este orden):

| Col | Nombre | Descripción |
|-----|--------|-------------|
| A | INGRESO | Timestamp |
| B | USUARIO | Email de Coupa |
| C | COD SAP Proveedor | Código SAP |
| D | RUT | RUT del proveedor |
| E | NOMBRE | Nombre del proveedor |
| F | NUMERO FACTURA | # factura (para buscar solicitud base) |
| G | FECHA EMISION | Fecha inicio servicio |
| H | DETALLE | Justificación |
| I | EXENTO | Monto exento |
| J | NETO | Precio unitario |
| K | FECHA VENCIMIENTO | Fecha fin servicio |
| L | IVA | Monto IVA |
| M | TOTAL | Monto total |
| N | MES | Mes contable |
| O | OC | ← Bot escribe aquí el # de solicitud |
| P | Aprobador | Email del aprobador |
| Q | Commodity | Código commodity |
| R | Cuenta Contable | Código cuenta |
| S | Plan de Pago | Código (CL15, CL30, etc.) |
| T | CECO | Centro de costos |
| U | Almacen SAP tienda | Almacén SAP |
| V | NOMBRE TIENDA | Nombre legible |
| W | REALIZADA | `FALSE` = pendiente, `TRUE` = procesada |

## 🚀 Ejecución

```bash
cd "c:\Users\331642\Desktop\OC masiva"
python main.py
```

### Primera ejecución:
1. Se abrirá el navegador para autorizar Google Sheets (una vez).
2. Se abrirá Chromium para hacer login en Coupa via Google SSO.
3. Ambas sesiones se guardan automáticamente para futuras ejecuciones.

### Ejecuciones siguientes:
- El token de Google se renueva automáticamente.
- La sesión de Coupa se reutiliza vía `credentials/auth.json`.
- Si la sesión de Coupa expira, se hará login automáticamente.

## 📊 Flujo del Bot

```
┌────────────────────────┐
│ 1. Conectar a Sheets   │ → Lee hoja CONSOLIDADO OC
├────────────────────────┤
│ 2. Filtrar pendientes  │ → Filas donde REALIZADA = FALSE
├────────────────────────┤
│ 3. Login en Coupa      │ → auth.json o login SSO
├────────────────────────┤
│ 4. Por cada fila:      │
│  a) Buscar solicitud   │ → Usa NUMERO FACTURA
│  b) Copiar solicitud   │ → Base para nueva OC
│  c) Justificación      │ → Del campo DETALLE
│  d) Eliminar adjunto   │ → Si viene de la copia
│  e) Fechas servicio    │ → FECHA EMISION → VENCIMIENTO
│  f) Proveedor          │ → Autocomplete con NOMBRE
│  g) Commodity          │ → Código del Sheet
│  h) Precio unitario    │ → NETO del Sheet
│  i) Plazo de pago      │ → Plan de Pago → select
│  j) Impuesto IVA 19%   │ → Selección automática
│  k) Cuenta contable    │ → Selector de cuentas
│  l) Aprobador          │ → Búsqueda por email
│  m) Extraer # OC       │ → Del header #XXXXX
│  n) Enviar aprobación  │ → Botón final
│  o) Actualizar Sheet   │ → OC=# y REALIZADA=TRUE
├────────────────────────┤
│ 5. Resumen final       │ → Exitosas vs errores
└────────────────────────┘
```

## 🔧 Solución de Problemas

### "SHEET_ID está vacío"
→ Abre `config.py` y pega el ID de tu Google Sheet.

### "SpreadsheetNotFound"
→ Verifica que el Sheet esté compartido con la cuenta de servicio o con tu email de Google.

### Error de login en Coupa
→ Elimina `credentials/auth.json` y ejecuta de nuevo para forzar un login fresco.

### "Selector not found" o timeout
→ Los selectores pueden cambiar si Coupa actualiza su interfaz. Revisa `coupa_actions.py` y ajusta los selectores según la UI actual.

### El bot se salta filas
→ Verifica que la columna `REALIZADA` tenga exactamente `FALSE` (no vacío ni otro texto).

### Error "Plan de pago no encontrado"
→ Agrega el código faltante al diccionario `PLANES_DE_PAGO` en `config.py`. Inspecciona el `<select>` en Coupa para obtener el value correcto.

## ⚠️ Notas Importantes

- **Prueba con 1 fila primero**: Antes de cargar muchas OC, prueba con una sola fila para verificar que todo funcione correctamente.
- **HEADLESS = False**: Mantén el navegador visible durante las primeras pruebas para poder ver qué hace el bot.
- **SLOW_MO**: Si el bot va muy rápido y falla, aumenta el valor en `config.py` (ej: 1000ms).
- **Contraseñas**: `config.py` contiene credenciales. No subas este archivo a repositorios públicos.
