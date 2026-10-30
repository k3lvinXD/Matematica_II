import json
import tempfile
import unittest
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable
from academy.database import metadata, users
from deploy.prepare_ubuntu import prepare
from deploy.transfer_academy import export_data, import_data, TABLES


class UbuntuTests(unittest.TestCase):
    def test_secrets_not_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            path = prepare(directory)
            old = path.read_bytes()
            self.assertIn(b'postgresql+psycopg://', old)
            with self.assertRaises(FileExistsError):
                prepare(directory)
            self.assertEqual(old, path.read_bytes())

    def test_schema_compiles_postgres(self):
        for table in metadata.sorted_tables:
            sql = str(CreateTable(table).compile(dialect=postgresql.dialect()))
            self.assertIn('CREATE TABLE', sql)
            if table in TABLES:
                self.assertIn('SERIAL', sql)

    def test_private_export_and_destination_guard(self):
        engine = create_engine('sqlite://')
        metadata.create_all(engine)
        with engine.begin() as db:
            db.execute(users.insert().values(id=7, name='José', email='j@example.com',
                       password_hash='test-only', role='student'))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'transfer.json'
            export_data(engine, path)
            data = json.loads(path.read_text(encoding='utf-8'))
            self.assertEqual(data['tables']['academic_users'][0]['id'], 7)
            self.assertNotIn('academic_login_limits', data['tables'])
            with self.assertRaises(FileExistsError):
                export_data(engine, path)
            with self.assertRaises(ValueError):
                import_data(engine, path)
        engine.dispose()
