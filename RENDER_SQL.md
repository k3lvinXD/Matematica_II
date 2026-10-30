# Render gratuito y Azure SQL Database

## Estado

Estos archivos preparan el despliegue Docker. No crean cuentas, una suscripción de Azure ni una base remota, y no publican automáticamente la página. La conexión local a SQL Express permanece intacta. Es necesario completar la base alojada y configurar sus secretos en Render.

## 1. Base de datos alojada

Entra en https://portal.azure.com con tu cuenta Microsoft y configura una suscripción compatible. La verificación de identidad y cualquier información de facturación deben introducirse directamente en el portal, nunca en el chat ni en el repositorio.

Desde la oferta **Azure SQL Database gratuita**, selecciona **Start free / Empezar gratis**. Crea una base llamada `MatematicaII` y un servidor lógico con nombre único. Configura un usuario SQL y una contraseña privada para conectarte desde Render; la autenticación de Windows de la laptop no funciona allí.

Antes de crear el recurso, comprueba:

- Que esté seleccionada la oferta gratuita y el costo estimado sea cero.
- Que el comportamiento al agotar el límite gratuito sea **AutoPause / pausar**, no continuar pagando.
- Que no se añadan servicios de pago opcionales.

La oferta publicada incluye por base 100 000 segundos de vCore, 32 GB de datos y 32 GB de copias de seguridad al mes. La base puede suspenderse al agotarse la cuota, y la primera conexión después de una pausa puede tardar. Deben verificarse las condiciones y elegibilidad que muestre tu suscripción; no todas son compatibles.

Documentación oficial: https://learn.microsoft.com/en-us/azure/azure-sql/database/free-tier?view=azuresql

## 2. Acceso desde Render

El firewall del servidor SQL debe permitir las direcciones de salida del servicio de Render. Consúltalas en el panel de ese servicio y autoriza solamente los rangos necesarios en Azure; no abras el servidor a todas las direcciones. Si necesitas inicializar tablas desde tu laptop, autoriza también su IP pública mientras realizas esa operación.

Utiliza un usuario con acceso a `MatematicaII`. El arranque necesita crear las tablas faltantes y leerlas; la aplicación también necesita insertar, actualizar y borrar sus registros. La base debe existir antes del despliegue. `create_all` no migra columnas de tablas existentes ni copia datos desde tu laptop.

## 3. Código y servicio Docker

Sube al repositorio los archivos fuente y los nuevos `Dockerfile`, `.dockerignore`, `render.yaml`, `deploy/render_start.py` y las pruebas. No subas `.env`, `instance`, `venv`, respaldos ni credenciales.

En Render puedes crear un servicio mediante **New → Blueprint**, seleccionando el repositorio y su `render.yaml`. La plantilla define un servicio Docker gratuito llamado `matematica-ii-sql`; no cambia automáticamente el servicio Python existente ni su URL. Conserva el servicio anterior mientras verificas el nuevo.

Como alternativa, crea un **Web Service** con runtime **Docker**, Dockerfile `./Dockerfile`, contexto `.`, plan **Free** y health check `/`. No configures el build command de Python: Docker instala las dependencias y el controlador ODBC. El comando de arranque ya está en el Dockerfile.

Variables privadas en Render:

- `SECRET_KEY`: secreto aleatorio de al menos 32 caracteres. El Blueprint lo genera automáticamente y lo conserva entre despliegues.
- `ACADEMY_PRODUCTION=1`.
- `ACADEMY_ODBC_CONNECTION`: conexión de la base alojada, con el formato siguiente; sustituye los marcadores únicamente en el campo privado de Render:

```text
DRIVER={ODBC Driver 18 for SQL Server};SERVER=tcp:TU_SERVIDOR.database.windows.net,1433;DATABASE=MatematicaII;UID=TU_USUARIO;PWD={TU_CONTRASEÑA};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;
```

Si la contraseña contiene `}`, se representa como `}}` dentro del valor entre llaves de ODBC. La conexión local `Trusted_Connection=yes` no sirve en Render. No copies allí todo tu `.env` local.

El chat JARVIS requiere además su clave del proveedor de texto, si quieres habilitar sus respuestas en línea. Los exámenes automáticos no dependen de esa API. Configura esa clave directamente en Render y no la incluyas en `render.yaml`.

## 4. Verificación después del despliegue

El arranque valida las variables, verifica/crea las seis tablas y ejecuta una lectura SQL antes de iniciar Gunicorn. Si falla, no imprime la conexión ni sus contraseñas; revisa el host, el firewall y los permisos. Una base gratuita pausada puede requerir un nuevo intento de despliegue después de reactivarse.

Comprueba registro, inicio de sesión, generación de examen, entrega, comentarios y descarga PDF. Reinicia o despliega de nuevo y comprueba que los datos siguen en la base remota. Las cuentas locales no aparecerán automáticamente.

Para autorizar un profesor si tu plan no ofrece terminal remota, conecta SSMS a la base de Azure con tu cuenta administradora y ejecuta esto usando el correo registrado en la página desplegada:

```sql
UPDATE dbo.academic_users
SET role=N'teacher', teacher_requested=0, auth_version=auth_version+1
WHERE email=N'CORREO_REGISTRADO';
```

Debe afectar exactamente una fila. La cuenta deberá volver a iniciar sesión.

Render gratuito puede suspender el servicio web por inactividad. Los datos permanecen en Azure, pero hay tiempos de arranque y límites de ambas ofertas. Estas opciones gratuitas no garantizan disponibilidad continua durante un examen.

Referencias: https://render.com/docs/docker, https://render.com/docs/blueprint-spec, https://render.com/docs/free, https://learn.microsoft.com/sql/connect/odbc/linux-mac/installing-the-microsoft-odbc-driver-for-sql-server
