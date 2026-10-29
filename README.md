> Configuración vigente de voz: Voice.ai. Las secciones de ElevenLabs y Gemini TTS se conservan como historial; consulta la configuración Voice.ai al final.

> Voz vigente: ElevenLabs. La configuración de Gemini TTS en las secciones anteriores es histórica; consulta «Activar tu voz de ElevenLabs» al final.

# Matemática II Interactiva

Plataforma web educativa para el Proyecto Integrador de **Matemática II ** de la UNI. Integra cálculo diferencial de funciones de varias variables, cálculo integral multivariable y análisis vectorial en un flujo único:

`Problema → modelo matemático → desarrollo → gráfica → interpretación → aplicación de ingeniería`

## Capacidades

- Editor visual MathLive con entrada de texto compatible con SymPy.
- Motor simbólico seguro con validación de símbolos, sin uso de `eval()`.
- Desarrollo por pasos: datos implícitos, fórmula, sustitución/desarrollo, resultado e interpretación.
- Gráficas Plotly interactivas de superficies, planos tangentes, campos vectoriales y curvas espaciales.
- Herramientas para parciales, gradiente, direccionales, tangente, extremos, Lagrange, diferenciales exactas, Jacobianos y regla de la cadena.
- Integrales dobles, triples y polares; área de superficie; masa y centro de masa.
- Funciones vectoriales, campos, divergencia, rotacional, laplaciano, integrales de línea, conservatividad y teorema de Green.
- Caso integrador de distribución de temperatura en una placa técnica, ejercicios y un historial de sesión.

## Arquitectura del Sistema y Stack Tecnológico

El proyecto está construido bajo una arquitectura cliente-servidor robusta y modular. Este diseño se basa en el principio de separación de responsabilidades (*Separation of Concerns*), delegando la interacción visual al navegador del cliente y aislando la pesada carga de procesamiento simbólico y generación de lenguaje natural en el servidor web.

| Capa | Tecnología | Función Principal |
| :--- | :--- | :--- |
| **Backend / API** | Python 3 y Flask | Microframework que orquesta la lógica, expone los endpoints RESTful y gestiona las variables de entorno de forma segura. |
| **Motor de Cálculo** | SymPy, NumPy, SciPy | Resolución de cálculo simbólico exacto, generación de mallas espaciales y operaciones matriciales. |
| **Interfaz (UI/UX)** | HTML5, CSS3, JS, Bootstrap 5 | Estructura semántica, diseño responsivo y peticiones asíncronas (AJAX/Fetch API) para una experiencia fluida. |
| **Entrada Matemática** | MathLive (CDN) | Teclado virtual interactivo que traduce la notación matemática natural del estudiante a texto y comandos procesables. |
| **Tipografía Científica**| MathJax (CDN) | Renderizado en el navegador de fórmulas complejas y resultados algebraicos en alta calidad (formato LaTeX). |
| **Visualización 3D** | Plotly.js (CDN) | Renderizado de gráficos interactivos (superficies, curvas de nivel) a partir de los datos generados por el backend. |
| **Inteligencia Artificial**| Google Gemini API | Tutor virtual restringido que genera explicaciones pedagógicas ancladas a los resultados validados por el motor. |

---

### Flujo de Ejecución y Procesamiento de Datos

Para garantizar precisión matemática y una respuesta rápida, la plataforma sigue un flujo de datos estrictamente orquestado ante cada consulta del estudiante:

#### 1. Interacción del Usuario y Captura de Datos
El estudiante interactúa con la plataforma a través del editor visual de **MathLive**. Esta herramienta es vital porque elimina la barrera de aprender sintaxis de programación; el usuario escribe fracciones, derivadas o integrales de forma natural. **JavaScript** captura esta entrada, empaqueta los parámetros en un objeto JSON y realiza una petición asíncrona (Fetch) hacia el endpoint `/api/calculate` del servidor, permitiendo que la página se mantenga dinámica sin necesidad de recargarse.

