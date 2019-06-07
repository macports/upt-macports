import unittest
import upt
from upt_macports.upt_macports import MacPortsPackage, logging
from unittest import mock
from io import StringIO


class TestMacPortsPackageLicenses(unittest.TestCase):
    def setUp(self):
        self.package = MacPortsPackage()
        self.package.upt_pkg = upt.Package('foo', '42')

    def test_no_licenses(self):
        self.package.upt_pkg.licenses = []
        expected = 'unknown'
        self.assertEqual(self.package.licenses, expected)

    def test_one_license(self):
        self.package.upt_pkg.licenses = [upt.licenses.BSDThreeClauseLicense()]
        expected = 'BSD'
        self.assertEqual(self.package.licenses, expected)

    def test_unknown_license(self):
        self.package.upt_pkg.licenses = [upt.licenses.ZlibLicense()]
        expected = 'unknown # MacPorts license unknown for zlib'
        self.assertEqual(self.package.licenses, expected)

    def test_bad_license(self):
        self.package.upt_pkg.licenses = [upt.licenses.UnknownLicense()]
        expected = 'unknown'
        self.assertEqual(self.package.licenses, expected)

    def test_multiple_license(self):
        self.package.upt_pkg.licenses = [
            upt.licenses.BSDTwoClauseLicense(),
            upt.licenses.BSDThreeClauseLicense()
        ]
        expected = 'BSD BSD'
        self.assertEqual(self.package.licenses, expected)

    # Logger tests

    @mock.patch('sys.stdout', new_callable=StringIO)
    def test_license_not_found(self, m_stdout):
        upt.log.create_logger(logging.DEBUG)
        self.package.upt_pkg.licenses = []
        self.package.licenses
        self.assertEqual(m_stdout.getvalue(), 'No license found\n')

    @mock.patch('sys.stdout', new_callable=StringIO)
    def test_license_detection_failed(self, m_stdout):
        upt.log.create_logger(logging.DEBUG)
        self.package.upt_pkg.licenses = [upt.licenses.UnknownLicense()]
        self.package.licenses
        self.assertEqual(m_stdout.getvalue(), 'upt failed to detect license\n')

    @mock.patch('sys.stdout', new_callable=StringIO)
    def test_license_detection_success(self, m_stdout):
        upt.log.create_logger(logging.DEBUG)
        self.package.upt_pkg.licenses = [upt.licenses.BSDThreeClauseLicense()]
        self.package.licenses
        self.assertEqual(m_stdout.getvalue(), 'Found license BSD\n')

    @mock.patch('sys.stderr', new_callable=StringIO)
    @mock.patch('sys.stdout', new_callable=StringIO)
    def test_license_conversion_error(self, m_stdout, m_stderr):
        upt.log.create_logger(logging.DEBUG)
        self.package.upt_pkg.licenses = [upt.licenses.ZlibLicense()]
        self.package.licenses
        err = 'MacPorts license unknown for zlib\n'
        info = 'Please report the error at https://github.com/macports/upt-macports\n' # noqa
        self.assertEqual(m_stdout.getvalue(), info)
        self.assertEqual(m_stderr.getvalue(), err)


class TestMacPortsPackageArchiveType(unittest.TestCase):
    def setUp(self):
        self.package = MacPortsPackage()
        self.package.upt_pkg = upt.Package('foo', '42')

    def test_no_archive(self):
        self.package.upt_pkg.archives = []
        expected = 'unknown'
        self.assertEqual(self.package.archive_type, expected)

    def test_known_archive(self):
        self.package.upt_pkg.archives = [upt.Archive("url.co/dir/file.tar.gz")]
        expected = 'gz'
        self.assertEqual(self.package.archive_type, expected)

    def test_unknown_archive(self):
        self.package.upt_pkg.archives = [upt.Archive("url.co/dir/file.rar")]
        expected = 'unknown'
        self.assertEqual(self.package.archive_type, expected)


if __name__ == '__main__':
    unittest.main()
