import unittest

import upt

from upt_macports.upt_macports import MacPortsPythonPackage


class TestMacPortsPythonPackage(unittest.TestCase):
    def setUp(self):
        self.package = MacPortsPythonPackage()
        self.package.upt_pkg = upt.Package('test-pkg', '13.37')

    def test_pkgname(self):
        expected = ['py-foo', 'py-py-foo', 'py-pyfoo', 'py-pyfoo']
        names = ['foo', 'py-foo', 'pyfoo', 'pyFoo']
        for (name, expected_name) in zip(names, expected):
            self.package.upt_pkg = upt.Package(name, '13.37')
            self.assertEqual(self.package._pkgname(), expected_name)


if __name__ == '__main__':
    unittest.main()