#### 2. Validación y Cálculo Simbólico (El "Cerebro" Exacto)
Una vez que **Flask** recibe el *payload*, la expresión se sanitiza y se envía al motor matemático. Se utiliza **SymPy** por una razón crítica: procesa matemáticas de forma *simbólica* y no numérica. Esto asegura que el estudiante reciba resultados algebraicos exactos (por ejemplo, $\frac{\pi}{2}$ o $\sqrt{3}$) en lugar de aproximaciones flotantes que inducen a error. Si el problema requiere trazados tridimensionales, **NumPy** genera las matrices de coordenadas espaciales.

#### 3. Generación de Explicaciones con IA Restringida
Los modelos de lenguaje tienden a "alucinar" o cometer errores en cálculos matemáticos complejos. Para solucionar esto, el sistema implementa un enfoque de **IA Anclada**. En lugar de pedirle a **Google Gemini** que resuelva el problema, el backend le inyecta los resultados exactos que SymPy ya validó matemáticamente. El *prompt* interno obliga a la IA a actuar exclusivamente como un "traductor pedagógico", generando el desarrollo algebraico paso a paso que conecta ineludiblemente con la respuesta correcta del motor. 

#### 4. Renderizado y Respuesta al Cliente
El backend devuelve al navegador un JSON consolidado que contiene: el título del tema, los pasos de la IA formateados de forma segura, y los arreglos de coordenadas tridimensionales (si aplica). En el frontend:
* **MathJax** intercepta todas las cadenas de texto con notación LaTeX y las dibuja instantáneamente con calidad de imprenta (con soporte para scroll horizontal en fórmulas extensas).
* **Plotly.js** toma los arreglos de coordenadas y renderiza gráficos 3D interactivos, permitiendo al estudiante rotar, hacer zoom y explorar visualmente conceptos de cálculo multivariable como planos tangentes o paraboloides.

## Instalación y ejecución

## Abrir y ejecutar en Visual Studio Code

1. Extrae el proyecto y abre la carpeta **matematica_ii_interactiva** con **File → Open Folder** en VS Code.
2. Instala las extensiones recomendadas: **Python** y **Python Debugger** de Microsoft.
3. Abre una terminal integrada (`Ctrl + Ñ`) y crea el entorno virtual con los comandos de la sección correspondiente a tu sistema.
4. Selecciona el intérprete `venv` si VS Code lo solicita.
5. Pulsa **F5** y elige **Iniciar Matemática II Interactiva**. VS Code iniciará `app.py` en su terminal integrada.
6. Abre `http://127.0.0.1:5000` en el navegador.

La carpeta `.vscode` incluida configura automáticamente la depuración para este proyecto.

### Windows (PowerShell)

