# ============================================================================
# coupa_actions.py — Funciones de automatización en Coupa
# ============================================================================
# Cada función encapsula una acción atómica en la interfaz de Coupa.
# Usa selectores robustos (roles, atributos parciales) para resistir
# cambios en los IDs dinámicos que genera Coupa entre sesiones.
# ============================================================================

import re
import time
from playwright.sync_api import Page, expect

from config import (
    COUPA_HOME_URL,
    PLANES_DE_PAGO,
    TIMEOUT_SELECTOR,
    TIMEOUT_CORTO,
    TIMEOUT_NAVEGACION,
)


# ============================================================================
#  1. BUSCAR Y COPIAR SOLICITUD BASE
# ============================================================================

def buscar_y_copiar_solicitud(page: Page, numero_factura: str):
    """
    Navega a la actividad reciente, busca una solicitud por número de factura
    y la copia como base para una nueva solicitud.
    
    Flujo en Coupa:
    1. Click en menú "Inicio"
    2. Click en "Ver todos (Actividad reciente)"
    3. Buscar por número de factura
    4. Click en "Copiar solicitud n.°"
    
    Args:
        page: página de Playwright en Coupa.
        numero_factura: número para buscar en la lista de solicitudes.
    """
    print(f"   🔍 Buscando solicitud base: {numero_factura}...")

    # Navegar al inicio
    page.goto(COUPA_HOME_URL, timeout=TIMEOUT_NAVEGACION)
    page.wait_for_load_state("networkidle", timeout=TIMEOUT_NAVEGACION)

    # Abrir actividad reciente
    page.get_by_role("menuitem", name="Inicio").click()
    page.get_by_role("link", name="Ver todos (Actividad reciente").click()
    page.wait_for_load_state("networkidle", timeout=TIMEOUT_NAVEGACION)

    # Buscar la solicitud
    campo_busqueda = page.get_by_role("textbox", name="Buscar")
    campo_busqueda.click()
    campo_busqueda.fill(str(numero_factura))
    campo_busqueda.press("Enter")

    # Click en botón de búsqueda como refuerzo
    boton_buscar = page.get_by_role("button", name="Buscar")
    if boton_buscar.is_visible(timeout=TIMEOUT_CORTO):
        boton_buscar.click()

    page.wait_for_load_state("networkidle", timeout=TIMEOUT_NAVEGACION)

    # Copiar la solicitud encontrada (usando .first porque a veces la búsqeda trae múltiples si el número de factura coincide parcialmente)
    page.get_by_role("button", name="Copiar solicitud n.º").first.click()
    page.wait_for_load_state("networkidle", timeout=TIMEOUT_NAVEGACION)

    print(f"   ✅ Solicitud base copiada.")


# ============================================================================
#  2. LLENAR JUSTIFICACIÓN
# ============================================================================

def llenar_justificacion(page: Page, detalle: str, nombre_tienda: str):
    """
    Llena el campo de justificación combinando DETALLE + NOMBRE_TIENDA.
    
    Ejemplo resultado: "ARRIENDO Aeropuerto"
    
    Args:
        page: página de Playwright en la solicitud.
        detalle: texto del tipo de servicio (columna DETALLE, ej: "ARRIENDO").
        nombre_tienda: nombre de la tienda (columna NOMBRE TIENDA, ej: "Aeropuerto").
    """
    justificacion = f"{detalle} {nombre_tienda}".strip()
    print(f"   📝 Llenando justificación: '{justificacion}'")
    campo = page.get_by_role("textbox", name="Justificación")
    campo.click()
    # Limpiar contenido anterior (la copia puede traer datos previos)
    campo.fill("")
    campo.fill(justificacion)


# ============================================================================
#  3. ELIMINAR ADJUNTO EXISTENTE
# ============================================================================

