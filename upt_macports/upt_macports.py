import upt
import logging
import jinja2
import pkg_resources
import json
import requests
import os
import subprocess
import sys
import re


class MacPortsPackage(object):
    def __init__(self):
        self.logger = logging.getLogger('upt')

    def create_package(self, upt_pkg, output):
        self.upt_pkg = upt_pkg
        self.logger.info(f'Creating MacPorts package for {self.upt_pkg.name}')
        if output is None:
            print(self._render_makefile_template())
        else:
            self._create_output_directories(upt_pkg, output)
            self._create_portfile(self._render_makefile_template(), 'Portfile')

    def update_package(self, diff, old_pkg, new_pkg, path):
        # Experimental update
        self.upt_pkg = old_pkg
        # old = self._render_makefile_template()
        self.upt_pkg = new_pkg
        new = self._render_makefile_template()
        package_path = os.path.join(path,  self.portfile_path(), 'Portfile')
        with open(package_path, 'r', encoding='utf-8') as f:
            existing = f.read()

        # replace checksums, version and add/replace revision
        existing = existing.replace(
            old_pkg.archives[0].rmd160, new_pkg.archives[0].rmd160)
        existing = existing.replace(
            old_pkg.archives[0].sha256, new_pkg.archives[0].sha256)
        existing = existing.replace(
            str(old_pkg.archives[0].size), str(new_pkg.archives[0].size))

        existing = existing.replace(old_pkg.version, new_pkg.version)
        if 'revision ' in existing:
            existing = re.sub(r'revision\s+\d+',
                              'revision            0', existing)
        else:
            try:
                pattern = new_pkg.version.replace('.', '\.') + '.+'
                vline = re.findall(pattern, existing)[0]
                existing = existing.replace(
                    vline, vline + '\nrevision            0')
            except IndexError:
                self.logger.info('Failed to set revision')

        # End of Experimental

        # add comments for anything that changed
        comments = ''
        # print changes in dependencies
        new_req = diff.new_requirements()
        if new_req:
            comments += '## New Dependencies: \n'
            self.logger.info('New Dependencies for this version are: ')
            for req in new_req:
                print(req)
                comments += f'# {req}\n'
        else:
            self.logger.info('No New Dependencies for this version')
        old_req = diff.deleted_requirements()
        if old_req:
            comments += '## Deleted Dependencies: \n'
            self.logger.info('Deleted Dependencies for this version are: ')
            for req in old_req:
                print(req)
                comments += f'# {req}\n'
        else:
            self.logger.info('No deleted Dependencies for this version')

        if old_pkg.homepage != new_pkg.homepage:
            comments += f'## New homepage is {new_pkg.homepage}'
        if old_pkg.summary != new_pkg.summary:
            comments += '## Updated description is:\n'
            comments += new_pkg.summary.replace('\n', '\n#')

        existing += comments
        # End of comments

        # Rename old file to Portfile.old
        self.logger.info('Renaming old Portfile to Portfile.old')
        os.rename(package_path, package_path + '.old')
        self.output_dir = os.path.join(path,  self.portfile_path())
        # Save upt file as Portfile.upt
        self._create_portfile(new, 'Portfile.upt')
        # Save new file as Portfile
        self.logger.info('Applying patch and hoping it works')
        self._create_portfile(existing, 'Portfile')

    def portfile_path(self):
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
        folder_name = self._normalized_macports_folder(self.upt_pkg.name)

        return os.path.join(port_category, folder_name)

    def _create_output_directories(self, upt_pkg, output_dir):
        """Creates the directory layout required"""
        self.logger.info(f'Creating the directory structure in {output_dir}')
        portfile_folder = self.portfile_path()
        self.output_dir = os.path.join(output_dir, portfile_folder)
        try:
            os.makedirs(self.output_dir, exist_ok=True)
            self.logger.info(f'Created {self.output_dir}')
        except PermissionError:
            sys.exit(f'Cannot create {self.output_dir}: permission denied.')

    def _create_portfile(self, portfile, name):
        self.logger.info('Creating the Portfile')
        try:
            with open(os.path.join(self.output_dir, name), 'x',
                      encoding='utf-8') as f:
                f.write(portfile)
        except FileExistsError:
            sys.exit(f'Cannot create {self.output_dir}/{name}: already exists.')  # noqa

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
                self.logger.info('Please report the error at https://github.com/macports/upt-macports')  # noqa
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
            self.logger.error('Could not determine the type of the source archive')  # noqa
            return 'unknown'


class MacPortsPythonPackage(MacPortsPackage):
    template = 'python.Portfile'
    archive_format = upt.ArchiveType.SOURCE_TARGZ
    category = 'python'

    def _pkgname(self):
        macports_name = self._normalized_macports_name(self.upt_pkg.name)
        return f'{macports_name}'

    @staticmethod
    def _normalized_macports_name(name):
        name = name.lower()
        return f'py-{name}'

    def _python_root_name(self):
        pypi_name = self.upt_pkg.get_archive().filename.split('-'+self.upt_pkg.version)[0]  # noqa
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
    category = 'perl'

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

    def jinja2_reqformat(self, req):
        return f'p${{perl5.major}}-{self._normalized_macports_name(req.name).lower()}'  # noqa

    def _cpandir(self):
        pkg = self.upt_pkg
        # If no archives detected then we cannot locate dist file
        if not pkg.archives:
            self.logger.warning('No dist file was found')
            return ' # could not locate dist file'

        # We start by checking at usual location
        archive_name = pkg.archives[0].url.split('/')[-1]
        part_name = pkg.name.replace('::', '-').split('-')[0]
        check_url = f'https://cpan.metacpan.org/modules/by-module/{part_name}/{archive_name}'  # noqa
        r = requests.head(check_url)
        if r.status_code == 200:
            self.logger.info('Dist file found at usual location')
            return ''
        else:
            # Sometimes if it is not available,
            # then we fallback to alternate location
            # to be verified by the maintainer
            fallback_dist = '/'.join(pkg.archives[0].url.split('id/')[1].split('/')[:-1])  # noqa
            self.logger.info('Dist file was not found at usual location')
            self.logger.info('Using fallback location for dist file')
            return f' ../../authors/id/{fallback_dist}/'


class MacPortsRubyPackage(MacPortsPackage):
    template = 'ruby.Portfile'
    archive_format = upt.ArchiveType.RUBYGEM
    category = 'ruby'

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

    def update_package(self, diff, old_pkg, new_pkg, path):
        try:
            self.frontend = new_pkg.frontend
            pkg_cls = self.pkg_classes[new_pkg.frontend]
        except KeyError:
            raise upt.UnhandledFrontendError(self.name, new_pkg.frontend)
        packager = pkg_cls()
        packager.update_package(diff, old_pkg, new_pkg, path)

    def package_versions(self, name, frontend):
        try:
            port_name = self.pkg_classes[frontend](
            )._normalized_macports_folder(name)
        except KeyError:
            raise upt.UnhandledFrontendError(self.name, frontend)
        print(port_name)
        self.logger.info(f'Checking MacPorts tree for port {port_name}')
        cmd = f'port info --version {port_name}'
        port = subprocess.getoutput(cmd)
        if port.startswith('Error'):
            self.logger.info(f'{port_name} not found in MacPorts tree')
            return []
        elif port.startswith('version'):
            curr_ver = port.split()[1]
            if frontend == 'cpan':
                curr_ver = curr_ver[:-3]
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
