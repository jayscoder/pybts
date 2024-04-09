from py_trees import behaviour
from py_trees.display import dot_tree, render_dot_tree
from py_trees import common
import os


def render_node(node: behaviour.Behaviour, filepath: str = '',
                visibility_level: common.VisibilityLevel = common.VisibilityLevel.DETAIL):
    """
    将节点画出来，根据filepath的后缀来区分画的格式
    支持：
    - dot
    - png
    - svg
    - gif
    - jpg
    如果没有提供上述后缀，则默认采用png格式
    """

    graph = dot_tree(
            node,
            visibility_level,
            False,
            with_blackboard_variables=False,
            with_qualified_names=False,
    )
    _, ext = os.path.splitext(filepath)
    ext = ext.lower()
    if ext == '.dot':
        graph.write(filepath)
    elif ext == '.png':
        graph.write_png(filepath)
    elif ext == '.svg':
        graph.write_svg(filepath)
    elif ext == '.gif':
        graph.write_gif(filepath)
    elif ext in ['.jpg', 'jpeg']:
        graph.write_jpg(filepath)
    else:
        graph.write_png(filepath)