def eliminar_adjunto(page: Page):
    """
    Elimina el adjunto que pueda venir de la solicitud copiada.
    Solo actúa si el botón de eliminar adjunto está visible.
    
    Args:
        page: página de Playwright en la solicitud.
    """
    boton_eliminar = page.get_by_role("button", name="Eliminar adjunto")
    try:
        if boton_eliminar.is_visible(timeout=TIMEOUT_CORTO):
            boton_eliminar.click()
            print("   🗑️ Adjunto eliminado.")
        else:
            print("   ℹ️ No hay adjunto para eliminar.")
    except Exception:
        print("   ℹ️ No se encontró botón de eliminar adjunto (OK, continuando).")


# ============================================================================
#  4. SELECCIONAR FECHAS DE SERVICIO
# ============================================================================

def seleccionar_fechas(page: Page, fecha_inicio: str, fecha_fin: str):
    """
    Selecciona las fechas de inicio y fin del servicio en los datepickers.
    
    Nota: Los datepickers de Coupa son complejos. Esta función limpia el
    campo y escribe la fecha directamente en formato input, simulando la
    interacción del usuario.
    
    Args:
        page: página de Playwright en la solicitud.
        fecha_inicio: fecha en formato del Sheet (ej: "03/02/2026" o "2026-02-03").
        fecha_fin: fecha en formato del Sheet.
    """
    print(f"   📅 Configurando fechas: {fecha_inicio} → {fecha_fin}")

    # --- Fecha inicio del servicio ---
    # Intentar con el selector por nombre de botón que abre el datepicker
    campo_inicio = page.locator("input[name*='need_by_date'], input[id*='need_by_date']").first
    if campo_inicio.is_visible(timeout=TIMEOUT_CORTO):
        campo_inicio.click()
        campo_inicio.fill("")
        campo_inicio.fill(fecha_inicio)
        campo_inicio.press("Escape")
    else:
        # Fallback: usar el botón del datepicker
        print("   ⚠️ Campo de fecha inicio no encontrado por input, usando datepicker...")
        boton_inicio = page.get_by_role("button", name="Início del servício o entrega")
        if boton_inicio.is_visible(timeout=TIMEOUT_CORTO):
            boton_inicio.click()
            # Se necesitará navegar al mes/día correcto manualmente
            # Por ahora, cerrar con Escape
            page.keyboard.press("Escape")

    # --- Fecha fin del servicio ---
    campo_fin = page.locator("input[name*='delivery_date'], input[id*='delivery_date']").first
    if campo_fin.is_visible(timeout=TIMEOUT_CORTO):
        campo_fin.click()
        campo_fin.fill("")
        campo_fin.fill(fecha_fin)
        campo_fin.press("Escape")
    else:
        print("   ⚠️ Campo de fecha fin no encontrado por input, usando datepicker...")
        boton_fin = page.get_by_role("button", name="Final del servício o entrega")
        if boton_fin.is_visible(timeout=TIMEOUT_CORTO):
            boton_fin.click()
            page.keyboard.press("Escape")


# ============================================================================
#  5. EDITAR LÍNEA DE SOLICITUD (Proveedor, Commodity, Precio, Plazo)
# ============================================================================

