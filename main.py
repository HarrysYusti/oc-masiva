# ============================================================================
# main.py — Orquestador principal del RPA de Carga Masiva de OC
# ============================================================================
# Este es el punto de entrada del script. Coordina todos los módulos:
#   1. Conecta a Google Sheets y obtiene filas pendientes
#   2. Inicia sesión en Coupa (login o reutiliza auth.json)
#   3. Para cada fila pendiente, ejecuta el flujo completo de creación de OC
#   4. Actualiza el Sheet con el resultado (# OC + REALIZADA = True)
#
# Ejecución: python main.py
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
    enviar_para_aprobacion,
)


def procesar_una_oc(page, datos: dict, es_exento: bool) -> str:
    """
    Ejecuta el flujo en Coupa para generar una sola OC basándose en los datos.
    Si es_exento es True, usa el monto de la columna exento y quita el IVA.
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

    # --- Paso 9: Enviar para aprobación ---
    enviar_para_aprobacion(page)

    return numero_solicitud


def procesar_fila(page, worksheet, datos: dict) -> str:
    """
    Procesa una fila en Coupa orquestando todas las acciones necesarias.
    Si la fila tiene tanto Neto como Exento, procesará 2 OCs consecutivas.
    """
    fila_num = datos["fila"]
    print(f"\n{'='*60}")
    print(f"📋 Procesando fila {fila_num}: {datos['nombre_proveedor']} - {datos['detalle']}")
    print(f"{'='*60}")

    monto_neto = str(datos["neto"]).replace("$", "").replace(".", "").strip()
    monto_exento = str(datos["exento"]).replace("$", "").replace(".", "").strip()

    ocs_generadas = []

    # 1. Procesar OC para NETO
    if monto_neto and monto_neto != "0":
        num_oc = procesar_una_oc(page, datos, es_exento=False)
        if num_oc != "ERROR":
            ocs_generadas.append(num_oc)

    # 2. Procesar OC para EXENTO
    if monto_exento and monto_exento != "0":
        num_oc = procesar_una_oc(page, datos, es_exento=True)
        if num_oc != "ERROR":
            ocs_generadas.append(num_oc)

    # Combinamos para guardarlo en la hoja de excel
    numeros_str = ", ".join(ocs_generadas) if ocs_generadas else "ERROR"

    # --- Paso 10: Actualizar Google Sheet ---
    marcar_realizada(worksheet, fila_num, numeros_str)

    print(f"\n   ✅ Fila {fila_num} procesada con éxito. Solicitudes: {numeros_str}")
    return numeros_str


def main():
    """
    Función principal que orquesta todo el proceso de carga masiva.
    
    Maneja errores por fila: si una fila falla, registra el error
    y continúa con la siguiente para no perder tiempo en las demás.
    """
    print("=" * 60)
    print("🤖 RPA de Carga Masiva de OC — Coupa + Google Sheets")
    print("=" * 60)

    # =============================================
    # FASE 1: Conectar a Google Sheets
    # =============================================
    print("\n📊 Fase 1: Conectando a Google Sheets...")
    try:
        worksheet = conectar_sheets()
    except Exception as e:
        print(f"❌ Error conectando a Google Sheets: {e}")
        print("   Verifica: SHEET_ID en config.py, token.json, permisos del Sheet.")
        sys.exit(1)

    # =============================================
    # FASE 2: Obtener filas pendientes
    # =============================================
    print("\n📋 Fase 2: Leyendo filas pendientes...")
    filas = obtener_filas_pendientes(worksheet)

    if not filas:
        print("ℹ️ No hay filas pendientes (todas tienen REALIZADA = True).")
        print("   Agrega filas con REALIZADA = False en el Sheet para procesarlas.")
        sys.exit(0)

    print(f"\n📊 Se procesarán {len(filas)} OC(s):")
    for f in filas:
        print(f"   Fila {f['fila']}: {f['nombre_proveedor']} | {f['detalle']} | ${f['neto']}")

    # =============================================
    # FASE 3: Iniciar sesión en Coupa
    # =============================================
    print("\n🔐 Fase 3: Iniciando sesión en Coupa...")
    with sync_playwright() as playwright:
        try:
            browser, context, page = iniciar_sesion(playwright)
        except Exception as e:
            print(f"❌ Error iniciando sesión en Coupa: {e}")
            traceback.print_exc()
            sys.exit(1)

        # =============================================
        # FASE 4: Procesar cada fila
        # =============================================
        print(f"\n🚀 Fase 4: Procesando {len(filas)} OC(s)...")
        exitosas = 0
        errores = []

        for i, datos in enumerate(filas, start=1):
            print(f"\n{'─'*60}")
            print(f"🔄 Progreso: {i}/{len(filas)}")
            print(f"{'─'*60}")

            try:
                procesar_fila(page, worksheet, datos)
                exitosas += 1
            except Exception as e:
                error_msg = f"Fila {datos['fila']}: {e}"
                errores.append(error_msg)
                print(f"\n❌ Error procesando fila {datos['fila']}: {e}")
                traceback.print_exc()
                print("   ⏭️ Continuando con la siguiente fila...")

                # Intentar volver al inicio de Coupa para la siguiente iteración
                try:
                    page.goto("https://natura.coupahost.com/user/home", timeout=30000)
                    page.wait_for_load_state("networkidle", timeout=30000)
                except Exception:
                    print("   ⚠️ No se pudo volver al inicio. "
                          "Intentando re-crear contexto...")
                    try:
                        context.close()
                        context = browser.new_context(
                            storage_state="credentials/auth.json"
                        )
                        page = context.new_page()
                    except Exception:
                        print("   ❌ Error fatal re-creando contexto. Abortando.")
                        break

        # =============================================
        # FASE 5: Resumen final
        # =============================================
        print("\n" + "=" * 60)
        print("📊 RESUMEN DE EJECUCIÓN")
        print("=" * 60)
        print(f"   ✅ Exitosas: {exitosas}/{len(filas)}")
        print(f"   ❌ Errores:  {len(errores)}/{len(filas)}")

        if errores:
            print("\n   Detalle de errores:")
            for err in errores:
                print(f"      • {err}")

        print("\n🏁 Proceso finalizado.")

        # Cerrar navegador
        context.close()
        browser.close()


if __name__ == "__main__":
    main()
