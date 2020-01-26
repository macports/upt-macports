import unittest
from unittest import mock
import upt
from upt_macports.upt_macports import MacPortsBackend


class TestMacPortsBackend(unittest.TestCase):
    def setUp(self):
        self.macports_backend = MacPortsBackend()
        self.macports_backend.frontend = 'pypi'

    @mock.patch('upt_macports.upt_macports.MacPortsBackend.package_versions',
                return_value=['1.2'])
    def test_current_version(self, m_package_versions):
        version = self.macports_backend.current_version(mock.Mock(), 'foo')
        self.assertEqual(version, '1.2')

    @mock.patch('upt_macports.upt_macports.MacPortsBackend.package_versions',
                return_value=[])
    @mock.patch('upt.Backend.current_version', return_value='1.2')
    def test_current_version_fallback(self, m_current_version,
                                      m_package_versions):
        version = self.macports_backend.current_version(mock.Mock(), 'foo')
        self.assertEqual(version, '1.2')

    def test_unhandled_frontend(self):
        upt_pkg = upt.Package('foo', '42')
        upt_pkg.frontend = 'invalid frontend'
        with self.assertRaises(upt.UnhandledFrontendError):
            self.macports_backend.create_package(upt_pkg)


class TestMacPortsPackageExist(unittest.TestCase):
    def setUp(self):
        self.macports_backend = MacPortsBackend()
        self.macports_backend.upt_pkg = upt.Package('foo', '42')
        self.macports_backend.frontend = 'pypi'

    @mock.patch('subprocess.getoutput')
    def test_port_found(self, mock_sub):
        expected = ['0.123']
        mock_sub.return_value = 'version: 0.123'
        self.assertEqual(
            self.macports_backend.package_versions('foo'), expected)

    @mock.patch('subprocess.getoutput')
    def test_port_not_found(self, mock_sub):
        expected = []
        mock_sub.return_value = 'Error: fake-error'
        self.assertEqual(
            self.macports_backend.package_versions('foo'), expected)

    @mock.patch('subprocess.getoutput')
    def test_port_outdated(self, mock_sub):
        expected = ['0.123']
        mock_sub.return_value = 'Warning: fake-warning \nversion: 0.123'
        self.assertEqual(
            self.macports_backend.package_versions('foo'), expected)

    @mock.patch('subprocess.getoutput')
    def test_port_error(self, mock_sub):
        mock_sub.return_value = 'bash: port: command not found'
        with self.assertRaises(SystemExit):
            self.macports_backend.package_versions('foo')


class TestMacPortsCpanVersion(unittest.TestCase):
    def setUp(self):
        self.macports_backend = MacPortsBackend()
        self.macports_backend.upt_pkg = upt.Package('foo', '42')
        self.macports_backend.frontend = 'cpan'

    def test_version_conversion(self):
        converted = ['1', '1.2.3', '1.200.0', '1.200.0', '1.20.0',
                     '1', '1.2.3', '1.200.0', '1.200.0', '1.20.0']
        upstream = ['1', '1.2.3', '1.2', '1.20', '1.02',
                    'v1', 'v1.2.3', 'v1.2', 'v1.20', 'v1.02']
        for mp_ver, cpan_ver in zip(upstream, converted):
            self.assertEqual(
                    self.macports_backend.standardize_CPAN_version(mp_ver),
                    cpan_ver)

    @mock.patch('upt.Backend.needs_requirement')
    def test_needs_requirement(self, mock_need_req):
        specifiers = {
            '>=42': '>=42',
            '<=42': '<=42',
            '!=42': '!=42',
            '==42': '==42',
            '>= 1.2, != 1.5, < 2.0': '>=1.200.0, !=1.500.0, <2.0.0',
            '>= 1.2, != 2, < 3.0': '>=1.200.0, !=2, <3.0.0'
        }

        for key, value in specifiers.items():
            req = upt.PackageRequirement('bar', key)
            self.macports_backend.needs_requirement(req, 'fake-phase')
            self.assertCountEqual(
                mock_need_req.call_args[0][0].specifier.split(', '),
                value.split(', ')
                )


if __name__ == '__main__':
    unittest.main()