def editar_linea_solicitud(page: Page, datos: dict, es_exento: bool = False):
    """
    Abre la edición de la línea de solicitud y llena los campos principales.
    
    Usa selectores robustos para campos con IDs dinámicos:
    - Proveedor: [id^="supplierSearchAutocomplete"] en vez de ID exacto
    - Commodity: get_by_role("textbox", name="Commodity")
    - Precio: get_by_role("textbox", name="Precio unitario")
    
    Args:
        page: página de Playwright en la solicitud.
        datos: dict con claves: nombre_proveedor, commodity, neto/exento, plan_de_pago.
        es_exento: bandera que indica si procesar la línea como exenta.
    """
    print("   ✏️ Editando línea de solicitud...")

    # Abrir editor de línea
    page.get_by_role("button", name="Editar línea de solicitud").click()
    page.wait_for_load_state("networkidle", timeout=TIMEOUT_NAVEGACION)

    # Esperar a que el formulario de edición esté visible
    time.sleep(2)  # Pequeña pausa para estabilidad del DOM dinámico

    # --- 5.1 PREPARAR ARTÍCULO ---
    _llenar_articulo(page, datos["detalle"], datos["nombre_tienda"])

    # --- 5.2 PROVEEDOR ---
    _seleccionar_proveedor(page, datos["cod_sap_proveedor"])

    # --- 5.3 COMMODITY ---
    _seleccionar_commodity(page, datos["commodity"])

    # --- 5.4 PRECIO UNITARIO ---
    monto = datos["exento"] if es_exento else datos["neto"]
    _llenar_precio(page, monto)

    # --- 5.4 PLAZO DE PAGO ---
    _seleccionar_plazo_pago(page, datos["plan_de_pago"])

    # --- 5.5 FECHA LÍMITE (Hoy + 30 días) ---
    import datetime
    fecha_limite = (datetime.datetime.now() + datetime.timedelta(days=30)).strftime("%d/%m/%y")
    _seleccionar_fecha_limite(page, fecha_limite)

    # --- 5.6 IMPUESTO ---
    _seleccionar_impuesto(page, es_exento)

    print("   ✅ Línea de solicitud editada.")


def _llenar_articulo(page: Page, detalle: str, nombre_tienda: str):
    """
    Llena el campo 'Artículo' en la línea de solicitud.
    """
    texto = f"{detalle} {nombre_tienda}".strip()
    print(f"      📄 Llenando Artículo: {texto}")
    try:
        # Usamos locators genéricos para descripción en Coupa
        campo = page.locator("input[name*='description'], input[id*='description']").first
        if not campo.is_visible(timeout=TIMEOUT_CORTO):
            # Fallback
            campo = page.locator(".line-description input[type='text']").first
            
        if campo.is_visible(timeout=TIMEOUT_CORTO):
            campo.click()
            campo.press("Control+a")
            campo.press("Backspace")
            campo.fill(texto)
    except Exception as e:
        print(f"      ⚠️ No se pudo ubicar el campo Artículo: {e}")


def _seleccionar_proveedor(page: Page, cod_sap_proveedor: str):
    """
    Busca y selecciona el proveedor tipeando el código, quitando y poniendo 
    el último dígito para forzar la carga AJAX de Coupa.
    """
    print(f"      🏢 Seleccionando proveedor por COD SAP: {cod_sap_proveedor}")

    campo = page.locator("input[id^='supplierSearchAutocomplete']").first
    campo.click()
    campo.fill("")
    
    # Lógica de "despertar" el autocompletado
    codigo_inicio = str(cod_sap_proveedor)[:-1]
    ultimo_digito = str(cod_sap_proveedor)[-1]

    # Llenamos el inicio
    campo.fill(codigo_inicio)
    time.sleep(1)
    # Tipeamos el último dígito con retraso para disparar la validación
    campo.press_sequentially(ultimo_digito, delay=200)

    # Esperar a que la sugerencia aparezca desde el servidor
    time.sleep(2.5)

    # Navegar hacia abajo y seleccionar (mucho más seguro que hacer clic en elementos dinámicos)
    campo.press("ArrowDown")
    time.sleep(0.5)
    campo.press("Enter")
    
    print("      ✅ Proveedor seleccionado.")


def _seleccionar_commodity(page: Page, commodity: str):
    """
    Selecciona el código de commodity en el campo autocomplete.
    
    Args:
        page: página de Playwright.
        commodity: código de commodity (ej: "50302002").
    """
    print(f"      📦 Seleccionando commodity: {commodity}")

    campo = page.get_by_role("textbox", name="Commodity")
    campo.click()
    campo.fill("")
    campo.fill(str(commodity))

    # Esperar a que aparezca la sugerencia y seleccionarla
    time.sleep(2)

    # Buscar la opción en el autocomplete usando el código
    opciones = page.locator(".ui-autocomplete .ui-menu-item")
    try:
        opciones.first.click(timeout=TIMEOUT_CORTO)
    except Exception:
        # Intentar con get_by_role option
        opcion = page.get_by_role("option", name=re.compile(re.escape(str(commodity))))
        try:
            opcion.first.click(timeout=TIMEOUT_CORTO)
        except Exception:
            print(f"      ⚠️ No se encontró el commodity '{commodity}'. Verificar código.")