```powershell
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

### Linux / macOS

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

Abre [http://127.0.0.1:5000](http://127.0.0.1:5000) en el navegador. Las bibliotecas de interfaz se cargan desde CDN, por lo que se recomienda conexión a Internet al abrir la aplicación.



## Uso de las calculadoras

1. Selecciona una unidad o el **Laboratorio Matemático**.
2. Escribe con el editor visual o con sintaxis de texto (`x^2+y^2`, `sqrt(x)`, `sin(theta)`).
3. Completa punto, dirección, límites o restricción cuando la herramienta lo solicite.
4. Pulsa **Calcular** para ver el procedimiento, el resultado simbólico y su aproximación decimal.
5. Usa **Ver gráfica** para una superficie adicional o manipula la gráfica generada con Plotly.

Las expresiones admiten variables `x`, `y`, `z`, `t`, `r`, `theta`, `phi`, `rho` y las funciones `sin`, `cos`, `tan`, `asin`, `acos`, `atan`, `exp`, `log`, `sqrt` y `abs`.

## Seguridad

La aplicación no evalúa código Python escrito por usuarios. Antes de llegar a SymPy, cada expresión se limita en longitud, caracteres, identificadores, variables y funciones; atributos, cadenas, listas y separadores de sentencias no son admisibles. Los errores se devuelven como mensajes amigables, sin traceback.

## Agregar ejercicios

1. Añade el enunciado y la tarjeta visual en `templates/ejercicios.html`.
2. Registra la respuesta simbólica simplificada y la pista en el diccionario `EXERCISES` de `app.py`.
3. El comprobador compara expresiones equivalentes, no solamente texto idéntico.

## Agregar herramientas o problemas de ingeniería

1. Implementa una función de cálculo en el módulo de unidad correspondiente.
2. Incluye su nombre en `OPERATIONS` y `HANDLERS`.
3. Añade una tarjeta con la macro `calculator()` en la plantilla adecuada.
4. Si corresponde, devuelve un `plot` en la respuesta para que `static/js/main.js` lo represente.
5. Acompaña el resultado con interpretación matemática y aplicación ingenieril.


## Mejoras de confiabilidad de octubre de 2026

Se conservaron las 23 operaciones y el diseño existente. Las mejoras toman como referencia la propuesta docente y se integraron en los módulos originales.

- El cálculo responde sin consultar Gemini y sin generar gráficas. La interfaz solicita después la gráfica y ofrece un botón opcional para la explicación de IA.
- El botón de gráfica usa la operación de la tarjeta: campos, curvas y planos ya no se envían a una ruta que solo acepta superficies escalares.
- El cálculo, la gráfica y la IA se ejecutan en procesos separados, con un máximo de dos trabajos simultáneos por proceso Flask. Los tiempos máximos son 12 segundos para matemáticas y 20 para IA; el proceso que excede el tiempo se termina. Las solicitudes aceptan como máximo 16 KiB.
- La entrada se normaliza con SymPy y se interpreta mediante un AST permitido, sin eval ni parse_expr. Se conservan multiplicación implícita, raíces, logaritmos y variables polares. Los decimales se convierten a racionales exactos. Se rechazan divisiones por cero, resultados numéricos no reales, entradas excesivamente complejas y exponentes numéricos fuera de [-100,100].
- Extremos distingue puntos aislados de familias; el Hessiano inconcluso no se presenta como una clasificación definitiva.
- Divergencia admite dos o tres componentes. La vista 3D de campos queda fuera de esta entrega; se muestra el resultado y una nota.
- Integral doble permite elegir `xy` (primero x) o `yx` (primero y). Las cotas exteriores son constantes reales finitas; las interiores solo dependen de la variable exterior. Se verifica el orden de cotas afines; para cotas no afines se advierte que no se certificó el orden en todo el intervalo.
- Se muestra la antiderivada interna y el residuo de su comprobación. Esto no certifica la convergencia de integrales impropias.
- Las respuestas, el historial y las explicaciones se insertan como texto, sin interpretar HTML. El editor conserva la agrupación de raíces y fracciones anidadas; la notación no admitida da un mensaje explícito.
- Las gráficas convierten puntos no finitos a null para generar JSON válido. Los errores gráficos no eliminan el resultado matemático.
- Las respuestas incorrectas a ejercicios muestran una pista, sin revelar automáticamente la solución.

### API

`POST /api/calculate` conserva `operation`, `expression` y `params`, y los campos de resultado originales. `plot` ahora es null; `warnings` puede contener advertencias.

`POST /api/plot` recibe los mismos datos y devuelve la gráfica correspondiente, o un objeto `kind: message`. Esta implementación recalcula la operación en su propio proceso para evitar compartir expresiones ejecutables o estado de usuario entre peticiones.

`POST /api/plot/surface` sigue disponible para clientes que solo necesiten una superficie.

`POST /api/explain` recibe los datos del cálculo, reconstruye los pasos en el servidor y solicita la explicación a Gemini. No acepta como contexto confiable pasos enviados por el navegador. Las explicaciones adicionales se identifican como orientativas, sin certificación algebraica automática.

`POST /api/exercise/<id>` devuelve `correct` y `hint`; ya no entrega `solution`.

Los errores distinguen entrada (400), tamaño (413), operación interna (500), ocupación o IA no configurada (503) y tiempo agotado (504). No se devuelven trazas ni credenciales.

### IA opcional

El motor funciona sin clave ni importación del SDK de Gemini. Para el botón de explicación se utiliza la clave existente `GEMINI_API_KEY` en `.env`; no debe publicarse. `GEMINI_MODEL` permite configurar el modelo; su valor predeterminado conserva el modelo que ya usaba el proyecto. Los fallos del proveedor no impiden obtener el cálculo. No se verificó una llamada real al proveedor durante esta entrega.

### Pruebas

Desde la carpeta del proyecto, con las dependencias instaladas:

```powershell
python -m unittest discover -s tests -v
node tests/test_frontend.cjs
```

Node solo es necesario para la prueba del editor JavaScript. Las pruebas Python comprueban operaciones, casos límite, rutas, procesos, tiempos máximos y errores. No requieren clave de IA. El código conserva las dependencias originales; no hay que reemplazar requirements.txt con el del paquete docente.

### Límites de esta entrega

Los límites de tiempo y concurrencia no constituyen una cuota dura de memoria ni una cola global entre varios procesos de producción. El análisis completo de dominios, límites multivariables, singularidades, conservatividad global, convergencia y validación de cada paso de IA requiere trabajo adicional. La aplicación continúa usando bibliotecas del navegador por CDN. No se incluyen cuentas, exportaciones ni persistencia académica.

## Asistente virtual: avatar, JARVIS, texto y voz

Abre **JARVIS · Asistente** en el menú (`/asistente`) o el botón flotante **Atlas** de cualquier otra página. Las dos vistas comparten la conversación en la misma pestaña. El estilo Tutor guía paso a paso; JARVIS cambia el tono y ofrece una pantalla de inspiración tecnológica.

- Escribe y pulsa Enviar. Enter envía; Shift+Enter añade una línea.
- **Dictar** activa el micrófono por una acción tuya. Revisa el texto y pulsa Enviar; el dictado nunca envía solo. Requiere permiso del navegador y HTTPS o localhost.
- **Escuchar** lee cada respuesta. En Personalizar puedes elegir una voz española disponible y activar lectura automática. Detener voz cancela la lectura. Cerrar el panel o cambiar de pestaña detiene la voz.
- **Personalizar avatar y voz** permite cambiar nombre, color y personaje. Puedes cargar PNG/JPG/WebP hasta 2 MB y 2048 × 2048; se normaliza a PNG con un límite de almacenamiento aproximado de 450 KB. Si no cabe, se pide una imagen menor.
- Para una hoja de sprites usa celdas del mismo tamaño, entre 1 y 16 fotogramas por fila y 1 o 4 filas. En cuatro filas, de arriba abajo: espera, escucha, pensamiento y habla. La animación respeta la preferencia de movimiento reducido.
- **Preguntar al asistente sobre este cálculo** adjunta la entrada de un resultado. El servidor vuelve a calcularla con SymPy antes de enviarla a la IA. Las explicaciones adicionales son orientativas.
- **Nueva conversación** borra el historial y el contexto de la sesión, conservando la personalización.

El avatar y las preferencias se guardan en localStorage de ese navegador. Las últimas 20 intervenciones se guardan en sessionStorage de la pestaña; hasta 8 se envían como historial, recortado según tamaño. No hay sincronización entre dispositivos ni cuentas. La imagen no se envía a Gemini. Las preguntas y el contexto del cálculo sí se envían al proveedor al pulsar Enviar.

El chat usa la configuración existente `GEMINI_API_KEY` y `GEMINI_MODEL`. En desarrollo configura la clave en `.env`; en Render, en las variables de entorno del servicio. Nunca la pongas en JavaScript ni la subas a GitHub. No se añadieron dependencias. Sin clave, el chat muestra un aviso y las calculadoras siguen funcionando.

La voz usa Web Speech API y las voces instaladas/disponibles en el navegador; no reproduce la voz del personaje de una película. La disponibilidad del dictado varía según navegador y sistema, y puede utilizar un servicio remoto del navegador. Las fórmulas complejas se consultan mejor en el texto: la lectura no es un lector matemático especializado. Referencia: [MDN: Web Speech API](https://developer.mozilla.org/en-US/docs/Web/API/Web_Speech_API).

### Archivos del asistente

- `modules/assistant.py`: valida preguntas e historial, recalcula el contexto y consulta Gemini.
- `app.py` y `modules/worker.py`: página `/asistente`, API `/api/chat` y ejecución con límite de tiempo.
- `templates/assistant_panel.html`: panel compartido y controles.
- `templates/assistant_widget.html`: botón y panel flotante.
- `templates/asistente.html`: pantalla JARVIS.
- `static/js/assistant.js`: conversación, almacenamiento local, avatar animado, dictado y lectura.
- `static/css/assistant.css`: presentación adaptable y animaciones.
- `static/js/main.js`: acción que adjunta un cálculo al asistente.

### Validación del asistente

```powershell
python -m unittest discover -s tests -v
node tests/test_frontend.cjs
node tests/test_assistant_frontend.cjs
```

Se comprobaron 37 pruebas Python y las pruebas JavaScript del editor y del chat. Estas últimas simulan DOM, micrófono y síntesis: prueban eventos, transcripción sin envío automático, lectura, contexto, errores y respuestas antiguas. El proveedor de IA se simuló; no se consumió cuota. No se pudo completar la revisión visual ni una prueba de audio real porque el navegador automatizado no arrancó en el entorno de trabajo. Queda probar micrófono/altavoz y una respuesta real con tu configuración en tu navegador.

## Actualización: Cuphead y voz natural

Cuphead es ahora el sprite predeterminado, visible en el botón flotante y en la cabecera. Se utilizan exclusivamente los 16 PNG `cuphead_run_0001` a `cuphead_run_0016` del ZIP proporcionado por el usuario. La secuencia se llama `run`: el archivo no contiene otra secuencia denominada caminar. Los PNG se conservan intactos; CSS amplía el personaje compensando los márgenes transparentes. No se añadieron disparos ni otras acciones. La animación se pausa con la pestaña oculta y respeta movimiento reducido.

El botón **⚙ Personalizar sprite y voz** abre los controles y permanece visible en la barra del chat. Puedes elegir Cuphead, los personajes anteriores o tu propia imagen. Esta actualización activa Cuphead y la lectura automática una vez, al migrar las preferencias anteriores; las elecciones posteriores se conservan. Los recursos llevan versión en su URL para evitar cargar el CSS o JavaScript anterior de caché.

Al pulsar **Enviar**, el asistente dice inmediatamente una confirmación breve usando la voz española del navegador. Después de recibir el texto, genera y reproduce la respuesta en voz natural. No puede leer una respuesta antes de que Gemini la genere: no se implementa transmisión progresiva del chat. **Detener voz** cancela tanto la generación de audio en el navegador como la reproducción, e impide la lectura automática pendiente de esa pregunta.

En **Tipo de voz** puedes seleccionar:

- **Natural · Gemini** (predeterminada): síntesis en español latinoamericano usando la misma `GEMINI_API_KEY`. Consume la cuota de audio del proveedor, que puede diferir de la cuota de chat. La generación tiene su propia espera; los fragmentos se leen en orden. Si el proveedor falla, se continúa con la voz del navegador.
- **Español · navegador (rápida)**: empieza a leer al recibir la respuesta, sin solicitar audio a Gemini. Prioriza las voces españolas denominadas Natural/Neural/Online cuando existen. **Voz del navegador / respaldo** permite elegir entre las voces españolas disponibles.

**Probar voz** reproduce una frase de prueba. La lectura convierte fracciones, raíces, potencias y símbolos habituales a expresiones españolas y segmenta el texto con pausas. La pronunciación de fórmulas muy complejas sigue dependiendo de la síntesis; conserva el texto como referencia.

Configuración opcional del servidor:

```text
GEMINI_TTS_MODEL=gemini-3.8-flash-tts
GEMINI_TTS_VOICE=Charon
```

Son los valores predeterminados de la integración REST utilizada. Se consultó la [documentación oficial de Gemini TTS](https://ai.google.dev/gemini-api/docs/generate-content/speech-generation). Si la cuenta no tiene acceso al modelo o no tiene cuota, el navegador es el respaldo. No se actualiza el SDK ni se añaden dependencias. El nuevo endpoint `/api/speech` recibe fragmentos de hasta 1200 caracteres; valida el audio, devuelve WAV sin guardarlo y aplica un límite de tiempo independiente de 24 segundos. La clave queda en el servidor.

Validación de esta actualización: 44 pruebas Python y tres suites JavaScript (editor, chat y voz/sprite), con proveedor y dispositivos simulados. Se comprobó la existencia de los 16 PNG, sus dimensiones y márgenes transparentes; se inspeccionó visualmente el primer fotograma. No se hizo una llamada real de audio a Gemini ni una escucha en el dispositivo del usuario. Para probar el resultado completo: reinicia Flask, recarga la página con Ctrl+F5 y pulsa **Probar voz**. El navegador puede requerir interacción para permitir reproducir sonido.

```powershell
node tests/test_speech_frontend.cjs
```


# Activar tu voz de ElevenLabs

Voz seleccionada: https://elevenlabs.io/voices/YKrm0N1EAM9Bw27j8kuD
Identificador predeterminado: `YKrm0N1EAM9Bw27j8kuD`.

1. En tu cuenta de ElevenLabs, comprueba que puedes usar esa voz; si el sitio lo solicita, añádela a tu biblioteca.
2. Crea una clave de API con permiso para convertir texto a voz. No hace falta enviarla por el chat.
3. En el archivo `.env` del proyecto añade esta variable con tu clave real:

```dotenv
ELEVENLABS_API_KEY=tu_clave_real
```

El identificador ya está configurado en el código. Solo si quieres cambiarlo, utiliza:

```dotenv
ELEVENLABS_VOICE_ID=YKrm0N1EAM9Bw27j8kuD
```

En Render configura estas variables en Environment del servicio. La clave de Gemini sigue siendo necesaria para las respuestas del chat, pero ya no se usa para generar esta voz. No publiques `.env`: ya está excluido mediante `.gitignore`.

4. Reinicia el servidor y recarga con Ctrl+F5.
5. Abre **Personalizar sprite y voz**, selecciona **ElevenLabs · voz elegida** y pulsa **Probar voz**.

Las respuestas se leen automáticamente si la casilla correspondiente está activa. En el modo ElevenLabs no se reproduce la confirmación inicial con otra voz: el sonido comienza al estar listo el audio solicitado. La voz del navegador sigue disponible como opción y como respaldo identificado mediante un aviso si ElevenLabs falla.

La implementación usa el modelo multilingüe `eleven_multilingual_v2` y MP3. Recibe el texto español ya preparado por el asistente y conserva la pronunciación matemática mejorada. No descarga una grabación fija del catálogo: solicita audio nuevo para cada respuesta y consume cuota de ElevenLabs.

El enlace no permitió verificar desde aquí el nombre de catálogo, escuchar la voz ni comprobar los permisos de tu cuenta. Se verificaron el ID enviado a la API, el formato MP3, la cancelación, los errores y el respaldo mediante pruebas con respuestas simuladas. Falta una prueba real después de configurar la clave.

Documentación utilizada: https://elevenlabs.io/docs/api-reference/text-to-speech/convert


# Voz seleccionada en Voice.ai

Proveedor vigente: Voice.ai. Esta configuración reemplaza ElevenLabs para las respuestas habladas.

- Voz predeterminada: `ca993c5a-dc17-4800-94fc-1cdcabe759fc`.
- Variable privada del servidor: `VOICEAI_API_KEY`.
- Variable opcional para cambiar la voz: `VOICEAI_VOICE_ID`.
- Idioma solicitado a la API: español (`es`). Formato: MP3.
- Ruta oficial: `https://dev.voice.ai/api/v1/tts/speech`.

