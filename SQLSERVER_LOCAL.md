# SQL Server en esta laptop

Instancia: `localhost\SQLEXPRESS`. Base del proyecto: `MatematicaII`.
Se utiliza la autenticación de tu usuario de Windows, sin guardar una contraseña SQL.

Con el entorno virtual del proyecto activado, ejecuta:

```powershell
python conectar_sqlserver.py
```

El configurador verifica que SQLite no tenga datos pendientes, crea la base y las tablas si faltan, prueba lectura/escritura y revierte los registros de prueba. Solo después configura `ACADEMY_ODBC_CONNECTION` en `.env`. Conserva las demás variables y guarda una copia privada del archivo anterior en `instance`. No borra SQLite ni tablas existentes. Si hay datos nuevos en SQLite, se detiene para permitir una migración.

Reinicia Flask después de ver el mensaje de éxito. En Management Studio actualiza **Databases → MatematicaII → Tables**. Allí aparecen las tablas `academic_users`, `academic_courses`, `academic_enrollments`, `academic_exams`, `academic_attempts` y `academic_login_limits`.

Si faltan dependencias, ejecuta `python -m pip install -r requirements-sqlserver.txt` y repite el configurador. El controlador Microsoft ODBC Driver 18 debe estar instalado en Windows.

Esta conexión es exclusivamente local: `TrustServerCertificate=yes` se utiliza para la instancia de desarrollo de la laptop. No se abre ningún puerto ni se habilita acceso remoto. Render no puede usar `localhost\SQLEXPRESS` para llegar a esta laptop. Un despliegue remoto necesita una base accesible desde ese servidor y su propia configuración.

Para volver a SQLite, detén Flask, elimina solamente la línea `ACADEMY_ODBC_CONNECTION` de `.env` y reinicia. Los datos creados en SQL Server no se copian automáticamente a SQLite. Nunca subas `.env` o `instance` a GitHub.