def _llenar_precio(page: Page, precio: str):
    """
    Llena el campo de precio unitario.
    
    Args:
        page: página de Playwright.
        precio: monto como string (ej: "4625725").
    """
    print(f"      💰 Estableciendo precio unitario: {precio}")

    campo = page.get_by_role("textbox", name="Precio unitario")
    campo.click()
    # Seleccionar todo y reemplazar
    campo.press("Control+a")
    campo.fill(str(precio))


def _seleccionar_plazo_pago(page: Page, plan_pago: str):
    """
    Selecciona el plazo de pago buscando por texto parcial.
    
    El campo es un dropdown/autocomplete. Se escribe el código del plan
    (ej: "CL15") y se selecciona el primer resultado que aparezca.
    No es necesario el nombre completo, con el código parcial
    debería aparecer solo 1 opción.
    
    Args:
        page: página de Playwright.
        plan_pago: código parcial del plan de pago (ej: "CL15").
    """
    print(f"      ⏰ Seleccionando plazo de pago: {plan_pago}")

    try:
        # Intentar primero como dropdown estandard (usando value numerico seguro codegen="653", etc)
        select_plazo = page.locator("select[id^='payment_term']")
        if select_plazo.is_visible():
            # Si el plan no está en el dicc, intenta buscar por string
            val_seguro = PLANES_DE_PAGO.get(plan_pago)
            if val_seguro:
                select_plazo.select_option(value=val_seguro)
            else:
                select_plazo.select_option(label=re.compile(re.escape(plan_pago), re.IGNORECASE))
            print(f"      ✅ Plazo de pago seleccionado.")
            return
    except Exception:
        pass

    # Fallback: si es un autocomplete en vez de select
        try:
            campo = page.locator("[id*='payment_term'], [name*='payment_term']").first
            campo.click()
            campo.fill(str(plan_pago))
            time.sleep(2)
            # Seleccionar primer resultado
            primer_resultado = page.locator(".ui-autocomplete .ui-menu-item").first
            if primer_resultado.is_visible(timeout=TIMEOUT_CORTO):
                primer_resultado.click()
            else:
                print(f"      ⚠️ No se encontró plazo de pago '{plan_pago}'.")
        except Exception as e:
            print(f"      ⚠️ Error seleccionando plazo de pago: {e}")


def _seleccionar_fecha_limite(page: Page, fecha_vencimiento: str):
    """
    Establece la fecha límite en el formulario de edición de línea.
    
    Args:
        page: página de Playwright.
        fecha_vencimiento: fecha en formato del Sheet.
    """
    print(f"      📅 Fecha límite: {fecha_vencimiento}")

    # Buscar el input de fecha límite dentro del formulario de edición
    campo_fecha = page.locator("input[name*='need_by_date']").first
    try:
        if campo_fecha.is_visible(timeout=TIMEOUT_CORTO):
            campo_fecha.click()
            campo_fecha.fill("")
            campo_fecha.fill(fecha_vencimiento)
            campo_fecha.press("Tab")
    except Exception:
        print("      ℹ️ Campo de fecha límite no encontrado, continuando...")