En Render debes configurar `VOICEAI_API_KEY` en las variables de entorno del servicio; el archivo `.env` local no se sube a GitHub. Gemini continúa generando el texto del chat.

Reinicia el servidor y recarga con Ctrl+F5. En **Personalizar sprite y voz** aparece **Voice.ai · voz elegida**. Pulsa **Probar voz**. Esta actualización selecciona una vez Voice.ai y activa la lectura automática, respetando la personalización posterior.

Si el servicio rechaza la clave, la voz, el idioma o la cuota, se muestra un aviso y se usa la voz del navegador como respaldo. No se compra ni cambia ningún plan automáticamente.

Referencia: [API oficial de Voice.ai](https://voice.ai/docs/api-reference/text-to-speech/generate-speech).


Prueba real de esta entrega: Voice.ai devolvió HTTP 403 con una página HTML de bloqueo de Cloudflare antes de entregar audio. No se pudo validar el acceso de la clave a esta voz ni escuchar el resultado. La aplicación distingue este bloqueo de errores de autenticación y cuota. Se requiere resolver el acceso con Voice.ai si también ocurre al ejecutar el proyecto.

## Aula virtual

Cuentas de estudiantes y profesores, cursos por código y exámenes automáticos: consulta [GUIA_AULA.md](GUIA_AULA.md). En local funciona con SQLite; SQL Server se configura cuando dispongas de un servidor.

