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


class TestDirectoryCreation(unittest.TestCase):
    def setUp(self):
        self.package = MacPortsPackage()
        self.package.upt_pkg = upt.Package('foo', '42')
        self.package.upt_pkg.frontend = 'pypi'
        self.package.category = 'python'

    @mock.patch('os.makedirs')
    @mock.patch.object(MacPortsPackage, '_normalized_macports_folder',
                       create=True, return_value='py-foo')
    def test_create_directories_output(self, folder_name, m_mkdir):
        self.package._create_output_directories(self.package.upt_pkg,
                                                '/ports/')
        m_mkdir.assert_called_with('/ports/python/py-foo', exist_ok=True)

    @mock.patch('os.makedirs', side_effect=PermissionError)
    @mock.patch.object(MacPortsPackage, '_normalized_macports_folder',
                       create=True, return_value='py-foo')
    def test_create_directories_permission_error(self, folder_name, m_mkdir):
        with self.assertRaises(SystemExit):
            self.package._create_output_directories(self.package.upt_pkg,
                                                    '/ports/')

    @mock.patch.object(MacPortsPackage, '_render_makefile_template',
                       side_effect=PermissionError)
    @mock.patch.object(MacPortsPackage, '_create_output_directories')
    @mock.patch.object(MacPortsPackage, '_create_portfile')
    def test_render_makefile_error(self, portfile, outdir, render):
        with self.assertRaises(PermissionError):
            self.package.create_package(mock.Mock(), 'path')
        render.assert_called()
        outdir.assert_not_called()
        portfile.assert_not_called()


class TestFileCreation(unittest.TestCase):
    def setUp(self):
        self.package = MacPortsPackage()
        self.package.output_dir = '/outdir'
        self.package.upt_pkg = upt.Package('foo', '42')

    @mock.patch('builtins.open', new_callable=mock.mock_open)
    def test_portfile_creation(self, m_open):
        fn = 'upt_macports.upt_macports.MacPortsPackage._render_makefile_template' # noqa
        with mock.patch(fn, return_value='Portfile content'):
            self.package._create_portfile('Portfile content')
            m_open.assert_called_once_with('/outdir/Portfile', 'x',
                                           encoding='utf-8')
            m_open().write.assert_called_once_with('Portfile content')

    @mock.patch('builtins.open', side_effect=FileExistsError)
    def test_portfile_file_exists(self, m_open):
        with self.assertRaises(SystemExit):
            self.package._create_portfile('Portfile content')


class TestMacPortsPackageArchiveType(unittest.TestCase):
    def setUp(self):
        self.package = MacPortsPackage()
        self.package.upt_pkg = upt.Package('foo', '42')

    def test_no_archive(self):
        self.package.upt_pkg.archives = []
        self.package.upt_pkg.frontend = 'frontend'
        self.package.archive_format = upt.ArchiveType.SOURCE_TARGZ
        expected = 'unknown'
        self.assertEqual(self.package.archive_type, expected)

    def test_known_archive(self):
        self.package.upt_pkg.archives = [upt.Archive("url.co/dir/file.tar.gz")]
        self.package.upt_pkg.frontend = 'frontend'
        self.package.archive_format = upt.ArchiveType.SOURCE_TARGZ
        expected = 'gz'
        self.assertEqual(self.package.archive_type, expected)

    def test_unknown_archive(self):
        self.package.upt_pkg.archives = [upt.Archive("url.co/dir/file.rar")]
        self.package.upt_pkg.frontend = 'frontend'
        self.package.archive_format = upt.ArchiveType.RUBYGEM
        expected = 'unknown'
        self.assertEqual(self.package.archive_type, expected)


if __name__ == '__main__':
    unittest.main()
