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

    def test_folder_name(self):
        expected = ['rb-foo', 'rb-foo', 'rb-foo-bar', 'rb-foo-bar']
        names = ['Foo', 'foo', 'Foo-bar', 'foo-bar']
        for (name, expected_name) in zip(names, expected):
            self.assertEqual(
                self.package._normalized_macports_folder(name), expected_name)

    def test_jinja2_reqformat(self):
        req = upt.PackageRequirement('Require')
        self.assertEqual(self.package.jinja2_reqformat(req),
                         'rb${ruby.suffix}-require')

    def test_homepage(self):
        upt_homepages = [
            '',
            'unknown',
            'https://github.com/test-pkg',
        ]

        excpected_homepages = [
            'https://rubygems.org/gems/test-pkg',
            'https://rubygems.org/gems/test-pkg',
            'https://github.com/test-pkg'
        ]

        for (upt_homepage, expected_homepage) in zip(upt_homepages,
                                                     excpected_homepages):
            self.package.upt_pkg.homepage = upt_homepage
            self.assertEqual(self.package.homepage, expected_homepage)


if __name__ == '__main__':
    unittest.main()
