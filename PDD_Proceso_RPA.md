# Documentación Integral del Proceso RPA: Carga Masiva de OCs en Coupa de Natura

Este documento detalla a nivel funcional y técnico todo el funcionamiento, la arquitectura y los requisitos del robot (RPA) creado para la automatización masiva de Órdenes de Compra (OCs) en la plataforma corporativa Coupa usando Python y Playwright. Su objetivo es que tanto perfiles técnicos como principiantes puedan entender, instalar, y escalar el código.

---

## 1. Introducción y Alcance
El RPA extrae información tabulada de un archivo de Google Sheets alimentado por el equipo operativo. Para evitar la enorme carga manual (y mitigar errores humanos) de ingresar factura por factura, el script entra a Coupa de Natura, realiza un duplicado de un carrito o solicitud de compra anterior ("Solicitud Base"), lo "limpia" borrando la información adjunta, y procede a crear entre 1 y 2 carritos nuevos para cada fila del Excel (generando OCs independientes para montos `NETO` y montos `EXENTOS`). Toda cuenta contable, CECO, y código SAP se reajusta automáticamente antes de guardar el borrador en el portal y marcar el ciclo como `REALIZADO` devolviendo el número de OC de vuelta a Google Sheets.

---

## 2. Requisitos Previos e Instalación (Setup)
Para ejecutar este proyecto en cualquier entorno (ya sea técnico o de un analista de negocio), se deben tener instaladas las siguientes herramientas:

### Prerrequisitos de Software:
1. **Python 3.10+** (Asegurarse de marcar "Add Python to PATH" durante la instalación).
2. **Terminal/Línea de Comandos:** Símbolo del sistema, PowerShell o la terminal de VSCode.
3. El archivo local de credenciales de Google: `token/credenciales.json` proveniente de Google Cloud Console (usado para la API de Sheets).

### Librerías Requeridas (Python Libraries):
Ve a tu terminal dentro de la carpeta del proyecto y ejecuta estos comandos:

```bash
# Instalación de las librerías base para controlar integraciones y navegadores
pip install playwright google-api-python-client google-auth-httplib2 google-auth-oauthlib 

# Instalación e inicialización de los navegadores de Playwright
playwright install
```

---

## 3. Estructura del Código (Arquitectura)
El código sigue las mejores prácticas y divide todo el trabajo masivo en módulos independientes funcionales:

