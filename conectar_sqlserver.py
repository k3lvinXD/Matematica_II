"""Conecta el aula a SQL Server Express local con autenticación de Windows.

Ejecutar desde una terminal normal del usuario, no desde un entorno aislado.
No borra bases, no cambia claves existentes y no abre puertos de red.
"""
from pathlib import Path
import os
import re
import secrets
import sqlite3
import sys
from datetime import datetime
from contextlib import closing

ROOT = Path(__file__).resolve().parent
SERVER = r'localhost\SQLEXPRESS'
DATABASE = 'MatematicaII'
DRIVER = 'ODBC Driver 18 for SQL Server'
CURRENT_STEP = 'Comprobar dependencias'


def progress(message):
    global CURRENT_STEP
    CURRENT_STEP = message
    print(message, flush=True)


def diagnostic(error):
    original = getattr(error, 'orig', error)
    details = ' | '.join(str(item) for item in getattr(original, 'args', ()))
    details = re.sub(r'(?i)(PWD|PASSWORD|API_KEY|TOKEN|SECRET)\s*[=:]\s*[^;\s]+', r'\1=[oculto]', details)
    return 'Paso: ' + CURRENT_STEP + '\nTipo: ' + type(original).__name__ + '\nDetalle SQL: ' + details[:4000]


def connection_string(database):
    # TrustServerCertificate se limita a esta instancia LOCAL de desarrollo.
    return (f'DRIVER={{{DRIVER}}};SERVER={SERVER};DATABASE={database};'
            'Trusted_Connection=yes;Encrypt=yes;TrustServerCertificate=yes;')


def verify_sqlite_empty():
    source = ROOT / 'instance' / 'academia.sqlite3'
    if not source.exists():
        return
    with closing(sqlite3.connect(source.as_uri() + '?mode=ro', uri=True)) as db:
        tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        for table in ('academic_users', 'academic_courses', 'academic_enrollments', 'academic_exams', 'academic_attempts'):
            if table in tables and db.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]:
                raise RuntimeError('SQLite tiene datos. No se cambia la conexión: primero hay que migrarlos. No se borró nada.')


def updated_env(content, connection):
    # Conserva exactamente las líneas de otras variables, incluidas claves privadas.
    lines = content.splitlines(keepends=True)
    newline = '\r\n' if '\r\n' in content else '\n'
    result = []
    found = False
    for line in lines:
        if re.match(r'^\s*(?:export\s+)?ACADEMY_ODBC_CONNECTION\s*=', line):
            if not found:
                result.append("ACADEMY_ODBC_CONNECTION='" + connection + "'" + newline)
                found = True
        else:
            result.append(line)
    if not found:
        if result and not result[-1].endswith(('\n', '\r')):
            result.append(newline)
        result.append("ACADEMY_ODBC_CONNECTION='" + connection + "'" + newline)
    return ''.join(result)


def write_configuration(connection):
    path = ROOT / '.env'
    original = path.read_bytes() if path.exists() else b''
    text = original.decode('utf-8-sig')
    updated = updated_env(text, connection).encode('utf-8')
    if original.startswith(b'\xef\xbb\xbf'):
        updated = b'\xef\xbb\xbf' + updated
    if updated == original:
        return None
    private = ROOT / 'instance'
    private.mkdir(exist_ok=True)
    backup = private / ('env-antes-sqlserver-' + datetime.now().strftime('%Y%m%d-%H%M%S') + '-' + secrets.token_hex(3) + '.bak')
    if original:
        backup.write_bytes(original)
    temporary = private / ('sqlserver-env-' + secrets.token_hex(6) + '.tmp')
    try:
        temporary.write_bytes(updated)
        if (path.read_bytes() if path.exists() else b'') != original:
            raise RuntimeError('El .env cambió durante la operación. No se reemplazó.')
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
    return backup if original else None


