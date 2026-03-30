# ============================================================================
# coupa_session.py — Gestión de sesión de Coupa (Login + auth.json)
# ============================================================================
# Maneja la autenticación en Coupa via Google SSO. Si existe un archivo
# auth.json con el estado de la sesión previa, lo reutiliza. Si no existe
# o la sesión expiró, ejecuta el flujo de login completo y guarda el estado.
# ============================================================================

import os
from playwright.sync_api import Playwright, Browser, BrowserContext, Page

from config import (
    CREDENTIALS_DIR, COUPA_HOME_URL, HEADLESS, SLOW_MO,
    TIMEOUT_NAVEGACION
)


def _ejecutar_login(page: Page):
    """
    Inicia el flujo de login manual.
    Abre la página de Coupa y espera a que el usuario se loguee.
    Una vez que el usuario llega al Inicio, el script continúa.
    
    Args:
        page: página de Playwright donde ejecutar el login.
    """
    print("🔐 Iniciando login manual...")
    print("   👉 Se ha abierto el navegador. Por favor, INICIA SESIÓN MANUALMENTE.")
    print("   👉 Tienes 5 minutos. El script continuará automáticamente cuando veas el inicio de Coupa.")

    # Navegar a la página raíz de Coupa (redirige al login SSO de la empresa)
    page.goto("https://natura.coupahost.com", timeout=TIMEOUT_NAVEGACION)

    # Esperar hasta que un elemento clave de la home de Coupa esté visible (indicando login exitoso)
    # Se da un timeout muy largo (5 minutos = 300,000 ms) para que el usuario escriba sus datos
    try:
        page.get_by_role("menuitem", name="Inicio").wait_for(state="visible", timeout=300000)
        print("   ✅ Login manual detectado exitosamente. Continuando...")
    except Exception as e:
        print("   ❌ Error: Se agotó el tiempo de espera para el login manual o cerraste la ventana.")
        raise e


def _validar_sesion(page: Page) -> bool:
    """
    Verifica si la sesión actual es válida navegando a Coupa Home.
    
    Si la sesión expiró o no existe, Google SSO redirigirá a una página de login.
    
    Args:
        page: página con contexto de sesión cargado.
    
    Returns:
        True si la sesión es válida (menu Inicio visible), False si pide login.
    """
    try:
        page.goto(COUPA_HOME_URL, timeout=TIMEOUT_NAVEGACION)
        page.wait_for_load_state("networkidle", timeout=TIMEOUT_NAVEGACION)
        
        # En vez de comprobar la URL que a veces falla en SSO, 
        # esperamos a ver si carga el menú Inicio en unos pocos segundos.
        # Si sale el menú, estamos logueados.
        es_valido = page.get_by_role("menuitem", name="Inicio").is_visible()
        if not es_valido:
            # Esperar máximo 5 segundos para ver si aparece el menú antes de declararla inválida
            try:
                page.get_by_role("menuitem", name="Inicio").wait_for(state="visible", timeout=5000)
                es_valido = True
            except Exception:
                pass
        return es_valido
    except Exception:
        return False


def iniciar_sesion(playwright: Playwright) -> tuple[BrowserContext, BrowserContext, Page]:
    """
    Inicia una sesión persistente en Coupa (usando un perfil real de Chrome).
    Esto es más efectivo que auth.json porque guarda todo (Cookies, LocalStorage, 
    IndexedDB de Google SSO) entre ejecuciones.
    
    Flujo:
    1. Lanza el navegador usando el perfil de usuario en credentials/chrome_profile.
    2. Valida si la sesión en Coupa sigue activa.
       - Si es válida → listo
       - Si no → ejecuta login manual para guardar el estado.
    
    Args:
        playwright: instancia de Playwright.
    
    Returns:
        Tupla (contexto_browser, contexto, page) listos para automatizar.
    """
    # Usar un directorio de perfil persistente como si fuera un navegador normal
    perfil_dir = os.path.join(CREDENTIALS_DIR, "chrome_profile")
    os.makedirs(perfil_dir, exist_ok=True)

    print("🔑 Iniciando navegador con perfil de sesión persistente...")
    context = playwright.chromium.launch_persistent_context(
        user_data_dir=perfil_dir,
        headless=HEADLESS,
        slow_mo=SLOW_MO,
        viewport={"width": 1280, "height": 720}
    )

    # Una sesión persistente ya tiene una página inicial creada
    page = context.pages[0] if context.pages else context.new_page()

    if _validar_sesion(page):
        print("✅ Sesión persistente reutilizada exitosamente.")
    else:
        print("⚠️ Sesión expirada o es primera vez. Iniciando login manual...")
        _ejecutar_login(page)
        # El contexto persistente guarda las cookies automáticamente a disco

    # Devolvemos el context en la posición de "browser" también para mantener
    # la compatibilidad con el código de main.py (que hará browser.close())
    return context, context, page
