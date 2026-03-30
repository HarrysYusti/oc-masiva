# ============================================================================
# config.py — Configuración centralizada del RPA de Carga Masiva de OC
# ============================================================================
# Este archivo contiene todas las constantes, rutas y configuraciones
# que el script necesita. Modificar SOLO este archivo para adaptar el bot
# a diferentes entornos o hojas de Google Sheets.
# ============================================================================

import os

# --- Rutas del proyecto ---
# Directorio raíz del proyecto (donde está este archivo)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Carpeta para almacenar el estado de sesión de Coupa (cookies/auth)
CREDENTIALS_DIR = os.path.join(BASE_DIR, "credentials")
AUTH_JSON_PATH = os.path.join(CREDENTIALS_DIR, "auth.json")

# --- Google API (OAuth2) ---
# Ruta al client_secret descargado de Google Cloud Console
CLIENT_SECRET_PATH = os.path.join(
    BASE_DIR, "token",
    "client_secret_750447830718-ovpklqnoah5s7fjprvj3kr9girgj4c9f.apps.googleusercontent.com.json"
)
# Ruta donde se guarda el token de acceso generado
TOKEN_PATH = os.path.join(BASE_DIR, "token", "token.json")

# Permisos requeridos: lectura/escritura en Sheets y Drive
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# --- Google Sheets ---
# ID del spreadsheet (extraer de la URL del Sheet)
# Ejemplo: https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit
SHEET_ID = "1dh-_8y4zIuLNdu6JiW-xsIVn4zvo9J-5_zZepftnsD0"  # <-- COMPLETAR con el ID real del spreadsheet

# Nombre exacto de la hoja dentro del spreadsheet
SHEET_NAME = "CONSOLIDADO OC"

# --- Mapeo de columnas (1-indexed, como aparecen en el Sheet) ---
# Estas constantes mapean cada campo a su número de columna en "CONSOLIDADO OC"
class Col:
    """Números de columna en la hoja CONSOLIDADO OC (1-indexed)."""
    INGRESO            = 1   # Timestamp de ingreso
    USUARIO            = 2   # Email del usuario de Coupa
    COD_SAP_PROVEEDOR  = 3   # Código SAP del proveedor
    RUT                = 4   # RUT del proveedor
    NOMBRE_PROVEEDOR   = 5   # Nombre completo del proveedor
    NUMERO_FACTURA     = 6   # Número de factura (se usa para buscar la solicitud base)
    FECHA_EMISION      = 7   # Fecha inicio del servicio
    DETALLE            = 8   # Justificación / detalle del servicio
    EXENTO             = 9   # Monto exento (puede ser None)
    NETO               = 10  # Monto neto = precio unitario
    FECHA_VENCIMIENTO  = 11  # Fecha fin del servicio
    IVA                = 12  # Monto IVA
    TOTAL              = 13  # Monto total
    MES                = 14  # Mes contable
    OC                 = 15  # Aquí se escribirá el # de solicitud generada
    APROBADOR          = 16  # Email del aprobador en Coupa
    COMMODITY          = 17  # Código de commodity (ej: 50302002)
    CUENTA_CONTABLE    = 18  # Código de cuenta contable
    PLAN_DE_PAGO       = 19  # Código del plan de pago (ej: CL15)
    CECO               = 20  # Centro de costos
    ALMACEN_SAP        = 21  # Almacén SAP de la tienda
    NOMBRE_TIENDA      = 22  # Nombre de la tienda
    REALIZADA          = 23  # Bandera: False = pendiente, True = procesada
    SOLICITUD_BASE     = 24  # Número de solicitud base a copiar en Coupa

# --- URLs de Coupa ---
COUPA_HOME_URL = "https://natura.coupahost.com"

# --- Configuración del navegador ---
HEADLESS = False  # False = visible (recomendado para debugging)
SLOW_MO = 500     # Milisegundos de pausa entre acciones (ayuda a estabilidad)

# --- Timeouts ---
TIMEOUT_NAVEGACION = 60000   # 60s para cargas de página
TIMEOUT_SELECTOR = 30000     # 30s para esperar elementos
TIMEOUT_CORTO = 10000        # 10s para operaciones rápidas

# --- Mapeo de Planes de Pago ---
# El <select> de Coupa usa un value numérico para cada plan de pago.
# Este diccionario mapea el código legible (del Sheet) al value del <option>.
# Si necesitas agregar más planes, inspecciona el <select> en Coupa.
PLANES_DE_PAGO = {
    "CL15": "652",    # Pago a 15 días
    "CL30": "653",    # Pago a 30 días  (verificar value real)
    "CL45": "654",    # Pago a 45 días  (verificar value real)
    "CL60": "655",    # Pago a 60 días  (verificar value real)
    # Agregar más según sea necesario
}
