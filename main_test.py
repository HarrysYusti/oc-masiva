# ============================================================================
# main_test.py — Script de PRUEBA del RPA (1 sola fila, solo GUARDAR)
# ============================================================================
# Este script procesa SOLO la primera fila pendiente del Sheet y en vez
# de enviar para aprobación, solo GUARDA como borrador.
#
# Úsalo para verificar que todos los campos se llenan correctamente
# en Coupa antes de pasar al script productivo (main.py).
#
# Una vez validado, ejecuta main.py para el procesamiento real.
#
# Ejecución: python main_test.py
# ============================================================================

import sys
import traceback
from playwright.sync_api import sync_playwright

from google_sheets import conectar_sheets, obtener_filas_pendientes, marcar_realizada
from coupa_session import iniciar_sesion
from coupa_actions import (
    buscar_y_copiar_solicitud,
    llenar_justificacion,
    eliminar_adjunto,
    seleccionar_fechas,
    editar_linea_solicitud,
    seleccionar_cuenta,
    extraer_numero_solicitud,
    guardar_borrador,
)


def procesar_una_oc_test(page, datos: dict, es_exento: bool) -> str:
    """
    Ejecuta el flujo en Coupa para generar una OC basándose en los datos.
    Si es_exento es True, usa el monto exento y quita el IVA.
    """
    tipo_monto = "EXENTO" if es_exento else "NETO"
    print(f"\n   --- Procesando OC para Monto {tipo_monto} ---")

    # --- Paso 1: Buscar y copiar solicitud base (columna X del Sheet) ---
    buscar_y_copiar_solicitud(page, datos["solicitud_base"])

    # --- Paso 2: Llenar justificación (DETALLE + NOMBRE TIENDA) ---
    llenar_justificacion(page, datos["detalle"], datos["nombre_tienda"])

    # --- Paso 3: Eliminar adjunto existente ---
    eliminar_adjunto(page)

    # --- Paso 4: Fechas de servicio ---
    seleccionar_fechas(page, datos["fecha_emision"], datos["fecha_vencimiento"])

    # --- Paso 5: Editar línea de solicitud (pasa flag es_exento) ---
    editar_linea_solicitud(page, datos, es_exento=es_exento)

    # --- Paso 6: Cuenta contable y CECO ---
    seleccionar_cuenta(page, datos["cuenta_contable"], datos["ceco"])

    # --- Paso 7: Extraer # de solicitud ---
    numero_solicitud = extraer_numero_solicitud(page)

    # --- Paso 9: GUARDAR como borrador (NO enviar para aprobación) ---
    guardar_borrador(page)

    return numero_solicitud


def procesar_fila_test(page, worksheet, datos: dict):
    """
    Procesa UNA fila en modo prueba.
    Si la fila tiene tanto Neto como Exento, procesará 2 OCs distintas.
    """
    fila_num = datos["fila"]
    print(f"\n{'='*60}")
    print(f"🧪 MODO PRUEBA — Procesando fila {fila_num}")
    print(f"   Proveedor: {datos['nombre_proveedor']} (SAP: {datos['cod_sap_proveedor']})")
    print(f"   Detalle: {datos['detalle']} | Tienda: {datos['nombre_tienda']}")
    print(f"   Neto: {datos['neto']} | Exento: {datos['exento']} | Commodity: {datos['commodity']}")
    print(f"{'='*60}")

    monto_neto = str(datos["neto"]).replace("$", "").replace(".", "").strip()
    monto_exento = str(datos["exento"]).replace("$", "").replace(".", "").strip()

    ocs_generadas = []

    # 1. Procesar OC para NETO
    if monto_neto and monto_neto != "0":
        num_oc = procesar_una_oc_test(page, datos, es_exento=False)
        if num_oc != "ERROR":
            ocs_generadas.append(num_oc)

    # 2. Procesar OC para EXENTO
    if monto_exento and monto_exento != "0":
        num_oc = procesar_una_oc_test(page, datos, es_exento=True)
        if num_oc != "ERROR":
            ocs_generadas.append(num_oc)

    # Mostrar resultado final
    numeros_str = ", ".join(ocs_generadas) if ocs_generadas else "Ninguna OC generada"

    # --- Paso 10: Actualizar Google Sheet ---
    marcar_realizada(worksheet, fila_num, numeros_str)

    print(f"\n{'='*60}")
    print(f"✅ PRUEBA COMPLETADA — Fila {fila_num}")
    print(f"   # Solicitudes generadas: {numeros_str}")
    print(f"   ⚠️ Fueron GUARDADAS como borrador, NO enviadas.")
    print(f"   → Revisa el resultado en Coupa manualmente.")
    print(f"   → Si todo está correcto, ejecuta main.py para el loop productivo.")
    print(f"{'='*60}")

    return numeros_str


def main():
    """
    Función principal del script de prueba.
    Solo procesa la PRIMERA fila pendiente y guarda como borrador.
    """
    print("=" * 60)
    print("🧪 RPA de OC — MODO PRUEBA (1 fila, solo guardar)")
    print("=" * 60)

    # --- Conectar a Google Sheets ---
    print("\n📊 Conectando a Google Sheets...")
    try:
        worksheet = conectar_sheets()
    except Exception as e:
        print(f"❌ Error conectando a Google Sheets: {e}")
        sys.exit(1)

    # --- Obtener primera fila pendiente ---
    print("\n📋 Buscando primera fila pendiente...")
    filas = obtener_filas_pendientes(worksheet)

    if not filas:
        print("ℹ️ No hay filas pendientes. Agrega filas con REALIZADA = FALSE.")
        sys.exit(0)

    # Solo tomar la primera fila
    primera_fila = filas[0]
    print(f"\n📌 Se procesará UNA fila de prueba:")
    print(f"   Fila {primera_fila['fila']}: {primera_fila['nombre_proveedor']} | "
          f"{primera_fila['detalle']} | ${primera_fila['neto']}")

    # --- Iniciar sesión en Coupa ---
    print("\n🔐 Iniciando sesión en Coupa...")
    with sync_playwright() as playwright:
        try:
            browser, context, page = iniciar_sesion(playwright)
        except Exception as e:
            print(f"❌ Error iniciando sesión: {e}")
            traceback.print_exc()
            sys.exit(1)

        # --- Procesar la fila de prueba ---
        try:
            procesar_fila_test(page, worksheet, primera_fila)
        except Exception as e:
            print(f"\n❌ Error durante la prueba: {e}")
            traceback.print_exc()
            print("\n💡 Revisa los selectores en coupa_actions.py y ajusta si es necesario.")

        # No cerrar el navegador automáticamente para que el usuario pueda revisar
        print("\n⏸️ El navegador sigue abierto para que revises el resultado.")
        input("   Presiona ENTER para cerrar el navegador y finalizar...")

        context.close()
        browser.close()

    print("\n🏁 Prueba finalizada.")


if __name__ == "__main__":
    main()
