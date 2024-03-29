import py_trees


class Tree(py_trees.trees.BehaviourTree):
    def __init__(self, root: py_trees.behaviour.Behaviour, name: str = ''):
        super().__init__(root=root)
        self.name = name or root.name
