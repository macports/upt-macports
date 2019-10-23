import upt
import logging
import jinja2
import pkg_resources
import json
import requests
import os
import subprocess
import sys


class MacPortsPackage(object):
    def __init__(self):
        self.logger = logging.getLogger('upt')

    def create_package(self, upt_pkg, output):
        self.upt_pkg = upt_pkg
        self.logger.info(f'Creating MacPorts package for {self.upt_pkg.name}')
        portfile_content = self._render_makefile_template()
        if output is None:
            print(portfile_content)
        else:
            self._create_output_directories(upt_pkg, output)
            self._create_portfile(portfile_content)

    def _create_output_directories(self, upt_pkg, output_dir):
        """Creates the directory layout required"""
        self.logger.info(f'Creating the directory structure in {output_dir}')
        folder_name = self._normalized_macports_folder(upt_pkg.name)
        self.output_dir = os.path.join(
            output_dir, self.category, folder_name)
        try:
            os.makedirs(self.output_dir, exist_ok=True)
            self.logger.info(f'Created {self.output_dir}')
        except PermissionError:
            sys.exit(f'Cannot create {self.output_dir}: permission denied.')

    def _create_portfile(self, portfile_content):
        self.logger.info('Creating the Portfile')
        try:
            with open(os.path.join(self.output_dir, 'Portfile'), 'x',
                      encoding='utf-8') as f:
                f.write(portfile_content)
        except FileExistsError:
            sys.exit(f'Cannot create {self.output_dir}/Portfile: already exists.') # noqa

    def _render_makefile_template(self):
        env = jinja2.Environment(
            loader=jinja2.PackageLoader('upt_macports', 'templates'),
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True,
        )
        env.filters['reqformat'] = self.jinja2_reqformat
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

    def _pkgname(self):
        return self._normalized_macports_name(self.upt_pkg.name)


class MacPortsPythonPackage(MacPortsPackage):
    template = 'python.Portfile'
    archive_format = upt.ArchiveType.SOURCE_TARGZ
    category = 'python'

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

    def jinja2_reqformat(self, req):
        return f'py${{python.version}}-{req.name.lower()}'


class MacPortsNpmPackage(MacPortsPackage):
    template = 'npm.Portfile'

    @staticmethod
    def _normalized_macports_name(name):
        name = name.lower()
        return f'{name}'


class MacPortsPerlPackage(MacPortsPackage):
    template = 'perl.Portfile'
    archive_format = upt.ArchiveType.SOURCE_TARGZ
    category = 'perl'

    @staticmethod
    def _normalized_macports_name(name):
        return name.replace('::', '-')

    @staticmethod
    def _normalized_macports_folder(name):
        name = name.lower().replace('::', '-')
        return f'p5-{name}'

    def jinja2_reqformat(self, req):
        return f'p${{perl5.major}}-{self._normalized_macports_name(req.name).lower()}' # noqa

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
    category = 'ruby'

    @staticmethod
    def _normalized_macports_name(name):
        return name

    @staticmethod
    def _normalized_macports_folder(name):
        name = name.lower()
        return f'rb-{name}'

    def jinja2_reqformat(self, req):
        return f'rb${{ruby.suffix}}-{req.name.lower()}'


class MacPortsBackend(upt.Backend):
    def __init__(self):
        self.logger = logging.getLogger('upt')

    name = 'macports'
    pkg_classes = {
        'pypi': MacPortsPythonPackage,
        'cpan': MacPortsPerlPackage,
        'rubygems': MacPortsRubyPackage,
        'npm': MacPortsNpmPackage
    }

    def create_package(self, upt_pkg, output=None):
        try:
            self.frontend = upt_pkg.frontend
            pkg_cls = self.pkg_classes[upt_pkg.frontend]
        except KeyError:
            raise upt.UnhandledFrontendError(self.name, upt_pkg.frontend)
        packager = pkg_cls()
        packager.create_package(upt_pkg, output)

    def package_versions(self, name):
        try:
            port_name = self.pkg_classes[
                self.frontend]._normalized_macports_folder(name)
        except KeyError:
            raise upt.UnhandledFrontendError(self.name, self.upt_pkg.frontend)

        self.logger.info(f'Checking MacPorts tree for port {port_name}')
        cmd = f'port info --version {port_name}'
        port = subprocess.getoutput(cmd)
        if port.startswith('Error'):
            self.logger.info(f'{port_name} not found in MacPorts tree')
            return []
        elif port.startswith('version'):
            curr_ver = port.split()[1]
            self.logger.info(
                f'Current MacPorts Version for {port_name} is {curr_ver}')
            return [curr_ver]
        elif port.startswith('Warning'):
            self.logger.warning(
                'port definitions are more than two weeks old, '
                'consider updating them by running \'port selfupdate\'.')
            curr_ver = port.split('version: ')[1]
            self.logger.info(
                f'Current MacPorts Version for {port_name} is {curr_ver}')
            return [curr_ver]
        else:
            sys.exit(f'The command "{cmd}" failed. '
                     'Please make sure you have MacPorts installed '
                     'and/or your PATH is set-up correctly.')
