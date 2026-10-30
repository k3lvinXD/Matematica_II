"""Arranque Docker: valida la configuración y SQL antes de iniciar Gunicorn."""
import os
import sys


def odbc_fields(connection):
    fields = {}
    index = 0
    while index < len(connection):
        while index < len(connection) and connection[index] in '; \r\n\t':
            index += 1
        if index == len(connection):
            break
        end = connection.find('=', index)
        if end < 0:
            raise ValueError('La conexión ODBC contiene un campo sin valor.')
        key = connection[index:end].strip().lower()
        index = end + 1
        while index < len(connection) and connection[index].isspace():
            index += 1
        value = ''
        if index < len(connection) and connection[index] == '{':
            index += 1
            while True:
                if index >= len(connection):
                    raise ValueError('La conexión ODBC contiene una llave sin cerrar.')
                char = connection[index]
                index += 1
                if char == '}':
                    if index < len(connection) and connection[index] == '}':
                        value += '}'
                        index += 1
                        continue
                    break
                value += char
            while index < len(connection) and connection[index].isspace():
                index += 1
            if index < len(connection) and connection[index] != ';':
                raise ValueError('Separador ODBC inválido.')
        else:
            end = connection.find(';', index)
            if end < 0:
                end = len(connection)
            value = connection[index:end].strip()
            index = end
        if not key or key in fields:
            raise ValueError('La conexión ODBC tiene un campo vacío o repetido.')
        fields[key] = value
    return fields


def validate_environment(env):
    if len(env.get('SECRET_KEY', '')) < 32:
        raise ValueError('Configura SECRET_KEY con al menos 32 caracteres en Render.')
    connection = env.get('ACADEMY_ODBC_CONNECTION', '')
    if not connection:
        raise ValueError('Falta ACADEMY_ODBC_CONNECTION con la base SQL alojada.')
    fields = odbc_fields(connection)
    if fields.get('driver', '').lower() != 'odbc driver 18 for sql server':
        raise ValueError('Usa DRIVER={ODBC Driver 18 for SQL Server}.')
    server = fields.get('server', '').lower()
    address = server.removeprefix('tcp:').split('\\')[0].split(',')[0]
    if not address or address in {'.', '(local)', 'localhost', '127.0.0.1', '::1'} or server.startswith(('lpc:', 'np:')):
        raise ValueError('Configura el servidor SQL alojado; localhost no conecta a tu laptop desde Render.')
    if not fields.get('database') or fields['database'].lower() in {'master', 'tempdb', 'model', 'msdb'}:
        raise ValueError('Indica una base propia del proyecto, no una base del sistema.')
    if fields.get('trusted_connection', '').lower() in {'yes', 'true', '1'}:
        raise ValueError('La autenticación de Windows de tu laptop no está disponible en Render.')
    if fields.get('encrypt', '').lower() not in {'yes', 'true', 'mandatory', 'strict'}:
        raise ValueError('La conexión remota debe usar Encrypt=yes.')
    if fields.get('trustservercertificate', 'no').lower() not in {'no', 'false', '0'}:
        raise ValueError('Usa TrustServerCertificate=no y un certificado válido en el servidor remoto.')
    try:
        port = int(env.get('PORT', '10000'))
    except ValueError:
        raise ValueError('PORT debe ser un número.') from None
    if not 1 <= port <= 65535:
        raise ValueError('PORT está fuera de rango.')
    return port


def main():
    try:
        port = validate_environment(os.environ)
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 1
    engine = None
    try:
        from app import app
        from academy.database import metadata
        from sqlalchemy import text
        engine = app.extensions.get('academy_engine')
        if engine is None or engine.dialect.name != 'mssql':
            raise RuntimeError('No se inicializó SQL Server.')
        # El proceso de arranque termina después de esto; no conserva conexiones
        # cuando Gunicorn crea sus trabajadores. No migra ni elimina tablas.
        metadata.create_all(engine)
        with engine.connect() as db:
            db.execute(text('SELECT 1')).scalar_one()
    except Exception as error:
        # No volcar excepciones del driver: podrían incluir datos de conexión.
        print('No se pudo inicializar la base remota (' + type(error).__name__ + '). Revisa conexión, firewall y permisos de tablas.', file=sys.stderr)
        return 1
    finally:
        if engine is not None:
            engine.dispose()
    print('SQL Server verificado. Iniciando la página.', flush=True)
    os.execvp('gunicorn', ['gunicorn', '-c', 'gunicorn.conf.py', '--bind', f'0.0.0.0:{port}', 'app:app'])


if __name__ == '__main__':
    sys.exit(main())
