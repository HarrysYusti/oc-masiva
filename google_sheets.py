# ============================================================================
# google_sheets.py — Módulo de conexión y manejo de Google Sheets
# ============================================================================
# Gestiona la autenticación con Google API, lectura de filas pendientes
# y actualización del estado (REALIZADA / OC) tras procesar cada fila.
# ============================================================================

import os
import gspread
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow

from config import (
    SHEET_ID, SHEET_NAME, CLIENT_SECRET_PATH,
    TOKEN_PATH, SCOPES, Col
)


def _obtener_credenciales() -> Credentials:
    """
    Obtiene credenciales de Google API.
    
    Flujo:
    1. Si existe token.json, lo carga y refresca si expiró.
    2. Si no existe, inicia flujo OAuth interactivo (abre navegador).
    3. Guarda el token resultante para reutilizar en futuras ejecuciones.
    
    Returns:
        Credentials válidas para acceder a Google Sheets API.
    """
    creds = None

    # Intentar cargar token existente
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    # Si no hay credenciales válidas, re-autenticar
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            # Token expirado pero con refresh_token → refrescar automáticamente
            print("🔄 Refrescando token de Google API...")
            creds.refresh(Request())
        else:
            # No hay token o no tiene refresh → flujo interactivo completo
            print("🚀 Iniciando autenticación con Google (se abrirá el navegador)...")
            flow = InstalledAppFlow.from_client_secrets_file(
                CLIENT_SECRET_PATH, SCOPES
            )
            creds = flow.run_local_server(port=0)

        # Guardar token para futuras ejecuciones
        os.makedirs(os.path.dirname(TOKEN_PATH), exist_ok=True)
        with open(TOKEN_PATH, "w") as token_file:
            token_file.write(creds.to_json())
        print(f"💾 Token guardado en: {TOKEN_PATH}")

    return creds


def conectar_sheets() -> gspread.Worksheet:
    """
    Conecta al Google Sheet y retorna el worksheet 'CONSOLIDADO OC'.
    
    Returns:
        gspread.Worksheet: objeto worksheet listo para leer/escribir.
    
    Raises:
        gspread.SpreadsheetNotFound: si el SHEET_ID es inválido.
        gspread.WorksheetNotFound: si la hoja SHEET_NAME no existe.
    """
    if not SHEET_ID:
        raise ValueError(
            "❌ SHEET_ID está vacío en config.py. "
            "Copia el ID de la URL de tu Google Sheet y pégalo ahí."
        )

    creds = _obtener_credenciales()
    client = gspread.authorize(creds)

    # Abrir el spreadsheet por ID y seleccionar la hoja correcta
    spreadsheet = client.open_by_key(SHEET_ID)
    worksheet = spreadsheet.worksheet(SHEET_NAME)

    print(f"✅ Conectado a Google Sheet: '{spreadsheet.title}' → hoja '{SHEET_NAME}'")
    return worksheet


def obtener_filas_pendientes(worksheet: gspread.Worksheet) -> list[dict]:
    """
    Lee todas las filas donde REALIZADA == False (o vacío).
    
    Retorna una lista de diccionarios con los datos de cada fila pendiente.
    Cada dict incluye el número de fila original (1-indexed) para poder
    actualizar la celda correcta después.
    
    Args:
        worksheet: worksheet de gspread conectado.
    
    Returns:
        Lista de dicts, cada uno con:
        - 'fila': número de fila en el Sheet (1-indexed)
        - 'usuario': email del usuario
        - 'cod_sap_proveedor': código SAP del proveedor
        - 'nombre_proveedor': nombre del proveedor
        - 'numero_factura': número de factura
        - 'detalle': justificación
        - 'neto': precio unitario (string)
        - 'fecha_emision': fecha inicio servicio
        - 'fecha_vencimiento': fecha fin servicio
        - 'commodity': código de commodity
        - 'cuenta_contable': código de cuenta
        - 'plan_de_pago': código del plan de pago
        - 'ceco': centro de costos
        - 'aprobador': email del aprobador
        - 'nombre_tienda': nombre de la tienda
        - 'exento': monto exento (puede ser vacío)
    """
    # Obtener todos los valores como lista de listas (incluye header en [0])
    todas_las_filas = worksheet.get_all_values()

    if len(todas_las_filas) < 2:
        print("⚠️ La hoja no tiene filas de datos (solo encabezado).")
        return []

    filas_pendientes = []

    # Iterar desde la fila 2 (índice 1) en adelante, saltando el header
    for idx, fila in enumerate(todas_las_filas[1:], start=2):
        # Verificar que la fila tenga suficientes columnas
        if len(fila) < Col.REALIZADA:
            continue

        # Verificar si REALIZADA es False o vacío (pendiente de procesar)
        valor_realizada = str(fila[Col.REALIZADA - 1]).strip().upper()
        if valor_realizada in ("TRUE", "VERDADERO", "SI", "SÍ"):
            continue  # Ya fue procesada, saltar

        # Construir diccionario con los datos de la fila
        datos = {
            "fila": idx,  # Número de fila real en el Sheet
            "usuario": fila[Col.USUARIO - 1].strip(),
            "cod_sap_proveedor": fila[Col.COD_SAP_PROVEEDOR - 1].strip(),
            "nombre_proveedor": fila[Col.NOMBRE_PROVEEDOR - 1].strip(),
            "numero_factura": fila[Col.NUMERO_FACTURA - 1].strip(),
            "detalle": fila[Col.DETALLE - 1].strip(),
            "neto": fila[Col.NETO - 1].strip(),
            "fecha_emision": fila[Col.FECHA_EMISION - 1].strip(),
            "fecha_vencimiento": fila[Col.FECHA_VENCIMIENTO - 1].strip(),
            "commodity": fila[Col.COMMODITY - 1].strip(),
            "cuenta_contable": fila[Col.CUENTA_CONTABLE - 1].strip(),
            "plan_de_pago": fila[Col.PLAN_DE_PAGO - 1].strip(),
            "ceco": fila[Col.CECO - 1].strip(),
            "aprobador": fila[Col.APROBADOR - 1].strip(),
            "nombre_tienda": fila[Col.NOMBRE_TIENDA - 1].strip(),
            "exento": fila[Col.EXENTO - 1].strip() if len(fila) >= Col.EXENTO else "",
            "solicitud_base": fila[Col.SOLICITUD_BASE - 1].strip() if len(fila) >= Col.SOLICITUD_BASE else "",
        }

        filas_pendientes.append(datos)

    print(f"📋 Filas pendientes encontradas: {len(filas_pendientes)}")
    return filas_pendientes


def marcar_realizada(worksheet: gspread.Worksheet, fila: int, numero_solicitud: str):
    """
    Actualiza una fila procesada en el Sheet:
    - Escribe TRUE en la columna REALIZADA
    - Escribe el # de solicitud en la columna OC
    
    Args:
        worksheet: worksheet de gspread conectado.
        fila: número de fila (1-indexed) a actualizar.
        numero_solicitud: el número de OC extraído de Coupa (ej: "58744").
    """
    # Actualizar columna OC con el número de solicitud
    worksheet.update_cell(fila, Col.OC, numero_solicitud)

    # Marcar como realizada
    worksheet.update_cell(fila, Col.REALIZADA, "TRUE")

    print(f"   📝 Fila {fila} actualizada → OC: {numero_solicitud}, REALIZADA: TRUE")
