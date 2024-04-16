import pydot

# 创建一个图形对象
graph = pydot.Dot(graph_type='graph', rankdir='LR', fontsize='12')

# 创建不同形状的节点
node_box = pydot.Node("Box", shape="box")
node_ellipse = pydot.Node("Ellipse", shape="ellipse")
node_circle = pydot.Node("Circle", shape="circle")
node_diamond = pydot.Node("Diamond", shape="diamond")
node_record = pydot.Node("Record", shape="record")
node_triangle = pydot.Node("Triangle", shape="triangle")
node_round_rect = pydot.Node("RoundRect", shape="round_rect")

# 添加节点到图形中
graph.add_node(node_box)
graph.add_node(node_ellipse)
graph.add_node(node_circle)
graph.add_node(node_diamond)
graph.add_node(node_record)
graph.add_node(node_triangle)
graph.add_node(node_round_rect)
# 添加边
edges = [
    pydot.Edge("Box", "Ellipse"),
    pydot.Edge("Ellipse", "Circle"),
    pydot.Edge("Circle", "Diamond"),
    pydot.Edge("Diamond", "Record"),
    pydot.Edge("Record", "Triangle"),
]

for edge in edges:
    graph.add_edge(edge)

# 将图形保存为 PNG 文件
graph.write_png('output.png')

print("PNG 文件已保存")
