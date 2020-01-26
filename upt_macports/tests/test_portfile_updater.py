# Copyright 2021      Cyril Roelandt
#
# Licensed under the 3-clause BSD license. See the LICENSE file.
import io
import unittest
from unittest import mock

import upt
from upt_macports.portfile_updater import PortfileUpdater
from upt_macports.upt_macports import MacPortsPythonPackage


class TestPortfileUpdater(unittest.TestCase):
    def setUp(self):
        handle = io.StringIO('')
        self.updater = PortfileUpdater(handle, mock.Mock(),
                                       MacPortsPythonPackage)

    def test_update_version(self):
        test_cases = {
            'version 1.2.3': 'version 4.5.6',
            '   version    1.2.3': '   version    4.5.6',
            'github.setup auth pkg 1.2.3': 'github.setup auth pkg 4.5.6',
            'bitbucket.setup auth pkg 1.2.3': 'bitbucket.setup auth pkg 4.5.6',
            'perl5.setup foo 1.2.3': 'perl5.setup foo 4.5.6',
            'ruby.setup foo 1.2.3 gem': 'ruby.setup foo 4.5.6 gem',
            'platforms darwin': 'platforms darwin',
        }

        for before, after in test_cases.items():
            out = self.updater._update_version(before, '1.2.3', '4.5.6')
            self.assertEqual(out, after)

    def test_update_revision(self):
        test_cases = {
            'revision      1\n': 'revision      0\n',
            'revision      0\n': 'revision      0\n',
            'revision 1\nrevision 2\n': 'revision 0\nrevision 2\n',
            'foo\n': 'foo\n',
        }
        for before, after in test_cases.items():
            self.assertEqual(self.updater._update_revision(before), after)

    def test_update_checksums(self):
        # No checksum in the Portfile
        portfile = 'version 1.2\nrevision 0\n'
        out = self.updater._update_checksums(portfile, mock.Mock())
        self.assertEqual(out, portfile)

        # Build upt.Archive objects
        oldrmd = '91bf89c0493ad2caa8ed29372972e2e887f84bb8'
        oldsha = '2e50876bcdd74517e7b71f3e7a76102050edec255b3983403f1a63e7c8a41e7a'  # noqa
        newrmd = '770c41f726e57b64e2c27266e6b0cf8b7bf895ab'
        newsha = '2f52bbb095baa858b3273d851de5cc25a4470351bdfe675b2d5b997e3145c2c4'  # noqa
        oldsize = 42
        newsize = 1337
        new = upt.Archive('url', size=newsize, rmd160=newrmd, sha256=newsha)

        # A single hash in the Portfile
        portfile = f'checksums     rmd160  {oldrmd} \n'
        expected = f'checksums     rmd160  {newrmd} \\\n'
        expected += f'              sha256  {newsha} \\\n'
        expected += f'              size    {newsize}\n'
        out = self.updater._update_checksums(portfile, new)
        self.assertEqual(out, expected)

        # A more common case
        portfile = f'''
    checksums   md5 abcdef \\
                rmd160 {oldrmd} \\
                sha256 {oldsha} \\
                size   {oldsize}
'''
        expected = f'''
    checksums   rmd160  {newrmd} \\
                sha256  {newsha} \\
                size    {newsize}
'''
        out = self.updater._update_checksums(portfile, new)
        self.assertEqual(out, expected)

    def test_get_current_dependencies(self):
        portfile = '''
depends_lib-append libdep1

    depends_test-append testdep1 \\
                        testdep2
'''

        # lib phase
        block, deps = self.updater._get_current_dependencies(portfile, 'lib')
        self.assertEqual(block, 'depends_lib-append libdep1\n')
        self.assertListEqual(deps, ['libdep1'])

        # test phase
        block, deps = self.updater._get_current_dependencies(portfile, 'test')
        expected = '''    depends_test-append testdep1 \\
                        testdep2\n'''
        self.assertEqual(block, expected)
        self.assertListEqual(deps, ['testdep1', 'testdep2'])

        # build phase
        block, deps = self.updater._get_current_dependencies(portfile, 'build')
        self.assertEqual(block, '')
        self.assertEqual(deps, [])

    def test_get_current_dependencies_corner_cases(self):
        portfile = '''
depends_build-append port:foo port:bar

depends_lib-append \\
    port:baz
'''

        # build phase
        block, deps = self.updater._get_current_dependencies(portfile, 'build')
        self.assertEqual(block, 'depends_build-append port:foo port:bar\n')
        self.assertEqual(deps, ['port:foo', 'port:bar'])

        # lib phase
        block, deps = self.updater._get_current_dependencies(portfile, 'lib')
        self.assertEqual(block, 'depends_lib-append \\\n    port:baz\n')
        self.assertListEqual(deps, ['port:baz'])

    def test_remove_deleted_dependencies(self):
        current = ['foo', 'bar']
        deleted = ['bar', 'baz']
        expected = ['foo']
        out = self.updater._remove_deleted_dependencies(current, deleted)
        self.assertListEqual(out, expected)

    def test_add_new_dependencies(self):
        current = ['foo', 'bar']
        added = ['bar', 'baz']
        expected = ['foo', 'bar', 'baz']
        out = self.updater._add_new_dependencies(current, added)
        self.assertListEqual(out, expected)

    def test_format_like(self):
        # No deps
        self.assertEqual(self.updater._format_like([], mock.Mock(), 'lib'), '')

        # The block did not exist in the old Portfile and must be added
        expected = 'depends_lib-append port:foo\n'
        out = self.updater._format_like(['port:foo'], '', 'lib')
        self.assertEqual(out, expected)

        # No dependency on the first line
        old = 'depends_lib-append \\\nport:foo\n'
        expected = '''depends_lib-append \\
                   port:bar\n'''
        out = self.updater._format_like(['port:bar'], old, 'lib')
        self.assertEqual(out, expected)

        # There are spaces before the block
        deps = [
            'port:foo', 'port:bar', 'port:baz'
        ]
        old_depends_block = '''    depends_lib-append   port:foo  \\
        port:bar
'''
        expected = '''    depends_lib-append   port:foo \\
        port:bar \\
        port:baz
'''
        out = self.updater._format_like(deps, old_depends_block, 'lib')
        self.assertEqual(out, expected)

        # The original depends block is a single line
        old_depends_block = 'depends_test-append port:foo\n'
        expected = '''depends_test-append port:foo \\
                    port:bar \\
                    port:baz
'''
        out = self.updater._format_like(deps, old_depends_block, 'test')
        self.assertEqual(out, expected)

    def test_update_dependencies(self):
        old_portfile = '''version 1.2.3

depends_build-append  \\
    port:build-foo

    depends_lib-append port:lib-foo \\
                       port:lib-bar

platforms darwin
'''

        expected = '''version 1.2.3

depends_build-append  \\
    port:build-foo

    depends_lib-append port:lib-foo \\
                       port:lib-baz

platforms darwin
# TODO: Move this
depends_test-append port:test-foo
'''

        def reqformat(req):
            return f'port:{req}'

        oldpkg = upt.Package('somepkg', '1.2.3')
        oldpkg.requirements = {
            'build': [
                upt.PackageRequirement('build-foo')
            ],
            'run': [
                upt.PackageRequirement('lib-foo'),
                upt.PackageRequirement('lib-bar'),
            ]
        }
        newpkg = upt.Package('somepkg', '4.5.6')
        newpkg.requirements = {
            'build': [
                upt.PackageRequirement('build-foo')
            ],
            'run': [
                upt.PackageRequirement('lib-foo'),
                upt.PackageRequirement('lib-baz'),
            ],
            'test': [
                upt.PackageRequirement('test-foo'),
            ],
        }
        pdiff = upt.PackageDiff(oldpkg, newpkg)
        out = self.updater._update_dependencies(old_portfile, pdiff,
                                                lambda x: x)
        self.assertEqual(out, expected)

    def test_update_portfile_content_beautifulsoup(self):
        old_portfile = '''\
version 4.6.0

checksums           rmd160  6452de577ef676636fb0be79eba9224cafd5622d \\
                    size    160846
if {${name} ne ${subport}} {
    depends_lib-append  port:py${python.version}-setuptools
}
'''
        expected_portfile = '''\
version 4.9.1

checksums           rmd160  b72ed53263f07c843ce34513a9d62128051e2fc3 \\
                    sha256  73cc4d115b96f79c7d77c1c7f7a0a8d4c57860d1041df407dd1aae7f07a77fd7 \\
                    size    374759
if {${name} ne ${subport}} {
    depends_lib-append  port:py${python.version}-setuptools \\
                        port:py${python.version}-soupsieve
}
'''  # noqa
        oldpkg = upt.Package('beautifulsoup4', '4.6.0')
        oldpkg.frontend = 'pypi'
        oldpkg.requirements = {}
        oldpkg.archives = [
            upt.Archive('url',
                        rmd160='6452de577ef676636fb0be79eba9224cafd5622d',
                        sha256='808b6ac932dccb0a4126558f7dfdcf41710dd44a4ef497a0bb59a77f9f078e89',  # noqa
                        size=160846)
        ]
        newpkg = upt.Package('beautifulsoup4', '4.9.1')
        newpkg.frontend = 'pypi'
        newpkg.requirements = {
            'run': [
                upt.PackageRequirement('soupsieve'),
            ],
        }
        newpkg.archives = [
            upt.Archive('url',
                        rmd160='b72ed53263f07c843ce34513a9d62128051e2fc3',
                        sha256='73cc4d115b96f79c7d77c1c7f7a0a8d4c57860d1041df407dd1aae7f07a77fd7',  # noqa
                        size=374759)
        ]
        pdiff = upt.PackageDiff(oldpkg, newpkg)
        updater = PortfileUpdater(io.StringIO(old_portfile),
                                  pdiff,
                                  MacPortsPythonPackage)
        out = updater._update_portfile_content()
        self.assertEqual(out, expected_portfile)

    def test_update_portfile_content_sunpy(self):
        # Upgrading sunpy from 0.3.1 to 1.1.3 has us:
        # 1) Reset the revision (from 1 to 0)
        # 2) Parse a big block of runtime dependencies
        old_portfile = '''\
version     0.3.1
revision    1

if {${name} ne ${subport}} {
    depends_build-append  port:py${python.version}-numpy

    depends_lib-append    port:py${python.version}-scipy \\
                          port:py${python.version}-matplotlib \\
                          port:py${python.version}-astropy \\
                          port:py${python.version}-pyqt4 \\
                          port:py${python.version}-suds \\
                          port:py${python.version}-pandas \\
                          port:py${python.version}-beautifulsoup4 \\
                          port:py${python.version}-configobj \\
                          port:py${python.version}-setuptools \\
                          port:py${python.version}-py
}
'''
        expected_portfile = '''\
version     1.1.3
revision    0

if {${name} ne ${subport}} {
    depends_build-append  port:py${python.version}-numpy

    depends_lib-append    port:py${python.version}-scipy \\
                          port:py${python.version}-matplotlib \\
                          port:py${python.version}-astropy \\
                          port:py${python.version}-pyqt4 \\
                          port:py${python.version}-suds \\
                          port:py${python.version}-pandas \\
                          port:py${python.version}-beautifulsoup4 \\
                          port:py${python.version}-configobj \\
                          port:py${python.version}-setuptools \\
                          port:py${python.version}-py \\
                          port:py${python.version}-numpy \\
                          port:py${python.version}-parfive
}
# TODO: Move this
depends_test-append port:py${python.version}-hypothesis \\
                    port:py${python.version}-pytest \\
                    port:py${python.version}-pytest-doctestplus \\
                    port:py${python.version}-pytest-astropy \\
                    port:py${python.version}-pytest-cov \\
                    port:py${python.version}-pytest-mock \\
                    port:py${python.version}-tox \\
                    port:py${python.version}-tox-conda
'''
        oldpkg = upt.Package('sunpy', '0.3.1')
        oldpkg.frontend = 'pypi'
        oldpkg.requirements = {
        }
        newpkg = upt.Package('beautifulsoup4', '1.1.3')
        newpkg.frontend = 'pypi'
        newpkg.requirements = {
            'run': [
                upt.PackageRequirement('numpy'),
                upt.PackageRequirement('parfive'),
            ],
            'test': [
                upt.PackageRequirement('hypothesis'),
                upt.PackageRequirement('pytest'),
                upt.PackageRequirement('pytest-doctestplus'),
                upt.PackageRequirement('pytest-astropy'),
                upt.PackageRequirement('pytest-cov'),
                upt.PackageRequirement('pytest-mock'),
                upt.PackageRequirement('tox'),
                upt.PackageRequirement('tox-conda'),
            ],
        }
        pdiff = upt.PackageDiff(oldpkg, newpkg)
        updater = PortfileUpdater(io.StringIO(old_portfile),
                                  pdiff,
                                  MacPortsPythonPackage)
        out = updater._update_portfile_content()
        self.assertEqual(out, expected_portfile)

    def test_update_portfile_content_gwosc(self):
        # What is interesting about updating gwosc from 0.3.3 to 0.5.3 is:
        # 1) depends_lib-append must be removed completely
        # 2) depends_test-append must be added
        old_portfile = '''\
version 0.3.3

if {${name} ne ${subport}} {
    depends_build-append port:py${python.version}-setuptools
    depends_lib-append   port:py${python.version}-six
    livecheck.type      none
} else {
}
'''
        expected_portfile = '''\
version 0.5.3

if {${name} ne ${subport}} {
    depends_build-append port:py${python.version}-setuptools
    livecheck.type      none
} else {
}
# TODO: Move this
depends_test-append port:py${python.version}-pytest \\
                    port:py${python.version}-pytest-cov \\
                    port:py${python.version}-pytest-socket
'''
        oldpkg = upt.Package('gwosc', '0.3.3')
        oldpkg.frontend = 'pypi'
        oldpkg.requirements = {
            'run': [
                upt.PackageRequirement('six'),
            ],
        }
        newpkg = upt.Package('gwosc', '0.5.3')
        newpkg.frontend = 'pypi'
        newpkg.requirements = {
            'run': [],
            'test': [
                upt.PackageRequirement('pytest'),
                upt.PackageRequirement('pytest-cov'),
                upt.PackageRequirement('pytest-socket'),
            ],
        }
        pdiff = upt.PackageDiff(oldpkg, newpkg)
        updater = PortfileUpdater(io.StringIO(old_portfile),
                                  pdiff,
                                  MacPortsPythonPackage)
        out = updater._update_portfile_content()
        self.assertEqual(out, expected_portfile)

    def test_update(self):
        old_portfile = 'line1\n'
        new_portfile = 'line2\nline3\n'
        updater = PortfileUpdater(io.StringIO(old_portfile), None, mock.Mock())
        updater._update_portfile_content = lambda: new_portfile
        updater.update()
        updater.portfile_fp.seek(0)
        self.assertEqual(updater.portfile_fp.read(), new_portfile)

    def test_update_shorter_portfile(self):
        old_portfile = 'line1\nline2\n'
        new_portfile = 'line3\n'
        updater = PortfileUpdater(io.StringIO(old_portfile), None, mock.Mock())
        updater._update_portfile_content = lambda: new_portfile
        updater.update()
        updater.portfile_fp.seek(0)
        self.assertEqual(updater.portfile_fp.read(), new_portfile)
