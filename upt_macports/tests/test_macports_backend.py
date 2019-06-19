import unittest
from unittest import mock
import upt
from upt_macports.upt_macports import MacPortsBackend


class TestMacPortsBackend(unittest.TestCase):
    def setUp(self):
        self.macports_backend = MacPortsBackend()

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


if __name__ == '__main__':
    unittest.main()
