import json
from flask import (
    Flask, send_from_directory, jsonify, request,
    Response
)
from pybts import utility
import os
import argparse
import yaml

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, 'templates')
STATIC_DIR = os.path.join(TEMPLATES_DIR, 'static')


class BoardServer:

    def __init__(self, title: str = 'PYBT', log_dir: str = '', update_interval: int = 0.5, debug: bool = False,
                 host: str = '0.0.0.0', port: int = 10000):
        self.title = title
        self.update_interval = update_interval  # 每隔0.5s刷新一次
        self.log_dir = log_dir
        self.app = Flask(__name__, static_folder=STATIC_DIR, template_folder=TEMPLATES_DIR)
        self.debug = debug
        self.host = host
        self.port = port

        # 注册路由
        self.app.add_url_rule('/static/<path:path>', view_func=self.send_static)
        self.app.add_url_rule('/api/get_config', view_func=self.get_config, methods=['GET'])
        self.app.add_url_rule('/api/get_echarts_data', view_func=self.get_echarts_data, methods=['GET'])
        self.app.add_url_rule('/api/get_xml_data', view_func=self.get_xml_data, methods=['GET'])

        self.app.add_url_rule('/api/get_option', view_func=self.get_option, methods=['GET'])
        self.app.add_url_rule("/", view_func=self.index, defaults={ 'path': '' }, methods=['GET'])
        self.app.add_url_rule("/<path:path>", view_func=self.index, methods=['GET'])

        self.option = {
            "title"  : {
                "text"   : "PYBT",
                "subtext": "",
            },
            "tooltip": {
                "show"     : True,
                "trigger"  : "item",
                "triggerOn": "mousemove|click"
            },
            "series" : [
                {
                    "type"                   : "tree",
                    "id"                     : 0,
                    "name"                   : '',
                    "data"                   : [],
                    "top"                    : "10%",
                    "left"                   : "8%",
                    "bottom"                 : "22%",
                    "right"                  : "10%",
                    "edgeShape"              : "polyline",
                    "edgeForkPosition"       : "63%",
                    "initialTreeDepth"       : 3,
                    "lineStyle"              : {
                        "width": 2,
                    },
                    "label"                  : {
                        "backgroundColor": "#fff",
                        "position"       : "left",
                        "verticalAlign"  : "middle",
                        "align"          : "right",
                        "fontSize"       : 14
                    },
                    "leaves"                 : {
                        "label": {
                            "position"     : "right",
                            "verticalAlign": "middle",
                            "align"        : "left",
                        },
                    },
                    "emphasis"               : {
                        "focus": "descendant",
                    },
                    "expandAndCollapse"      : False,
                    "animationDuration"      : 100,
                    "animationDurationUpdate": 100,
                    "select"                 : {
                        "itemStyle": {
                            "borderColor": "orange",
                        },
                    },
                    "selectedMode"           : "single",
                },
            ],
        }

    def run(self):
        self.app.run(host=self.host, port=self.port, debug=self.debug)

    def index(self, path):
        print('index', path)
        if path not in ['', '/', 'index.html']:
            target_paths = [
                path,
                path + '.html'
            ]
            for target_path in target_paths:
                if os.path.exists(os.path.join(TEMPLATES_DIR, target_path)):
                    return send_from_directory(TEMPLATES_DIR, target_path)
        return send_from_directory(TEMPLATES_DIR, 'index.html')

    def send_static(self, path):
        return send_from_directory(STATIC_DIR, path)

    def send_template(self, path):
        return send_from_directory(TEMPLATES_DIR, path)

    def get_projects(self):
        # 获取log_dir里面的所有的文件夹
        projects = []
        for filename in os.listdir(self.log_dir):
            filepath = os.path.join(self.log_dir, filename)
            if not os.path.isdir(filepath):
                continue
            bt_path = os.path.join(filepath, 'pybt.json')
            if os.path.exists(bt_path):
                projects.append(filename)
        return projects

    def get_config(self):
        projects = self.get_projects()
        return jsonify({
            'title'          : self.title,
            'update_interval': self.update_interval,
            'projects'       : projects,
        })

    def get_option(self):
        return jsonify(self.option)

    def get_history_steps(self, project):
        history_path = os.path.join(self.log_dir, project, 'history')
        if not os.path.exists(history_path):
            return []

        history_steps = []
        for filename in os.listdir(history_path):
            if filename.endswith('.json'):
                history_steps.append(int(filename.removesuffix('.json')))
        history_steps = sorted(history_steps)
        return history_steps

    def get_xml_data(self):
        project = request.args.get('project')
        step = int(request.args.get('step'))
        if step == -1:
            pybt_path = os.path.join(self.log_dir, project, 'pybt.json')
        else:
            pybt_path = os.path.join(self.log_dir, project, 'history', f'{step}.json')

        if not os.path.exists(pybt_path):
            return jsonify({ 'error': f'project {project}-{step} not exist' }), 500

        xml_data = ''
        if os.path.exists(pybt_path):
            with open(pybt_path, 'r') as f:
                json_data = json.load(f)
                xml_data = utility.bt_to_xml(json_data['tree'])

        return Response(xml_data, mimetype='application/xml')

    def get_echarts_data(self):
        project = request.args.get('project')
        step = int(request.args.get('step'))
        if step == -1:
            pybt_path = os.path.join(self.log_dir, project, 'pybt.json')
        else:
            pybt_path = os.path.join(self.log_dir, project, 'history', f'{step}.json')

        if not os.path.exists(pybt_path):
            return jsonify({ 'error': f'project {project}-{step} not exist' }), 500

        step = 0
        tree_data = { }
        if os.path.exists(pybt_path):
            with open(pybt_path, 'r') as f:
                json_data = json.load(f)
                tree_data = utility.bt_to_echarts_json(json_data['tree'])
                step = json_data['step']

        subtitle = ''
        if 'info' in json_data and json_data['info'] is not None:
            subtitle = yaml.dump(json_data['info'], allow_unicode=True)

        return jsonify({
            'tree'    : tree_data,
            'step'    : step,
            'steps'   : self.get_history_steps(project),
            'subtitle': subtitle
        })


def main():
    # 创建 ArgumentParser 对象
    parser = argparse.ArgumentParser(description="A simple program to demonstrate argparse")

    # 添加选项标志
    parser.add_argument("--dir", help="Path to the log directory", required=True)
    # 添加debug参数
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    # 添加host参数
    parser.add_argument("--host", default="localhost", help="Host address")
    # 添加port参数
    parser.add_argument("--port", type=int, default=10000, help="Port number")

    # 解析命令行参数
    args = parser.parse_args()

    server = BoardServer(log_dir=args.dir, debug=args.debug, host=args.host, port=args.port)
    server.run()


if __name__ == '__main__':
    main()
