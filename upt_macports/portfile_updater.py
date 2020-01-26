# Copyright 2021      Cyril Roelandt
#
# Licensed under the 3-clause BSD license. See the LICENSE file.
import logging
import re

import upt


class PortfileUpdater:
    def __init__(self, portfile_fp, pdiff, pkg_class):
        self.portfile_fp = portfile_fp
        self.pdiff = pdiff
        self.logger = logging.getLogger('upt')
        self.macports_pkg = pkg_class()

    def update(self):
        new_portfile_content = self._update_portfile_content()
        self.portfile_fp.seek(0)
        self.portfile_fp.write(new_portfile_content)
        self.portfile_fp.truncate()

    def _update_portfile_content(self):
        content = self.portfile_fp.read()
        content = self._update_version(content,
                                       self.pdiff.old_version,
                                       self.pdiff.new_version)
        content = self._update_revision(content)
        try:
            archive_format = self.macports_pkg.archive_format
            new_archive = self.pdiff.new.get_archive(archive_format)
            content = self._update_checksums(content, new_archive)
        except upt.ArchiveUnavailable:
            self.logger.info('We could not get archives for this package. '
                             'The checksums/size will be wrong.')
        content = self._update_dependencies(content, self.pdiff,
                                            self.macports_pkg.jinja2_reqformat)
        return content

    @staticmethod
    def _update_checksums(content, new_archive):
        '''Update the checksums block.

        Return CONTENT after replacing the checksums (and size) with updated
        checksums (and size) for NEW_ARCHIVE.

        In the process, completely removes md5 checksum, which are no longer
        required in MacPorts.
        '''
        m = re.search(r"[^\n]*checksums.*?[^\\]\n", content, re.DOTALL)
        if not m:  # This Portfile had no checksums, let's not change anything
            return content

        old_archive_block = m.group(0)
        m = re.match(r'(\s*)checksums(\s+)[^\s]+',
                     old_archive_block.split('\n')[0])
        space_before = m.group(1)
        space_after = m.group(2)
        indent = ' ' * len(space_before + 'checksums' + space_after)
        new_archive_block = f'{space_before}checksums{space_after}'
        new_archive_block += f'rmd160  {new_archive.rmd160} \\\n'
        new_archive_block += f'{indent}sha256  {new_archive.sha256} \\\n'
        new_archive_block += f'{indent}size    {new_archive.size}\n'
        return content.replace(old_archive_block, new_archive_block)

    @staticmethod
    def _update_version(content, old_version, new_version):
        '''Update the version of the package being updated.

        Return CONTENT after replacing the OLD_VERSION with the NEW_VERSION.
        This works for the "version" keyword, and a variety of "*.setup"
        keywords.
        '''
        keywords = '|'.join([
            'version', 'github.setup', 'bitbucket.setup',
            'ruby.setup', 'perl5.setup',
        ])
        return re.sub(fr'({keywords})(.*){old_version}',
                      fr'\g<1>\g<2>{new_version}',
                      content, count=1)

    @staticmethod
    def _update_revision(content):
        '''Update the first revision entry in the Portfile.'''
        return re.sub(r'revision(\s+)\d+', r'revision\g<1>0', content,
                      count=1)

    def _update_dependencies(self, content, pdiff, reqformat_fn):
        for phase in ['build', 'lib', 'test']:
            content = self._update_dependency_phase(content, pdiff,
                                                    reqformat_fn, phase)
        return content

    @staticmethod
    def _get_current_dependencies(content, phase):
        '''Return a list of the current dependencies for a given phase.

        Extract all dependencies for PHASE from CONTENT. PHASE must be one of
        'build', 'lib', 'test'. The dependencies are returned just like they
        are written in the Portfile, for instance:

            ['port:py${python.version}-six', 'port:py${python.version}-xlrd']
        '''
        mmm = re.search(fr"[^\n]*depends_{phase}-append.*?[^\\]\n",
                        content, re.DOTALL)
        deps = []
        if mmm:
            old_depends_block = mmm.group(0)
            for line in old_depends_block.split('\n'):
                m = re.match(fr'(\s*)depends_{phase}-append(\s+)(.*)', line)
                if m:
                    line = m.group(3)
                if line.endswith('\\'):
                    line = line[:-1]
                line = line.strip()
                deps.extend(line.split())
        else:
            old_depends_block = ''

        return old_depends_block, deps

    @staticmethod
    def _remove_deleted_dependencies(current_deps, deleted_dependencies):
        '''Remove DELETED_DEPENDENCIES from CURRENT_DEPS.

        CURRENT_DEPS and DELETED_DEPENDENCIES must be lists of dependencies as
        specified in a Portfile.

        Example:
            current_deps = ['port:py${python.version}-six',
                            'port:py${python.version}-xlrd']
            deleted_dependencies = ['port:py${python.version}-xlrd']
            This method will return ['port:py${python.version}-six']
        '''
        # We could have used operations on sets here, but since sets are
        # unordered, the dependencies would have been "shuffled", which would
        # have caused the diff between the old and the new Portfiles to be
        # bigger and harder to read that they needed to be.
        for deleted_dependency in deleted_dependencies:
            try:
                current_deps.remove(deleted_dependency)
            except ValueError:
                # This particular requirement is no longer marked as needed
                # upstream. Maybe it was never included in the Makefile, which
                # means that trying to remove it may raise this exception.
                pass
        return current_deps

    @staticmethod
    def _add_new_dependencies(current_deps, new_dependencies):
        '''Add NEW_DEPENDENCIES to CURRENT_DEPS.

        CURRENT_DEPS and NEW_DEPENDENCIES must be lists of dependencies as
        specified in a Portfile.

        Example:
            current_deps = ['port:py${python.version}-six']
            new_dependencies = ['port:py${python.version}-xlrd']
            This method will return  = ['port:py${python.version}-six',
                                        'port:py${python.version}-xlrd']
        '''
        # We could have used operations on sets here, but since sets are
        # unordered, the dependencies would have been "shuffled", which would
        # have caused the diff between the old and the new Portfiles to be
        # bigger and harder to read that they needed to be.
        #
        # Some of the new requirements may already be in the Portfile. This
        # happens when upstream failed to properly specify metadata in the old
        # version and fixed everything in the new one:
        #
        # Old upstream metadata: "required: []" (even though 'foo' is needed)
        # New upstream metadata: "required: ['foo']"
        #
        # In this case, upt will consider that 'foo' is a new requirement.
        # Since it was already required in the old version (even though that
        # was not specified in the metadata), the dependency on 'foo' will
        # already be specified in the Portfile. We need to make sure that we do
        # not duplicate this dependency, hence the if condition in the loop.
        for new_dependency in new_dependencies:
            if new_dependency not in current_deps:
                current_deps.append(new_dependency)
        return current_deps

    def _update_dependency_phase(self, content, pdiff, reqformat_fn, phase):
        phases = {
            'build': 'build',
            'lib': 'run',
            'test': 'test',
        }
        # Let's extract the dependencies currently specified in the Portfile
        # for this phase.
        old_depends_block, deps = self._get_current_dependencies(content,
                                                                 phase)

        # Start by removing the deleted dependencies.
        deleted_dependencies = [
            f'port:{reqformat_fn(deleted_dependency)}'
            for deleted_dependency in pdiff.deleted_requirements(phases[phase])
        ]
        deps = self._remove_deleted_dependencies(deps, deleted_dependencies)

        # Next, add the new dependencies.
        new_dependencies = [
            f'port:{reqformat_fn(new_dependency)}'
            for new_dependency in pdiff.new_requirements(phases[phase])
        ]
        deps = self._add_new_dependencies(deps, new_dependencies)

        # Finally, format the new depends block properly.
        new_depends_block = self._format_like(deps, old_depends_block, phase)
        if old_depends_block:
            content = content.replace(old_depends_block, new_depends_block)
        else:
            # This phase had no dependencies, let's add it at the bottom of the
            # Portfile and let the maintainer move it wherever they want.
            if new_depends_block:
                content += '# TODO: Move this\n'
                content += new_depends_block
        return content

    @staticmethod
    def _format_like(deps, old_depends_block, phase):
        '''Format a block of dependencies.

        Return a string representing a dependency block for PHASE, containing
        dependencies specified in DEPS, so that it uses the same
        indentation/spacing as OLD_DEPENDS_BLOCK.
        '''
        if not deps:  # No dependencies -> No block in the Portfile
            return ''

        # Read
        old_depends_block_lines = old_depends_block.split('\n')
        block_name = f'depends_{phase}-append'
        m = re.match(fr'(\s*)depends_{phase}-append(\s+)(.*)',
                     old_depends_block_lines[0])
        if m:
            first_line_indent = m.group(1)
            space = m.group(2)
            if m.group(3) == '\\':
                # When the first line does not contain a dependency, like this:
                #   depends_lib-append \
                # we use this "hack": this allows us to not handle a "special"
                # case" when crafting the new depends block.
                deps.insert(0, '')
        else:
            # This phase was not included in the original Portfile, we will
            # build it "from scratch".
            first_line_indent = ''
            space = ' '

        next_lines_indent = ''
        if len(old_depends_block_lines) > 1:
            m = re.match(r'(\s+)', old_depends_block_lines[1])
            if m:
                next_lines_indent = m.group(1)

        if next_lines_indent == '':
            next_lines_indent = first_line_indent
            next_lines_indent += ' ' * len(block_name)
            next_lines_indent += space

        # Craft the new block
        new_depends = f'{first_line_indent}{block_name}'
        if not deps[0]:
            new_depends += ' ' * (len(space) - 1)
        else:
            new_depends += space
        new_depends += ' \\\n'.join([
            dep if i == 0
            else f'{next_lines_indent}{dep}'
            for i, dep in enumerate(deps)
        ])
        new_depends += '\n'
        return new_depends