def _seleccionar_impuesto(page: Page, es_exento: bool):
    """
    Selecciona el tipo de impuesto (IVA 19% o Material sin impuesto) basándose en el codegen.
    Al finalizar, hace clic en el botón 'Guardar' de la caja de edición de línea.
    """
    desc_tipo = "Material sin impuesto (C0)" if es_exento else "IVA 19%"
    print(f"      🧾 Configurando impuesto para {desc_tipo}...")

    try:
        # Apuntar a la celda específica como hace el codegen
        celda_linea = page.get_by_role("cell", name=re.compile("Tipo de línea", re.IGNORECASE))
        
        # Borrar selección previa si existe
        boton_borrar = celda_linea.get_by_label("Borrar selección")
        if boton_borrar.is_visible(timeout=2000):
            boton_borrar.click()
            time.sleep(1)

        # Clic en "Seleccionar"
        page.locator("a").filter(has_text=re.compile(r"^Seleccionar$")).last.click()
        time.sleep(1)

        # Seleccionar la opción correcta
        if es_exento:
            page.get_by_role("option", name=re.compile("Material sin impuesto", re.IGNORECASE)).click()
        else:
            page.get_by_role("option", name=re.compile("IVA 19%|Impuesto Valor", re.IGNORECASE)).click()
            
        print(f"      ✅ Impuesto '{desc_tipo}' aplicado.")
        
        # --- CLIC EN GUARDAR LA CAJA ---
        print("      💾 Guardando formulario de la línea...")
        page.locator("#edit-line").get_by_role("button", name="Guardar").click(timeout=TIMEOUT_CORTO)
        page.wait_for_load_state("networkidle", timeout=TIMEOUT_NAVEGACION)
        time.sleep(2) # Pausa breve para asegurar que la caja se cierre por completo
        print("      ✅ Línea guardada exitosamente.")

    except Exception as e:
        print(f"      ⚠️ Error al seleccionar el impuesto o guardar la línea: {e}")


# ============================================================================
#  6. SELECCIONAR CUENTA CONTABLE Y CENTRO DE COSTOS
# ============================================================================

def seleccionar_cuenta(page: Page, cuenta_contable: str, ceco: str):
    """
    Selecciona la cuenta contable y el centro de costos usando page.keyboard 
    para evadir los inputs dinámicos flotantes de Coupa.
    """
    print(f"   🏦 Configurando cuenta contable: {cuenta_contable}, CECO: {ceco}")

    # Abrir modal
    try:
        page.get_by_role("button", name="Elegir una cuenta").click(timeout=TIMEOUT_CORTO)
    except Exception:
        page.get_by_text(re.compile("Elegir una cuentaclose|Elegir una cuenta", re.IGNORECASE)).first.click()
    
    page.wait_for_load_state("networkidle", timeout=TIMEOUT_NAVEGACION)
    time.sleep(2)

    try:
        # =================================================================
        # 1. LLENAR CECO (Objeto Colector / Centro de Costos)
        # =================================================================
        sector_ceco = page.locator("#account_segment_2_lv_id_chosen")
        
        # Borrar si hay algo
        boton_borrar_ceco = sector_ceco.get_by_role("button", name="Borrar selección")
        if boton_borrar_ceco.is_visible(timeout=2000):
            boton_borrar_ceco.click()
            time.sleep(1)
        
        # Abrir el dropdown (esto pone el cursor a parpadear en el buscador invisible)
        sector_ceco.locator("a").filter(has_text="Seleccionar").click()
        time.sleep(1)
        
        # 🔥 TRUCO: Escribir directamente en el teclado y seleccionar
        page.keyboard.type(str(ceco), delay=100)
        time.sleep(2) # Esperar que Coupa filtre la lista
        page.keyboard.press("ArrowDown")
        time.sleep(0.5)
        page.keyboard.press("Enter")
        
        print(f"   ✅ CECO '{ceco}' tecleado y asignado.")
        time.sleep(1)

        # =================================================================
        # 2. LLENAR CUENTA MAYOR
        # =================================================================
        sector_cuenta = page.locator("#account_segment_5_lv_id_chosen")
        
        # Borrar si hay algo
        boton_borrar_cuenta = sector_cuenta.get_by_role("button", name="Borrar selección")
        if boton_borrar_cuenta.is_visible(timeout=2000):
            boton_borrar_cuenta.click()
            time.sleep(1)

        # Abrir el dropdown
        sector_cuenta.locator("a").filter(has_text="Seleccionar").click()
        time.sleep(1)
        
        # 🔥 TRUCO: Escribir directamente y seleccionar
        page.keyboard.type(str(cuenta_contable), delay=100)
        time.sleep(2)
        page.keyboard.press("ArrowDown")
        time.sleep(0.5)
        page.keyboard.press("Enter")
        
        print(f"   ✅ Cuenta Mayor '{cuenta_contable}' tecleada y asignada.")
        time.sleep(1)

        # =================================================================
        # 3. CONFIRMAR SELECCIÓN
        # =================================================================
        page.get_by_role("link", name="Elegir").first.click()
        page.wait_for_load_state("networkidle")
        print("   ✅ Selección de cuenta aplicada y modal cerrada.")

    except Exception as e:
        print(f"   ⚠️ Error seleccionando cuenta/CECO: {e}")




