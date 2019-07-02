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

    def test_folder_name(self):
        expected = ['py-foo', 'py-py-foo', 'py-pyfoo', 'py-pyfoo']
        names = ['foo', 'py-foo', 'pyfoo', 'pyFoo']
        for (name, expected_name) in zip(names, expected):
            self.assertEqual(
                self.package._normalized_macports_folder(name), expected_name)

    def test_py_root_name(self):
        url_names = ['foo', 'Foo', 'Foo', 'foo']
        pypi_names = ['foo', 'foo', 'pyFoo', 'py-Foo']
        urls = [
            'https://fakepypi.com/random/path/foo-13.37.tar.gz',
            'https://fakepypi.com/random/path/Foo-13.37.tar.gz',
            'https://fakepypi.com/random/path/Foo-13.37.tar.gz',
            'https://fakepypi.com/random/path/foo-13.37.tar.gz'
        ]
        for (url_name, pypi_name, url) in zip(url_names, pypi_names, urls):
            self.package.upt_pkg = upt.Package(pypi_name, '13.37')
            self.package.upt_pkg.archives = [upt.Archive(url)]
            if url_name != pypi_name:
                self.assertEqual(
                    self.package._python_root_name(), url_name)
            else:
                self.assertEqual(
                    self.package._python_root_name(), None)


if __name__ == '__main__':
    unittest.main()
