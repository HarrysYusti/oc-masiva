import os
import json # Necesitamos json para guardar el token
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow

# --- Configuración de Archivos y Scopes ---

CLIENT_SECRET_FILE = r'G:\My Drive\Github-Natura\pruebas_locales\envio_correos\client_secret_750447830718-ovpklqnoah5s7fjprvj3kr9girgj4c9f.apps.googleusercontent.com.json' 
TOKEN_FILE = 'token.json' 

# SCOPES: Permisos full para drive y gmail. Editar scopes de ser necesario
SCOPES = [
    'https://mail.google.com/', 
    'https://www.googleapis.com/auth/drive'         
]
# ------------------------------------------

def generate_readable_token():
    """
    Gestiona el flujo de autenticación y guarda las credenciales en token.json 
    en un formato JSON legible (texto).
    """
    creds = None
    
    # 1. Chequeo inicial (solo si el token.json EXISTE y es JSON, lo cargaremos)
    # Si intentamos cargar el token binario anterior, fallará aquí. 
    # Por ahora, es mejor asumir que vamos a generar uno nuevo.
    
    # 2. Iniciar el flujo de autorización
    if not creds or not creds.valid:
        
        # Eliminamos cualquier token antiguo para asegurar el nuevo flujo
        if os.path.exists(TOKEN_FILE):
             os.remove(TOKEN_FILE)
             print(f"⚠️ Eliminando el token binario anterior para generar uno legible.")

        print("🚀 Iniciando flujo de autorización interactivo. ¡Atención a tu navegador!")
        
        flow = InstalledAppFlow.from_client_secrets_file(
            CLIENT_SECRET_FILE, SCOPES)
        creds = flow.run_local_server(port=0)

        # 3. Guardar el token como JSON (TEXTO)
        print(f"💾 Guardando nuevo token en '{TOKEN_FILE}' en formato JSON legible.")
        
        # Usamos el método to_json() de las credenciales
        token_json_data = creds.to_json()
        
        with open(TOKEN_FILE, 'w') as token: # Nota el modo 'w' para escritura de texto
            token.write(token_json_data)
            
    print("\n✨ Proceso de generación de token completado.")
    print(f"El archivo '{TOKEN_FILE}' es ahora legible y multi-scope.")
    return creds

if __name__ == '__main__':
    generate_readable_token()