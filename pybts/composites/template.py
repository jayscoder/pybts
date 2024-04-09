from pybts.composites.parallel import *


class Template(Parallel):
    def __init__(self, scope: str = '', **kwargs):
        super().__init__(**kwargs)
        self.scope = scope

