import unittest

import upt

from upt_macports.upt_macports import MacPortsRubyPackage


class TestMacPortsRubyPackage(unittest.TestCase):
    def setUp(self):
        self.package = MacPortsRubyPackage()
        self.package.upt_pkg = upt.Package('test-pkg', '13.37')

    def test_pkgname(self):
        expected = ['Foo', 'foo', 'Foo-bar', 'foo-bar']
        names = ['Foo', 'foo', 'Foo-bar', 'foo-bar']
        for (name, expected_name) in zip(names, expected):
            self.package.upt_pkg = upt.Package(name, '13.37')
            self.assertEqual(self.package._pkgname(), expected_name)


if __name__ == '__main__':
    unittest.main()
