# Cuentas, profesores y exámenes

## Empezar en tu computadora

En una terminal dentro del proyecto, con tu entorno virtual activado:

```powershell
python -m pip install -r requirements.txt
python app.py
```

Abre la dirección que indique Flask y pulsa **Mi aula** o **Ingresar**. Registra tu cuenta con una contraseña de al menos 12 caracteres. Si eres docente, marca la solicitud de profesor.

Todas las cuentas nuevas son estudiantes hasta que el administrador del servidor las autoriza. En otra terminal del mismo entorno, ejecuta con tu correo real:

```powershell
python -m flask --app app authorize-teacher profesor@ejemplo.com
```

Vuelve a iniciar sesión. El profesor puede crear un curso y compartir su código; los estudiantes se registran y se inscriben con ese código.

## Preparar y resolver un examen

1. El profesor entra en su curso y elige tema, dificultad, cantidad (1–20) y duración (5–180 minutos).
2. El sistema genera un **borrador** con ejercicios, fórmulas, respuesta escrita y explicación. Usa plantillas matemáticas con SymPy, sin una API de inteligencia artificial.
3. El profesor revisa y puede editar cada enunciado, fórmula y solución con el teclado matemático. Confirma la revisión y publica el examen. Después de publicarlo no se modifica su contenido.
4. Los alumnos inscritos pueden comenzar. Hay un intento por alumno; salir y volver continúa el mismo intento y no reinicia el tiempo.
5. El procedimiento y las respuestas se guardan automáticamente mientras hay conexión. También hay un botón para guardar y otro para entregar definitivamente. Al agotarse el tiempo se califican únicamente las respuestas que llegaron al servidor.
6. El profesor consulta resultados y entregas individuales. Al **cerrar el examen**, los estudiantes pueden consultar su nota y soluciones. Cerrar impide nuevos intentos y termina los pendientes.

Temas disponibles (los 23 de las calculadoras):

- Unidad 1: derivadas parciales, gradiente, derivada direccional, plano tangente y recta normal, máximos/mínimos/silla, Lagrange, diferencial exacta y potencial, regla de la cadena, Jacobiano y límite univariable.
- Unidad 2: integral doble cartesiana, integral triple, polares, área de una superficie, masa y centro de masa.
- Unidad 3: trayectoria espacial, campo vectorial 2D, divergencia, rotacional, laplaciano, integral de línea, campo conservativo y Green.

Los ejercicios piden un resultado numérico exacto o una componente concreta, indicando qué debe escribirse en la respuesta. El procedimiento permite desarrollar el plano, vector, potencial o clasificación cuando corresponda. El profesor debe revisar el borrador: la generación usa familias de ejercicios y no representa todas las variantes posibles de cada tema. No es un sistema de supervisión contra trampas.

## Resolver en la página y llevar al aula física

Los exámenes nuevos contienen ejercicios de respuesta escrita, sin opciones A/B/C/D. El estudiante escribe sus pasos en **Procedimiento** y su resultado exacto con el mismo teclado MathLive de las calculadoras. Si el teclado no carga, queda disponible un campo de texto (por ejemplo, `3/5`). La revisión automática comprueba equivalencia matemática de resultados numéricos; no acepta una aproximación decimal como si fuera exacta. El procedimiento se conserva para que lo evalúe el profesor.

El profesor abre **Ver resultados**, pulsa el nombre del estudiante y ve la respuesta, el procedimiento y el estado correcto/incorrecto/pendiente. Una expresión no interpretable queda pendiente de revisión, y las notas con pendientes se señalan como provisionales. Los botones **Marcar correcto** y **Marcar incorrecto** permiten corregir el resultado después de revisar una entrega finalizada.

En cada examen del profesor están **Descargar PDF** y **Descargar imágenes PNG (ZIP)**. Funcionan también para borradores; guarda tus cambios antes. El documento tiene páginas A4, encabezado, nombre, fecha y espacio para resolver; no contiene respuestas ni datos de estudiantes. El ZIP incluye una imagen por página a 150 ppp. Descomprímelo para imprimir las imágenes. Solo el profesor dueño del curso puede descargar estas versiones.

Los exámenes anteriores conservan sus datos y entregas. Para reemplazar un borrador de opción múltiple, abre **Generar ejercicios nuevos para este borrador**, confirma el reemplazo y pulsa **Regenerar como ejercicios**. Mantiene el tema, dificultad, cantidad y duración, pero reemplaza todos los enunciados y ediciones. Un examen publicado no se regenera: crea uno nuevo.