* **`config.py`**: El cerebro de constantes. Guarda las URLs, los IDs del documento de Google Sheets específico, constantes de tiempos dinámicos de espera (`TIMEOUT_CORTO`, `TIMEOUT_SELECTOR`), y el diccionario del mapeo para saber exactamente qué número de columna contiene los datos (Ej: `DETALLE = 8`).
* **`google_sheets.py`**: Encargado puro de comunicarse con Google. Tiene métodos para hacer ping, solicitar acceso leyendo tu `credenciales.json`, extraer todas las filas cuya columna final diga `FALSE`, y otra función para devolver resultados (ej. enviar el #58793 de OC creada).
* **`coupa_session.py`**: Maneja el inicio al portal usando Playwright pero cargando la carpeta secreta `credentials/chrome_profile`. Si el token interno de sesión (SSO de Microsoft/Natura) caduca, fuerza al analista a meter su contraseña manualmente una única vez, y recuerda esto para futuras repeticiones.
* **`coupa_actions.py`**: La librería madre de Coupa. Contiene las "acciones atómicas" como `buscar_y_copiar_solicitud()`, `seleccionar_cuenta()`, `_seleccionar_impuesto()`, que interactúan físicamente (click y tipeo) con los cuadros de Coupa.
* **`main.py` y `main_test.py`**: Son los controladores principales. `main_test.py` se encarga de probar **apenas una sola fila del Google Sheets**, ideal para probar selectores nuevos y guardar un borrador; mientras que `main.py` es el orquestador real que ciclará todo el Excel uno a uno, ejecutando el RPA y enviando a aprobaciones masivamente en bucle.

---

## 4. Diagrama Fundamental: El Paso a Paso Lógico y Programático

A continuación la narrativa enlazada entre los pasos lógicos de cómo lo vería un humano, y su homólogo a nivel de código (`main.py` llamando a `coupa_actions.py`).

### Paso 1: Localizar la tarea (Sheets)
* **El robot:** Invoca `obtener_filas_pendientes()`.
* **Programación:** Recorre el diccionario extraído del Sheet, si la fila en la tupla [23] (`REALIZADA`) dice `FALSE`, guarda los datos (CECO, Tienda, Monto, Proveedor, Código de Factura) dentro de un gran objeto llamado `datos` que luego inyectará en las funciones.
* **Manejo Exento/Neto:** `main.py` pregunta si `datos["neto"]` contiene plata. Si es así, lanza una ejecución pasándole el estado `es_exento=False`. Cuando finaliza, el ciclo vuelve a preguntar si la misma fila trae registro en `datos["exento"]`, de ser así, lanza una **inmediatamente segunda ejecución paralela para la misma factura**, pero pasándole el parámetro `es_exento=True`.

### Paso 2: Copia e Inicialización de Carrito de Compra 
* **El robot:** Navega a la web predeterminada de "Actividad Reciente", busca en lo alto la OC antigua que sirve de clon, descrita en la columna `X` ("Solicitud Base"), la abre y copia.
* **Programación:** `buscar_y_copiar_solicitud(page, datos["solicitud_base"])` usa manipuladores por ID robustos como `[id^='something']` para pulsar el botón clonar. Luego salta a `eliminar_adjunto(page)` que ubica una clase CSS de basurero `i.icon-remove` para dejar la solicitud prístina.

### Paso 3: Relleno de Fechas y Textos descriptivos (Cabecera)
* **El robot:** Modifica el título de la requisición copiando de forma combinada "Detalle + Almacén Tienda / Aeropuerto" en justificación. Adicionalmente, inserta la fecha tecleando por fuerza bruta sin usar el calendario emergente.
* **Programación:** Pasa la etiqueta a `llenar_justificacion` e inserta los strings en el `<textarea>`. La fecha de `Need By` se calcula sumando 30 días usando `datetime` interno a `datetime.now()` e insertándola.

### Paso 4: Relleno de las Cajas con Ajax (El núcleo)
Para cada celda de datos que funciona en base a autocompletado inteligente asincrónico manejado por el servidor web Coupa (Proveedor, Cuenta, CECO):
* **El robot:** No envía un texto "bloque", porque los Javascripts en la web no logran reaccionar. El robot tipearía rápido el código parcial, retrasaría unas docenas de milisegundos su movimiento de "dedos", presionaría un caracter final, y emitiría la orden de la Tecla Bajar (Flecha abajo) terminando con Enter (Return).
* **Programación:** Esta es la barrera más desafiante. Se soluciona programáticamente accediendo al motor `keyboard` del navegador por sobre los roles estándar, ejemplo claro en `coupa_actions.py`:
```python
page.keyboard.type(str(ceco), delay=100) # Tecleado lento estilo humano de 0.1s/char
time.sleep(2) # Espera a la API de validación interna de Coupa
page.keyboard.press("ArrowDown") # Se fuerza mover a la clase css interna `.ui-menu-item`
page.keyboard.press("Enter")
```

### Paso 5: Selección de Impuesto Dinámico
* **El robot:** Dependiendo si es la ronda NETO o EXENTO, el pop-up de IVA requiere la elección de "IVA 19%" o "Material sin impuesto".
* **Programación:** Invoca `_seleccionar_impuesto(page, es_exento)`. Se usa la API de Playwright (por roles de accesibilidad) la cual no se rige atada a IDs mutantes (ej. `#select2_choice`). El bot en cambio busca a un humano y se guía por las letras. Busca el campo flotante al lado de *"Tipo de línea Artículo SaaS"*, presiona borrar y hace tap en la opción `IVA 19%` usando literales como Regex `re.compile("Material sin impuesto", re.IGNORECASE)`.

### Paso 6: Extracción y Guardado
* **El robot:** Da clic en el botón guardar inferior general y lee un número oculto que arroja la ventana en la esquina superior izquierda. 
* **Programación:** `page.locator("#pageHeader").inner_text()` usa regex `re.search(r"#(\d+)", texto_header)` para recuperar estrictamente los dígitos (ej. `53896`). Posteriormente, invoca al script `google_sheets._actualizar_linea_` y pega el valor en las posiciones indicadas de forma bidireccional, cerrando el bucle.


---

## 5. Escalado: Cómo extender el Proyecto (Para Principiantes/Técnicos)

Si el negocio muta y requiere agregar un parámetro nuevo (por ejemplo, incluir un campo obligatorio que se llama "Subnúmero de Activo Fijo"), Playwright tiene mecanismos sencillos de aprender, inclusive sin saber programar HTML.

A través del archivo auxiliar `lanzar_codegen.bat` ya entregado, Coupa emitirá un sistema para grabar la pantalla. Todo paso que des como humano creará la automatización exacta de sintaxis en un recuadro oscuro para que lo copies y pegues directamente a `coupa_actions.py`.

### 5.1 Guía para agregar un campo de texto extra en Playwright
Imagina que la compañía agrega el campo genérico `[Comprador Auxiliar]`:
1. Asegúrate de añadir en la parte superior del `google_sheets.py` el índice de la columna en Excel: `COMPRADOR = 24`.
2. Actualiza la función en `google_sheets` para que rescate su valor: `"comprador": fila[Col.COMPRADOR - 1]`.
3. Para incorporarlo en Coupa, abre el archivo `.bat` local.
4. En Coupa haz "clic" en el campo y copia la sentencia que da el Codegen oscuro. 
5. Usualmente el Codegen te dará algo como esto: `page.get_by_role("textbox", name="Comprador Auxiliar").click()`.
6. En `coupa_actions.py` creas una mini función llamada `_agregar_comprador_auxiliar(page, datos["comprador"])` y usas la función `.fill(texto)` del grabador.

### 5.2 Diferencias en Localizadores (Locators) al lidiar con Plataformas Inestables
Coupa usa la tecnología `Select2` la cual hace que la web cambie sus "IDs" y estructuras en tiempo real por cada actualización de mes. Se recomienda entender las tres jerarquías para localizar campos en interfaces volátiles:

* **Nivel 1 (Ideal y Fiable): Selección por Semántica y Rol Humano**
  * `page.get_by_role("button", name="Elegir una cuenta")` o `page.get_by_text("Mi campo")`. Esto imita cómo una persona invidente interactuaría. Jamás se romperá si el diseñador web le cambia las formas geométricas a los cuadros.
  * *Uso en el RPA:* Guardar, Cancelar, Seleccionar Impuesto, Nombres de Formularios.

* **Nivel 2 (Fuerte pero Rígido): Selección por ID de Cascarón Fijo**
  * Los selectores CSS y los XPath de herencia directa.
  * Ej: `page.locator("a.search-icon").first` o `page.locator("#account_segment_2_lv_id_chosen")`.
  * *Uso en el RPA:* Los casilleros de selección de Cuentas Contables y CECO que Coupa etiqueta estrictamente segmentados con la etiqueta 'account_segment_n_chosen'.

* **Nivel 3 (Evasivo - Último Recurso): Interacción con el Teclado Pura**
  * Los inputs dinámicos en React/Angular de auto-completado, como el *"Proveedor COD SAP"*. Aquí los campos estallan porque no puedes esperar que un *click()* garantice que el contenido cruzó por red.
  * Es el truco supremo:
    ```python
    campo = page.locator("[id^='supplierSearchAutocomplete']") # id^ ignora el sufijo mutante
    campo.click()
    page.keyboard.type("821848", delay=200) # Tecleado dilatado (200ms) que forza el Trigger
    time.sleep(2) # Obliga a Python a esperar la respuesta JSON por red
    page.keyboard.press("ArrowDown") # Captura el nodo UI
    ```  

### 5.3 Uso de las Esperas y Logs (Debugging)
Si la página parece congelada pero funciona manual: el RPA es más veloz que la internet. Si los campos dan el evento de TimeOut (*Timeout 30000ms exceeded*):
* Coloca `time.sleep(1)` o `time.sleep(2)` antes y después de campos que sabes cargan listados enormes de SAP.
* O mejor aún, la validación segura de red: `page.wait_for_load_state("networkidle", timeout=30000)` que congela el robot hasta que la web deje de intercambiar paquetes de forma transigente. 

Cualquier futura reescritura de módulos se hará conservando estos pilares y esta lectura general de las particularidades de `coupa_actions.py` y el motor `Playwright` asegurará años de estabilidad en un solo hilo al mes de automatización.
