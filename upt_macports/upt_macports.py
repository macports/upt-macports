import upt
import logging
import jinja2
import pkg_resources
import json
import requests
import os
import sys


class MacPortsPackage(object):
    def __init__(self):
        self.logger = logging.getLogger('upt')

    def create_package(self, upt_pkg, output):
        self.upt_pkg = upt_pkg
        self.logger.info(f'Hello, creating the package')
        if output is None:
            print(self._render_makefile_template())
        else:
            self._create_output_directories(upt_pkg, output)
            self._create_portfile()

    def _create_output_directories(self, upt_pkg, output_dir):
        """Creates the directory layout required"""
        self.logger.info(f'Creating the directory structure in {output_dir}')
        upt2macports = {
            'cpan': 'perl',
            'pypi': 'python',
            'rubygems': 'ruby',
        }
        try:
            port_category = upt2macports[self.upt_pkg.frontend]
        except KeyError:
            sys.exit(
                f'Unknown port category for frontend {self.upt_pkg.frontend}')
        folder_name = self._normalized_macports_folder(upt_pkg.name)
        self.output_dir = os.path.join(
            output_dir, port_category, folder_name)
        try:
            os.makedirs(self.output_dir, exist_ok=True)
            self.logger.info(f'Created {self.output_dir}')
        except PermissionError:
            sys.exit(f'Cannot create {self.output_dir}: permission denied.')

    def _create_portfile(self):
        self.logger.info('Creating the Portfile')
        try:
            with open(os.path.join(self.output_dir, 'Portfile'), 'x',
                      encoding='utf-8') as f:
                f.write(self._render_makefile_template())
        except FileExistsError:
            sys.exit(f'Cannot create {self.output_dir}/Portfile: already exists.') # noqa

    def _render_makefile_template(self):
        env = jinja2.Environment(
            loader=jinja2.PackageLoader('upt_macports', 'templates'),
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True,
        )
        template = env.get_template(self.template)
        return template.render(pkg=self)

    @property
    def licenses(self):
        relpath = 'spdx2macports.json'
        filepath = pkg_resources.resource_filename(__name__, relpath)
        with open(filepath) as f:
            spdx2macports = json.loads(f.read())

        if not self.upt_pkg.licenses:
            self.logger.info('No license found')
            return 'unknown'
        licenses = []
        for license in self.upt_pkg.licenses:
            try:
                if license.spdx_identifier == 'unknown':
                    port_license = 'unknown'
                    self.logger.warning(f'upt failed to detect license')
                else:
                    port_license = spdx2macports[license.spdx_identifier]
                    self.logger.info(f'Found license {port_license}')
                licenses.append(port_license)
            except KeyError:
                err = f'MacPorts license unknown for {license.spdx_identifier}'
                licenses.append('unknown # ' + err)
                self.logger.error(err)
                self.logger.info('Please report the error at https://github.com/macports/upt-macports') # noqa
        return ' '.join(licenses)

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
            archive_name = self.upt_pkg.get_archive(
                self.archive_format).filename
            archive_type = archive_name.split('.')[-1]
            return archive_keyword.get(archive_type, 'unknown')

        except upt.ArchiveUnavailable:
            self.logger.error('Could not determine the type of the source archive') # noqa
            return 'unknown'


class MacPortsPythonPackage(MacPortsPackage):
    template = 'python.Portfile'
    archive_format = upt.ArchiveType.SOURCE_TARGZ

    def _pkgname(self):
        macports_name = self._normalized_macports_name(self.upt_pkg.name)
        return f'{macports_name}'

    @staticmethod
    def _normalized_macports_name(name):
        name = name.lower()
        return f'py-{name}'

    def _python_root_name(self):
        pypi_name = self.upt_pkg.get_archive().filename.split('-'+self.upt_pkg.version)[0] # noqa
        if pypi_name != self.upt_pkg.name.lower():
            return pypi_name

    @staticmethod
    def _normalized_macports_folder(name):
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
    archive_format = upt.ArchiveType.SOURCE_TARGZ

    def _pkgname(self):
        macports_name = self._normalized_macports_name(self.upt_pkg.name)
        return macports_name

    @staticmethod
    def _normalized_macports_name(name):
        return name.replace('::', '-')

    @staticmethod
    def _normalized_macports_folder(name):
        name = name.lower().replace('::', '-')
        return f'p5-{name}'

    def _cpandir(self):
        pkg = self.upt_pkg
        # If no archives detected then we cannot locate dist file
        if not pkg.archives:
            self.logger.warning('No dist file was found')
            return ' # could not locate dist file'

        # We start by checking at usual location
        archive_name = pkg.archives[0].url.split('/')[-1]
        part_name = pkg.name.replace('::', '-').split('-')[0]
        check_url = f'https://cpan.metacpan.org/modules/by-module/{part_name}/{archive_name}' # noqa
        r = requests.head(check_url)
        if r.status_code == 200:
            self.logger.info('Dist file found at usual location')
            return ''
        else:
            # Sometimes if it is not available,
            # then we fallback to alternate location
            # to be verified by the maintainer
            fallback_dist = '/'.join(pkg.archives[0].url.split('id/')[1].split('/')[:-1]) # noqa
            self.logger.info('Dist file was not found at usual location')
            self.logger.info('Using fallback location for dist file')
            return f' ../../authors/id/{fallback_dist}/'


class MacPortsRubyPackage(MacPortsPackage):
    template = 'ruby.Portfile'
    archive_format = upt.ArchiveType.RUBYGEM

    def _pkgname(self):
        macports_name = self._normalized_macports_name(self.upt_pkg.name)
        return macports_name

    @staticmethod
    def _normalized_macports_name(name):
        return name

    @staticmethod
    def _normalized_macports_folder(name):
        name = name.lower()
        return f'rb-{name}'


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