# ============================================================================
#  8. EXTRAER NÚMERO DE SOLICITUD
# ============================================================================

def extraer_numero_solicitud(page: Page) -> str:
    """
    Extrae el número de solicitud del encabezado de la página.
    
    El encabezado tiene un formato como: "Solicitud de compra #58744"
    Esta función extrae el número, limpiando el '#' y espacios.
    
    Usa el selector #pageHeader para obtener el texto.
    
    Args:
        page: página de Playwright en la solicitud.
    
    Returns:
        String con el número de solicitud (ej: "58744"), o "ERROR" si no se pudo extraer.
    """
    try:
        header = page.locator("#pageHeader")
        texto_header = header.inner_text(timeout=TIMEOUT_SELECTOR)

        # Extraer el número usando regex: buscar '#' seguido de dígitos
        match = re.search(r"#(\d+)", texto_header)
        if match:
            numero = match.group(1)
            print(f"   🔢 Número de solicitud extraído: {numero}")
            return numero
        else:
            print(f"   ⚠️ No se encontró número en header: '{texto_header}'")
            return "ERROR"
    except Exception as e:
        print(f"   ❌ Error extrayendo número de solicitud: {e}")
        return "ERROR"


# ============================================================================
#  9. ENVIAR PARA APROBACIÓN
# ============================================================================

def enviar_para_aprobacion(page: Page):
    """
    Click en el botón "Enviar para aprobación" para enviar la solicitud.
    
    Espera a que la página confirme el envío antes de retornar.
    
    Args:
        page: página de Playwright en la solicitud.
    """
    print("   📤 Enviando solicitud para aprobación...")

    boton = page.get_by_role("button", name="Enviar para aprobación", exact=True)
    boton.click()

    # Esperar a que se procese el envío
    page.wait_for_load_state("networkidle", timeout=TIMEOUT_NAVEGACION)
    time.sleep(3)  # Pausa adicional para confirmar

    print("   ✅ Solicitud enviada para aprobación.")


# ============================================================================
#  10. GUARDAR BORRADOR (MODO PRUEBA)
# ============================================================================

def guardar_borrador(page: Page):
    """
    Guarda la solicitud como borrador SIN enviarla para aprobación.
    
    Útil para el modo de prueba: permite verificar que todos los campos
    se llenaron correctamente antes de pasar al envío real.
    
    Args:
        page: página de Playwright en la solicitud.
    """
    print("   💾 Guardando solicitud como borrador...")

    # Buscar botón de guardar (puede ser "Guardar" o "Guardar borrador")
    boton = page.get_by_role("button", name=re.compile(r"Guardar", re.IGNORECASE))
    try:
        boton.first.click(timeout=TIMEOUT_SELECTOR)
        page.wait_for_load_state("networkidle", timeout=TIMEOUT_NAVEGACION)
        time.sleep(2)
        print("   ✅ Solicitud guardada como borrador.")
    except Exception as e:
        print(f"   ⚠️ Error al guardar borrador: {e}")
        print("   Intentando buscar otro botón de guardar...")
        # Fallback: buscar por texto exacto
        try:
            page.locator("input[value='Guardar'], button:has-text('Guardar')").first.click(
                timeout=TIMEOUT_CORTO
            )
            page.wait_for_load_state("networkidle", timeout=TIMEOUT_NAVEGACION)
            print("   ✅ Solicitud guardada (fallback).")
        except Exception:
            print("   ❌ No se pudo encontrar el botón de guardar.")
