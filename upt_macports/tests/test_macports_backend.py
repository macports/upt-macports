import unittest
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


if __name__ == '__main__':
    unittest.main()
