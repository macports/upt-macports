import upt


class MacportsBackend(upt.Backend):
    name = 'macports'

    def create_package(self, upt_pkg, output=None):
        pass