Para actualizar la aplicación, instala `python -m pip install -r requirements.txt`, reinicia el servidor y recarga con Ctrl+F5. La exportación requiere Matplotlib, ReportLab y Pillow, ya incluidos en las dependencias. Se ejecuta en un proceso con límite de tiempo y una exportación simultánea por proceso del servidor.

## Comentarios a las entregas

En **Ver resultados → nombre del estudiante**, una entrega finalizada muestra **Comentarios para el estudiante**. Puedes escribir un comentario general (hasta 3000 caracteres) y uno por ejercicio (hasta 1500). **Guardar todos los comentarios** guarda el conjunto sin modificar la calificación. Deja un campo vacío y guarda para borrar ese comentario. Guarda los comentarios antes de salir o cambiar una calificación.

El estudiante los ve en **Ver entrega**, junto a su resultado, después de cerrar el examen. Antes del cierre permanecen privados. Solo el profesor dueño del curso puede editarlos y solo el estudiante dueño de la entrega puede consultarlos. Si otra ventana cambió los comentarios, se solicita recargar para evitar sobrescribirlos.

## Base de datos local

Sin configuración adicional se utiliza SQLite en `instance/academia.sqlite3`. La clave local de sesión se guarda en `instance/session.key`. Ambos archivos son privados y están excluidos de Git. Conserva una copia de seguridad de la carpeta `instance` con el servidor detenido. No publiques esa carpeta.

Para restablecer una contraseña desde la terminal del administrador:

```powershell
python -m flask --app app reset-academy-password estudiante@ejemplo.com
```

La terminal pide y confirma la contraseña sin mostrarla. No hay recuperación por correo en esta versión.

## Conectar SQL Server después

La integración está preparada con SQLAlchemy y pyodbc, pero necesitas disponer de un servidor, crear una base de datos y un usuario. No se ha probado contra un servidor SQL Server real en esta entrega.

1. Instala Microsoft ODBC Driver 18 en el equipo donde se ejecute Flask: [instrucciones oficiales](https://learn.microsoft.com/sql/connect/odbc/download-odbc-driver-for-sql-server).
2. Instala las dependencias opcionales: `python -m pip install -r requirements-sqlserver.txt`.
3. Configura las variables privadas del servidor, o tu `.env` local, sin subirlas a Git:

```dotenv
SECRET_KEY=REEMPLAZAR_CON_UN_SECRETO_ALEATORIO_DE_AL_MENOS_32_CARACTERES
ACADEMY_ODBC_CONNECTION=DRIVER={ODBC Driver 18 for SQL Server};SERVER=tcp:TU_SERVIDOR,1433;DATABASE=MatematicaII;UID=TU_USUARIO;PWD=TU_CLAVE;Encrypt=yes;TrustServerCertificate=no;
```

Usa un certificado válido para el servidor y una cuenta de base de datos dedicada. La contraseña debe escaparse según las reglas ODBC si contiene caracteres especiales. No envíes estas credenciales por chat.

4. Ejecuta `python -m flask --app app init-academy` para crear las tablas en la base existente. Después reinicia Flask.

Cambiar de SQLite a SQL Server no copia los usuarios y exámenes existentes; la migración de datos requiere una operación separada. `init-academy` crea tablas faltantes, no modifica esquemas existentes.

## Render o Ubuntu en producción

El código no se ha desplegado automáticamente. Sube los archivos fuente y vuelve a desplegar cuando configures el almacenamiento.

- Define `SECRET_KEY` con un valor aleatorio privado de al menos 32 caracteres. Puedes generarlo con `python -c "import secrets; print(secrets.token_hex(32))"` y guardarlo como variable del servidor.
- En Ubuntu define `ACADEMY_PRODUCTION=1` y sirve la página mediante HTTPS. En Render se detecta el entorno automáticamente.
- Configura SQL Server como arriba, instalando también el controlador del sistema operativo. El comando de instalación de dependencias será `pip install -r requirements-sqlserver.txt`.
- Como alternativa, utiliza un **disco persistente** y define `ACADEMY_DATABASE_URL=sqlite:////ruta/al/disco/academia.sqlite3`. SQLite es apropiado para una primera instalación pequeña con una instancia de la aplicación; no uses una base en el almacenamiento efímero de Render.
- Mantén el inicio con `gunicorn -c gunicorn.conf.py app:app` y ejecuta la inicialización de SQL Server y la autorización de profesores desde una terminal privada del servidor.
- Si falta la clave o la configuración de base de datos en producción, el aula muestra un aviso de configuración. Las secciones públicas de matemáticas siguen disponibles.

La voz de JARVIS y sus proveedores no intervienen en la generación de estos exámenes.
