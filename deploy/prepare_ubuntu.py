"""Genera credenciales privadas una sola vez, en el servidor Ubuntu."""
import os
import secrets
from pathlib import Path


def prepare(root):
    target = Path(root) / '.ubuntu.env'
    password = secrets.token_hex(32)
    content = (f'POSTGRES_PASSWORD={password}\nSECRET_KEY={secrets.token_hex(48)}\n'
               f'ACADEMY_DATABASE_URL=postgresql+psycopg://matematica:{password}@db:5432/matematica\n'
               'ACADEMY_PRODUCTION=1\nACADEMY_LOCAL_HTTP=1\n')
    # O_EXCL evita reemplazar credenciales de una base ya inicializada.
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as stream:
        stream.write(content)
    return target


if __name__ == '__main__':
    try:
        prepare(Path(__file__).resolve().parents[1])
        print('Configuración creada en .ubuntu.env. No la subas a GitHub.')
    except FileExistsError:
        print('La configuración ya existe; se conserva sin cambios.')
