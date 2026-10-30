import os
import sys


def main():
    engine = None
    try:
        if len(os.getenv('SECRET_KEY', '')) < 32 or os.getenv('ACADEMY_ODBC_CONNECTION'):
            raise ValueError('Configuración inválida para Ubuntu')
        from deploy.ubuntu_app import app
        from academy.database import metadata
        engine = app.extensions.get('academy_engine')
        if engine is None or engine.dialect.name != 'postgresql':
            raise ValueError('Se requiere PostgreSQL')
        metadata.create_all(engine)
    except Exception as error:
        print('No se pudo iniciar PostgreSQL: ' + type(error).__name__, file=sys.stderr)
        return 1
    finally:
        if engine is not None:
            engine.dispose()
    os.execvp('gunicorn', ['gunicorn', '-c', 'gunicorn.conf.py', '--bind',
                          '0.0.0.0:10000', 'deploy.ubuntu_app:app'])


if __name__ == '__main__':
    sys.exit(main())