def run():
    try:
        import pyodbc
        from sqlalchemy import create_engine, inspect, insert, select, update
        from sqlalchemy.engine import URL
        from academy.database import metadata, users, courses, enrollments, exams, attempts
    except ImportError as error:
        raise RuntimeError('Faltan dependencias. Ejecuta: python -m pip install -r requirements-sqlserver.txt') from error
    if DRIVER not in pyodbc.drivers():
        raise RuntimeError('Instala Microsoft ODBC Driver 18 para SQL Server (64 bits).')
    target = connection_string(DATABASE)
    if os.getenv('ACADEMY_ODBC_CONNECTION') and os.environ['ACADEMY_ODBC_CONNECTION'] != target:
        raise RuntimeError('Existe otra ACADEMY_ODBC_CONNECTION en las variables de Windows. Revísala antes de continuar.')
    verify_sqlite_empty()
    progress('1/5 Conectando a SQL Server con tu usuario de Windows…')
    master = pyodbc.connect(connection_string('master'), timeout=8, autocommit=True)
    try:
        progress('2/5 Comprobando la base MatematicaII…')
        # Consulta fija: no hay entrada de usuario. Cierra el resultado antes del DDL.
        cursor = master.cursor()
        try:
            exists = cursor.execute("SELECT DB_ID(N'MatematicaII')").fetchone()[0] is not None
        finally:
            cursor.close()
        if not exists:
            progress('2/5 Creando la base MatematicaII…')
            cursor = master.cursor()
            try:
                cursor.execute('CREATE DATABASE [MatematicaII]')
            finally:
                cursor.close()
            print('Base MatematicaII creada.')
        else:
            print('La base MatematicaII ya existe; se conservarán sus datos.')
    finally:
        master.close()
    engine = create_engine(URL.create('mssql+pyodbc', query={'odbc_connect': target}),
                           pool_pre_ping=True, hide_parameters=True, connect_args={'timeout': 8})
    try:
        progress('3/5 Conectando a MatematicaII y verificando tablas…')
        existing = set(inspect(engine).get_table_names())
        unrelated = existing - set(metadata.tables)
        if unrelated:
            raise RuntimeError('MatematicaII contiene tablas de otro sistema. No se modifica la configuración.')
        metadata.create_all(engine)
        # Comprueba identidades, Unicode, relaciones y actualización JSON.
        # Todo el contenido de prueba se revierte al terminar.
        progress('4/5 Probando lectura y escritura sin conservar registros de prueba…')
        with engine.connect() as db:
            transaction = db.begin()
            try:
                token = secrets.token_hex(10)
                teacher = db.execute(insert(users).values(name='Prueba de conexión ñ', email=token+'-teacher@example.invalid', password_hash='prueba-no-utilizable', role='teacher')).inserted_primary_key[0]
                student = db.execute(insert(users).values(name='Prueba estudiante', email=token+'-student@example.invalid', password_hash='prueba-no-utilizable', role='student')).inserted_primary_key[0]
                course = db.execute(insert(courses).values(teacher_id=teacher, title='Verificación temporal', join_code=token)).inserted_primary_key[0]
                db.execute(insert(enrollments).values(course_id=course, student_id=student))
                exam = db.execute(insert(exams).values(course_id=course, title='Prueba', topic='partials', difficulty='basic', duration=5, state='draft', questions_json='[]', created_at=0)).inserted_primary_key[0]
                attempt = db.execute(insert(attempts).values(exam_id=exam, student_id=student, started_at=0, deadline=1, answers_json='{}')).inserted_primary_key[0]
                changed = db.execute(update(attempts).where(attempts.c.id==attempt, attempts.c.answers_json=='{}').values(answers_json='{"verificado":true}', score=1))
                if changed.rowcount != 1 or db.execute(select(users.c.name).where(users.c.id==teacher)).scalar_one() != 'Prueba de conexión ñ':
                    raise RuntimeError('La comprobación de lectura/escritura no fue correcta.')
            finally:
                transaction.rollback()
        progress('5/5 Guardando la conexión del proyecto…')
        backup = write_configuration(target)
        print('OK: seis tablas verificadas; lectura y escritura correctas. Datos de prueba revertidos.')
        print('Proyecto conectado a SQL Server: localhost\\SQLEXPRESS / MatematicaII.')
        if backup:
            print('Respaldo privado del .env guardado en instance. No publiques esa carpeta.')
        print('Reinicia el servidor de Flask. En SSMS pulsa Actualizar sobre Databases.')
    finally:
        engine.dispose()


if __name__ == '__main__':
    try:
        run()
    except Exception as error:
        print('No se completó la configuración. La conexión anterior del proyecto se conserva.', file=sys.stderr)
        if isinstance(error, RuntimeError):
            print(str(error), file=sys.stderr)
        else:
            detail = diagnostic(error)
            print(detail, file=sys.stderr)
            try:
                private = ROOT / 'instance'
                private.mkdir(exist_ok=True)
                (private / 'sqlserver-diagnostico.log').write_text(detail, encoding='utf-8')
                print('Diagnóstico guardado en instance/sqlserver-diagnostico.log', file=sys.stderr)
            except OSError:
                pass
        sys.exit(1)
