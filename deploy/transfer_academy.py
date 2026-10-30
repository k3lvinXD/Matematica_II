"""Exportación privada y carga transaccional en PostgreSQL vacío."""
import argparse
import json
import os
from pathlib import Path
from sqlalchemy import select, func, text
from academy.database import metadata

TABLES = [table for table in metadata.sorted_tables if table.name != 'academic_login_limits']


def export_data(engine, path):
    # Durante la exportación detén Flask para que ninguna entrega cambie entre tablas.
    with engine.connect() as db:
        data = {'version': 1, 'tables': {t.name: [dict(row) for row in
                db.execute(select(t)).mappings()] for t in TABLES}}
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w', encoding='utf-8') as stream:
        json.dump(data, stream, ensure_ascii=False)


def import_data(engine, path):
    if engine.dialect.name != 'postgresql':
        raise ValueError('La importación requiere PostgreSQL')
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    if data.get('version') != 1 or set(data.get('tables', {})) != {t.name for t in TABLES}:
        raise ValueError('Formato de traslado inválido')
    metadata.create_all(engine)
    with engine.begin() as db:
        # Evita que otro proceso inserte mientras se comprueba el destino vacío.
        db.execute(text('LOCK TABLE ' + ', '.join(t.name for t in TABLES) + ' IN ACCESS EXCLUSIVE MODE'))
        if any(db.execute(select(func.count()).select_from(t)).scalar_one() for t in TABLES):
            raise ValueError('El destino contiene datos: no se sobrescribirá')
        for table in TABLES:
            rows = data['tables'][table.name]
            if not isinstance(rows, list):
                raise ValueError('Tabla inválida')
            expected = set(table.columns.keys())
            if any(not isinstance(row, dict) or set(row) != expected for row in rows):
                raise ValueError('Columnas inválidas')
            for offset in range(0, len(rows), 200):
                db.execute(table.insert(), rows[offset:offset + 200])
            # RESTART es transaccional; el siguiente registro no colisiona con IDs importados.
            next_id = max((row['id'] for row in rows), default=0) + 1
            if not isinstance(next_id, int) or next_id < 1:
                raise ValueError('Identificador inválido')
            db.execute(text(f'ALTER SEQUENCE {table.name}_id_seq RESTART WITH {next_id}'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['export', 'import'])
    parser.add_argument('path')
    args = parser.parse_args()
    from app import app
    engine = app.extensions.get('academy_engine')
    if engine is None:
        raise SystemExit('No hay una base configurada.')
    try:
        (export_data if args.action == 'export' else import_data)(engine, args.path)
        print('Traslado completado. El origen se conserva sin cambios.')
    except Exception as error:
        # No exponer filas, hashes de contraseña o credenciales del driver.
        raise SystemExit('No se completó el traslado (' + type(error).__name__ +
                         '). Revisa el archivo y que el destino esté vacío.') from None
    finally:
        engine.dispose()


if __name__ == '__main__':
    main()
