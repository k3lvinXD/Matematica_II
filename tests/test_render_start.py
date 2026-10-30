import unittest
from deploy.render_start import validate_environment, odbc_fields


class RenderStartupTests(unittest.TestCase):
    def env(self, **changes):
        return {'SECRET_KEY': 'x'*32, 'ACADEMY_ODBC_CONNECTION':
                'DRIVER={ODBC Driver 18 for SQL Server};SERVER=tcp:example.database.windows.net,1433;DATABASE=MatematicaII;UID=test;PWD={fake;password}}value};Encrypt=yes;TrustServerCertificate=no;', **changes}

    def test_remote_connection_and_escaped_password(self):
        self.assertEqual(validate_environment(self.env()), 10000)
        self.assertEqual(odbc_fields(self.env()['ACADEMY_ODBC_CONNECTION'])['pwd'], 'fake;password}value')

    def test_explicit_port(self):
        self.assertEqual(validate_environment(self.env(PORT='12345')), 12345)

    def test_secret_is_required(self):
        for value in ['', 'short']:
            with self.assertRaises(ValueError): validate_environment(self.env(SECRET_KEY=value))

    def test_local_windows_connection_rejected(self):
        for server in ['localhost\\SQLEXPRESS', '.', 'tcp:127.0.0.1,1433', 'lpc:DELL\\SQLEXPRESS']:
            connection = self.env()['ACADEMY_ODBC_CONNECTION'].replace('tcp:example.database.windows.net,1433', server)
            with self.assertRaises(ValueError): validate_environment(self.env(ACADEMY_ODBC_CONNECTION=connection))

    def test_tls_and_system_database(self):
        original = self.env()['ACADEMY_ODBC_CONNECTION']
        for connection in [original.replace('Encrypt=yes', 'Encrypt=no'),
                           original.replace('TrustServerCertificate=no', 'TrustServerCertificate=yes'),
                           original.replace('DATABASE=MatematicaII', 'DATABASE=master'),
                           original+'Trusted_Connection=yes;']:
            with self.assertRaises(ValueError): validate_environment(self.env(ACADEMY_ODBC_CONNECTION=connection))

    def test_invalid_port_and_empty_connection(self):
        for changes in [{'PORT':'not-a-port'}, {'PORT':'0'}, {'PORT':'70000'}, {'ACADEMY_ODBC_CONNECTION':''}]:
            with self.assertRaises(ValueError): validate_environment(self.env(**changes))

    def test_invalid_odbc_does_not_echo_secret(self):
        for connection in ['PWD={private-unclosed', 'PWD=private;PWD=another', 'PWD={private}garbage']:
            with self.assertRaises(ValueError) as error: odbc_fields(connection)
            self.assertNotIn('private', str(error.exception))


if __name__ == '__main__':
    unittest.main()
