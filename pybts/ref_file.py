import typing

from py_trees.common import Status
from pybts.decorators import Decorator


class RefFile(Decorator):
    """
    引用文件节点，在setup后会自动将子节点替换为对应文件里的节点
    必须得在setup里传builder
    注意：要记得检查，不要循环引用了
    """

    def __init__(self, path: str, **kwargs):
        super().__init__(**kwargs)
        self.path = path

    def setup(self, **kwargs: typing.Any) -> None:
        assert len(self.children) == 0, 'RefFile Node can not has children'
        self.path = self.converter.render(self.path)
        super().setup(**kwargs)
        from pybts.builder import Builder
        builder: Builder = kwargs.get('builder')
        assert builder is not None, 'has RefFile Node,builder must be set'

        self.decorated = builder.build_from_file(filepath=self.path)
        self.children = [self.decorated]
        self.decorated.parent = self

        for child in self.decorated.iterate():
            child.setup(**kwargs)

    def update(self) -> Status:
        return self.decorated.status
