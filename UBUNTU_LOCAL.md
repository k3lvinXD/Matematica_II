# Matemática II en Ubuntu Server local

Este despliegue usa PostgreSQL y Docker Compose. SQL Server y el archivo `.env`
de Windows permanecen intactos. No requiere contratar un servicio; sí consume
recursos y electricidad de tu equipo. La máquina virtual debe estar encendida.

## Preparar la máquina virtual

Como punto de partida asigna 2 CPU, 4 GB de RAM y 25 GB de disco; ajusta según uso.
Usa red «adaptador puente» para que otros equipos de tu LAN puedan acceder.
Con NAT necesitas configurar reenvío de puertos en el programa de virtualización.
Consulta la IP dentro de Ubuntu con `hostname -I`.

Instala Docker Engine y el complemento Compose siguiendo la guía oficial:
https://docs.docker.com/engine/install/ubuntu/
Verifica `docker compose version`. Los comandos siguientes requieren permiso
para usar Docker (o ejecutarlos con sudo). Instala OpenSSH si quieres administrar
la máquina desde Windows: `sudo apt install openssh-server`.

Copia el proyecto a Ubuntu, por ejemplo a `~/Matematica_II`, sin `.env`, `venv`,
`instance`, `.git` ni archivos privados. No copies el entorno virtual de Windows.
La imagen Docker instala las dependencias de Linux.

## Iniciar

Desde la carpeta del proyecto en Ubuntu:

```sh
python3 deploy/prepare_ubuntu.py
sh deploy/ubuntu.sh up -d --build
sh deploy/ubuntu.sh ps
sh deploy/ubuntu.sh logs --tail=80 app
```

Abre `http://IP_DE_UBUNTU:8080`. La configuración inicial es HTTP exclusivamente
para una red local de confianza. Las cookies están adaptadas a ese acceso.
No publiques el puerto en Internet: para ello configura HTTPS y cambia
`ACADEMY_LOCAL_HTTP=0` en `.ubuntu.env`, después recrea el servicio app.
PostgreSQL no expone su puerto a la laptop ni a la red.

`.ubuntu.env` contiene claves privadas generadas al azar. Nunca lo publiques.
No lo regeneres después de crear la base: cambiar el archivo no cambia la
contraseña almacenada en PostgreSQL. Conserva una copia privada.

Los usuarios/exámenes de Windows no aparecen automáticamente en Ubuntu.
Puedes empezar con un aula vacía, o trasladarlos como se indica abajo.
Para autorizar a un profesor después de registrarlo:

```sh
sh deploy/ubuntu.sh exec app python -m flask --app app authorize-teacher correo-del-profesor
```

## Trasladar los datos actuales sin borrarlos

1. En Windows detén Flask y evita nuevas entregas durante el traslado.
2. En la terminal del proyecto con su venv activo ejecuta:

```powershell
python -m deploy.transfer_academy export instance/traslado-academia.json
```

3. Copia ese JSON a Ubuntu de forma privada. Contiene datos personales y hashes
   de contraseñas; no lo subas a GitHub ni lo envíes por el chat.
4. Antes de usar el aula de Ubuntu, ejecuta allí (ajusta la ruta del JSON):

```sh
sh deploy/ubuntu.sh stop app
sh deploy/ubuntu.sh run --rm -T -v "$PWD/traslado-academia.json:/transfer.json:ro" app python -m deploy.transfer_academy import /transfer.json
sh deploy/ubuntu.sh up -d app
```

La importación solo acepta un PostgreSQL vacío. Conserva identificadores,
cuentas, contraseñas, cursos, exámenes, respuestas y comentarios. No copia
bloqueos temporales de login. Inserta todo en una transacción; no borra el origen.
Verifica el acceso y los resultados antes de dejar de usar Windows. Conserva
el archivo de traslado solo en un respaldo privado. Puede ser necesario dar
permiso de lectura del archivo al UID 10001 del contenedor.

## Respaldos y mantenimiento

```sh
sh deploy/backup_ubuntu.sh
```

Copia el archivo de `backups/` a otro disco/equipo. Un respaldo dentro de la misma
VM no protege frente a perder su disco. Puedes programar el script con cron.
Para comprobar/restaurar un respaldo, usa otra base vacía y `pg_restore`; no
restaures encima del aula activa sin revisar y respaldar antes.

```sh
sh deploy/ubuntu.sh exec db createdb -U matematica academia_restaurada
sh deploy/ubuntu.sh exec -T db pg_restore -U matematica -d academia_restaurada --exit-on-error --single-transaction < backups/ARCHIVO.dump
```

La base restaurada es independiente; la aplicación sigue usando `matematica`.
Para detener los servicios conservando datos: `sh deploy/ubuntu.sh down`.
**No añadas `-v`**: borraría el volumen de la base. Al actualizar el código:
haz respaldo y ejecuta `sh deploy/ubuntu.sh up -d --build`.
No cambies la versión principal de PostgreSQL sin una migración planificada.

JARVIS requiere configurar por separado las claves de sus proveedores en
`.ubuntu.env` si usas esas funciones. El despliegue no vuelve gratuitos sus
servicios. Algunas funciones de micrófono del navegador requieren HTTPS incluso
en una LAN. La disponibilidad y velocidad dependen de los recursos de la VM.
