import unittest

import upt

from upt_macports.upt_macports import MacPortsHackagePackage


class TestMacPortsHackagePackage(unittest.TestCase):
    def setUp(self):
        self.package = MacPortsHackagePackage()
        self.package.upt_pkg = upt.Package('test-pkg', '13.37')

    def test_pkgname(self):
        expected = ['Foo', 'foo', 'Foo-bar', 'foo-bar']
        names = ['Foo', 'foo', 'Foo-bar', 'foo-bar']
        for (name, expected_name) in zip(names, expected):
            self.package.upt_pkg = upt.Package(name, '13.37')
            self.assertEqual(self.package._pkgname(), expected_name)

    def test_folder_name(self):
        expected = ['hs-foo', 'hs-foo', 'hs-foo-bar', 'hs-foo-bar']
        names = ['Foo', 'foo', 'Foo-bar', 'foo-bar']
        for (name, expected_name) in zip(names, expected):
            self.assertEqual(
                self.package._normalized_macports_folder(name), expected_name)


if __name__ == '__main__':
    unittest.main()
