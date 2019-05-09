import unittest
import upt
from upt_macports.upt_macports import MacPortsPackage


class TestMacPortsPackageLicenses(unittest.TestCase):
    def setUp(self):
        self.package = MacPortsPackage()
        self.package.upt_pkg = upt.Package('foo', '42')

    def test_no_licenses(self):
        self.package.upt_pkg.licenses = []
        expected = ''
        self.assertEqual(self.package.licenses, expected)

    def test_one_license(self):
        self.package.upt_pkg.licenses = [upt.licenses.BSDThreeClauseLicense()]
        expected = 'BSD'
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


if __name__ == '__main__':
    unittest.main()
