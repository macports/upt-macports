import unittest

import requests_mock

import upt

from upt_macports.upt_macports import MacPortsPerlPackage


class TestMacPortsPerlPackage(unittest.TestCase):
    def setUp(self):
        self.package = MacPortsPerlPackage()
        self.package.upt_pkg = upt.Package('Foo-Bar', '13.37')
        self.package.upt_pkg.archives = [
            upt.Archive("https://democpan.org/authors/id/F/FO/FOOBAR/Foo-Bar-13.37.tar.gz")] # noqa
        self.check_url = "https://cpan.metacpan.org/modules/by-module/Foo/Foo-Bar-13.37.tar.gz" # noqa

    def test_pkgname(self):
        expected = ['Foo-bar', 'foo-bar', 'Foo-bar', 'foo-bar']
        names = ['Foo::bar', 'foo::bar', 'Foo-bar', 'foo-bar']
        for (name, expected_name) in zip(names, expected):
            self.package.upt_pkg = upt.Package(name, '13.37')
            self.assertEqual(self.package._pkgname(), expected_name)

    def test_folder_name(self):
        expected = ['p5-foo-bar', 'p5-foo-bar', 'p5-foo-bar', 'p5-foo-bar']
        names = ['Foo::bar', 'foo::bar', 'Foo-bar', 'foo-bar']
        for (name, expected_name) in zip(names, expected):
            self.assertEqual(
                self.package._normalized_macports_folder(name), expected_name)

    @requests_mock.mock()
    def test_missing_dist_pos1(self, requests):
        expected = ' ../../authors/id/F/FO/FOOBAR/'
        requests.head(self.check_url, status_code=400)
        self.assertEqual(self.package._cpandir(), expected)

    @requests_mock.mock()
    def test_distfile_found(self, requests):
        expected = ''
        requests.head(self.check_url, status_code=200)
        self.assertEqual(self.package._cpandir(), expected)

    @requests_mock.mock()
    def test_missing_distfile(self, requests):
        expected = ' # could not locate dist file'
        self.package.upt_pkg.archives = []
        self.assertEqual(self.package._cpandir(), expected)

    def test_jinja2_reqformat(self):
        req = upt.PackageRequirement('Require')
        self.assertEqual(self.package.jinja2_reqformat(req),
                         'p${perl5.major}-require')

    def test_homepage(self):
        upt_homepages = [
            '',
            'unknown',
            'https://github.com/Foo-Bar',
            'https://metacpan.org/pod/Foo-Bar'
        ]

        excpected_homepages = [
            None,
            None,
            'https://github.com/Foo-Bar',
            None
        ]

        for (upt_homepage, expected_homepage) in zip(upt_homepages,
                                                     excpected_homepages):
            self.package.upt_pkg.homepage = upt_homepage
            self.assertEqual(self.package.homepage, expected_homepage)


if __name__ == '__main__':
    unittest.main()
