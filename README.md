# Matemática II Interactiva

Plataforma web educativa para el Proyecto Integrador de **Matemática II (AC2208)** de la UNI. Integra cálculo diferencial de funciones de varias variables, cálculo integral multivariable y análisis vectorial en un flujo único:

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