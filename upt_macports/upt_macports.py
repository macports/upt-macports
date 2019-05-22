import upt
import logging
import jinja2
import pkg_resources
import json


class MacPortsPackage(object):
    def __init__(self):
        self.logger = logging.getLogger('upt')

    def create_package(self, upt_pkg, output):
        self.upt_pkg = upt_pkg
        self.logger.info(f'Hello, creating the package')
        print(self._render_makefile_template())
        print(self._depends)

    def _render_makefile_template(self):
        env = jinja2.Environment(
            loader=jinja2.PackageLoader('upt_macports', 'templates'),
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True,
        )
        # env.filters['reqformat'] = self.jinja2_reqformat
        template = env.get_template(self.template)
        return template.render(pkg=self)

    @property
    def licenses(self):
        relpath = 'spdx2macports.json'
        filepath = pkg_resources.resource_filename(__name__, relpath)
        with open(filepath) as f:
            spdx2macports = json.loads(f.read())

        return ' '.join([spdx2macports.get(license.spdx_identifier, 'unknown')
                        for license in self.upt_pkg.licenses])

    def _depends(self, phase):
        return self.upt_pkg.requirements.get(phase, [])

    @property
    def build_depends(self):
        return self._depends('build')

    @property
    def run_depends(self):
        return self._depends('run')

    @property
    def test_depends(self):
        return self._depends('test')

    @property
    def archive_type(self):
        archive_keyword = {
            'gz': 'gz',
            '7z': '7z',
            'bz2': 'bzip2',
            'lzma': 'lzma',
            'tar': 'tar',
            'zip': 'zip',
            'xz': 'xz'
        }
        try:
            archive_name = self.upt_pkg.get_archive().filename
            archive_type = archive_name.split('.')[-1]
            return archive_keyword.get(archive_type, 'unknown')

        except upt.ArchiveUnavailable:
            self.logger.error('Could not determine the type of the source archive') # noqa
            return 'unknown'


class MacPortsPythonPackage(MacPortsPackage):
    template = 'python.Portfile'

    def _pkgname(self):
        macports_name = self._normalized_macports_name(self.upt_pkg.name)
        return f'{macports_name}'

    @staticmethod
    def _normalized_macports_name(name):
        name = name.lower()
        return f'py-{name}'


class MacPortsNpmPackage(MacPortsPackage):
    template = 'npm.Portfile'

    def _pkgname(self):
        macports_name = self._normalized_macports_name(self.upt_pkg.name)
        return f'{macports_name}'

    @staticmethod
    def _normalized_macports_name(name):
        name = name.lower()
        return f'{name}'


class MacPortsPerlPackage(MacPortsPackage):
    template = 'perl.Portfile'

    def _pkgname(self):
        macports_name = self._normalized_macports_name(self.upt_pkg.name)
        return macports_name

    @staticmethod
    def _normalized_macports_name(name):
        return name


class MacPortsRubyPackage(MacPortsPackage):
    template = 'ruby.Portfile'


class MacPortsBackend(upt.Backend):
    name = 'macports'

    def create_package(self, upt_pkg, output=None):
        pkg_classes = {
            'pypi': MacPortsPythonPackage,
            'cpan': MacPortsPerlPackage,
            'rubygems': MacPortsRubyPackage,
            'npm': MacPortsNpmPackage
        }

        try:
            pkg_cls = pkg_classes[upt_pkg.frontend]
        except KeyError:
            raise upt.UnhandledFrontendError(self.name, upt_pkg.frontend)

        packager = pkg_cls()
        packager.create_package(upt_pkg, output)
