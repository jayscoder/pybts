import pybts
from pybts.display import render_node

if __name__ == '__main__':
    builder = pybts.Builder(folders=['demos'])
    node = builder.build_from_file('demo_ref_file.xml')
    render_node(node, filepath='demos/demo_ref_file.gif')
    tree = pybts.Tree(root=node)
    tree.setup(builder=builder)
    render_node(tree.root, filepath='demos/demo_ref_file_setup.png')
