import pydot
from py_trees import behaviour
from pybts.nodes import Node
from pybts.utility import *


def render_node(node: behaviour.Behaviour, filepath: str = '', fontsize: int = 24):
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
    graph: pydot.Dot = dot_graph(node, fontsize=fontsize)
    _, ext = os.path.splitext(filepath)
    ext = ext.lower()
    graph_format = 'png'
    if ext == '.dot':
        graph_format = 'raw'
    elif ext == '.png':
        graph_format = 'png'
    elif ext == '.svg':
        graph_format = 'svg'
    elif ext == '.gif':
        graph_format = 'gif'
    elif ext in ['.jpg', 'jpeg']:
        graph_format = 'jpg'
    graph.write(filepath, format=graph_format)


def add_node_to_graph(graph: pydot.Graph, node: behaviour.Behaviour, fontsize: int = 16) -> pydot.Node:
    node_label = node.name
    if isinstance(node, Node):
        node_label = node.label
    node_type = bt_to_node_type(node)
    node_color = STATUS_TO_PYDOT_SYMBOL_COLORS[node.status.name]
    if 'color' in node.attrs:
        node_color = node.attrs['color']

    node_font_colour = 'black'
    if 'fontcolor' in node.attrs:
        node_font_colour = node.attrs['fontcolor']

    node_shape = BT_NODE_TYPE_TO_PYDOT_SHAPE[node_type]
    if 'shape' in node.attrs:
        node_shape = node.attrs['shape']

    if 'fontsize' in node.attrs:
        fontsize = node.attrs['fontsize']

    pynode = pydot.Node(
            name=node.id.hex,
            label=node_label,
            shape=node_shape,
            style="filled",
            fillcolor=node_color,
            fontsize=fontsize,
            fontcolor=node_font_colour,
    )
    graph.add_node(pynode)

    if isinstance(node, Node) and 'collapsed' in node.attrs and node.attrs['collapsed']:
        return pynode
    for child in node.children:
        add_node_to_graph(graph=graph, node=child, fontsize=fontsize)
        edge = pydot.Edge(node.id.hex, child.id.hex)
        graph.add_edge(edge)
    return pynode


def dot_graph(
        root: behaviour.Behaviour,
        fontsize=16
) -> pydot.Dot:
    """
    Paint your tree on a pydot graph.
    Args:
        root (:class:`~py_trees.behaviour.Behaviour`): the root of a tree, or subtree
        fontsize: 字体
    Returns:
        pydot.Dot: graph

    Examples:
        .. code-block:: python

            # convert the pydot graph to a string object
            print("{}".format(pybts.display.dot_graph(root).to_string()))
    """

    graph = pydot.Dot(graph_type="digraph", ordering="out")

    graph.set_name(
            "pastafarianism"
    )  # consider making this unique to the tree sometime, e.g. based on the root name
    # fonts: helvetica, times-bold, arial (times-roman is the default, but this helps some viewers, like kgraphviewer)
    graph.set_graph_defaults(
            fontname="times-roman"
    )  # splines='curved' is buggy on 16.04, but would be nice to have
    graph.set_node_defaults(fontname="times-roman")
    graph.set_edge_defaults(fontname="times-roman")
    add_node_to_graph(graph=graph, node=root, fontsize=fontsize)
    return graph
