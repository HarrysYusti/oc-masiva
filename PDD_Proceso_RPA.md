# Documentación del Proceso RPA: Carga Masiva de OCs en Coupa

## 1. Descripción General del Proyecto
Este proyecto es una automatización basada en **Playwright** (Python) que se encarga de leer filas desde un archivo de Google Sheets y transformarlas en Órdenes de Compra (OC) dentro del portal Coupa de Natura. El RPA está diseñado para acelerar y asegurar la correcta creación masiva de OCs a partir de una planilla estandarizada.

El objetivo principal es tomar los datos pendientes (aquellos cuyas filas en la columna **REALIZADA** son `FALSE`), buscar una "Solicitud Base" indicada en el mismo Google Sheets, copiarla y modificar los datos de los ítems del carrito según el proveedor, el monto neto o exento, justificación, impuesto, y cuentas contables antes de proceder a guardar el borrador y extraer el # de solicitud de vuelta al Sheet.

---

## 2. Flujo Funcional y Técnico (Paso a Paso)

### 2.1. Conexión y Filtro Inicial
1. El script principal (ya sea `main.py` o su versión de pruebas `main_test.py`) comienza autorizando la conexión a Google Sheets a través del sistema OAuth usando un token validado.
2. Lee todos los datos de la hoja configurada en `config.py` (ej. `CONSOLIDADO OC`).
3. Filtra iterativamente buscando específicamente qué filas están pendientes (es decir, ignora si la columna REALIZADA contiene `TRUE`, `SI` o `VERDADERO`).

### 2.2. Login en Coupa y Manejo de Sesión
1. El RPA no inicia sesión cada vez desde cero. Para evadir validaciones excesivas del Single Sign-On de Microsoft/Google, utiliza un perfil persistente de navegador guardado en la carpeta local `/credentials/chrome_profile`. 
2. Si es la primera ejecución y el archivo no existe, fuerza un guardado automático tras pedir autorización manual con la GUI de Playwright. Luego de esto, reusa la sesión pre-logeada cada vez que el programa se lanza.

### 2.3. Ejecución por cada línea pendiente
Para cada fila leída en el Google Sheets, el robot realiza 2 evaluaciones cruciales: **¿La fila contiene monto NETO? ¿La fila contiene monto EXENTO?**
Si ambos montos existen (mayor a cero/no vacíos), el bot procesará la misma fila **dos veces consecutivas**, generando **dos** Órdenes de Compra separadas (una sin IVA y otra con IVA) para reflejar las exigencias estructurales del retail.

El proceso exacto para cada OC construida, usando módulos atómicos de acción, es el siguiente:

1. **Buscar y Copiar Solicitud Base (`_buscar_y_copiar_solicitud`):** 
   Se ubica en la barra de búsqueda de Actividad Reciente superior la solicitud que está transcrita en la columna "solicitud base" del Sheet. Se accede a ella y se le instruye al software clicar en el botón de **Copiar solicitud n.º X**. Esto traslada de inmediato toda una plantilla inicial a un nuevo carrito de compras.

2. **Llenar Justificación de Cabecera:**
   Se enlaza el campo `DETALLE` más el `NOMBRE TIENDA` del Sheet (Ej: *Agua y Electricidad Aeropuerto*). Este texto combinatorio asienta el texto explicativo de cabecera principal e infiere mejor usabilidad para futuras auditorías o aprobadores.

3. **Inpección y Borrado de archivos adjuntos pre-existentes:**
   El bot inspecciona de manera táctica si la solicitud base (copiada en el paso 1) contemplaba archivos adjuntos o respaldos en PDF heredados y los elimina forzosamente ejecutando clics automatizados en la papelera, de forma que el nuevo boceto de OC nazca completamente "limpio".

4. **Fechas de Servicio de la Organización:**
   Traslada al marco de navegación de la página inferior para actualizar la fecha respectiva. Si la `FECHA EMISIÓN` y la `FECHA VENCIMIENTO` operan sin fallos en el documento de SpreadSheets, el bot las aplica. Superando las restricciones visuales anti-robot del *Datepicker* de Coupa mediante tipeos absolutos con teclado forzado. La fecha límite o *"Need By"* se auto-calcula sumándole 30 días a la inyección inicial.

5. **Edición del Ítem/Línea de Solicitud (El Bloque Core):**
   Es el paso en el cual los cruces contables vitales son procesados y aplicados mediante un panel de despliegue sobre el artículo.

   * **Artículo:** Replica estricta la misma lógica de texto aplicada a la Justificación en Cabecera (Detalle + Tienda).
   * **Proveedor (Autocomplete / Carga Diferida):** Escribe el "COD SAP del proveedor". Al ser listas dinámicas alimentadas por Ajax, el bot simula una latencia humana, quitando e inyectando una última tecla con un delta de retardo manual para empujar la carga del panel servidor de Coupa, bajando virtualmente con la tecla "Flecha Abajo" para enclavar el nombre correcto exacto en el cuadro de input de Coupa sin clics imprecisos de mouse.
   * **Commodity:** Presiona y escribe el código exacto de Commodity, forzando la visualización del listado virtual y disparando la validación del formulario con Enter.
   * **Monto:** Inserta el monto neto analizado (o si es el ciclo del bloque exento, el valor despojado de IVA).
   * **Plazo de Pago:** Localiza e identifica el factor de plan de pago "CL15" insertando texto y forzando autocompleciones emuladas como las líneas previas.
   * **Impuesto (Tax Selectors):** Reemplaza el predeterminado con el condicional de la OC tratante. Limpia el "tag" flotante de Selección Actual del UI, y mediante validadores DOM obligará al sistema a elegir `Material sin impuesto (C0)` para Exento y `IVA 19%` para Neto, forzando búsquedas semánticas sobre los atributos Role > Option.

6. **Vínculo CO (Cuentas Contables y CECO de SAP):**
   Despliega una modalidad sobre-flotante ("Elegir una cuenta"). A través del mapeo exhaustivo de Selectores ID nativos (`#account_segment...`), el robot borra selecciones previas sucias provenientes de la copia inicial y obliga a la API Frontend a captar el `CECO` al igual que la `Cuenta Mayor` listadas en la iteración Sheets de la fila correspondiente, confirmando por ventana los cambios aplicados en Coupa.

7. **Extracción Identitaria y Pre-Guardado:**
   Acuerda guardados a los sub-layouts completados. Extrae la taxonomía del encabezado HTML (`h1` content > "#58744") separando la etiqueta alfanumérica filtrada mediante expresiones regulares (*Regex*), sustrayendo de este mecanismo el puro número para certificar una conclusión limpia tras guardarse el borrador (Test) o enviarse (Producción final).

### 2.5. Actualización, Marcas y Retroalimentación
Finalizada la corrida (independiente de si fue 1 ciclo por Neto o 2 ciclos mixtos de 1 OC exenta y 1 Neta), el script Python invoca un Call Externo HTTP seguro a `google_sheets` ejecutando la función `marcar_realizada`.
Esta directriz accede a la matriz matriz, posicionándose en la columna pre configurada de `REALIZADA` sobre-escribiéndola con un `TRUE`. Así mismo en la columna destinada al `# OC`, clava de manera remota los números de solicitud que fue extrayendo en el paso previo (Ej. `58985` y/o `58986`), dejando sellada permanentemente como procesada esa fila y habilitando cualquier auditoría de control sin intervención humana adicional.
