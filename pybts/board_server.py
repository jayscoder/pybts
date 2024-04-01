from typing import Union, List, Optional
import json
from flask import (
    Flask, send_from_directory, jsonify, request,
    Response
)
from pybts import utility
import os
import argparse
import yaml
import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, 'templates')
STATIC_DIR = os.path.join(TEMPLATES_DIR, 'static')


# TODO: 正在运行的项目要有UI展示
# TODO: 项目名称过长的话要有相应的处理（加tooltip）

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
            "toolbox": {
                "show"    : True,
                "itemSize": 30,
                "itemGap" : 16,
                "feature" : {
                    "myTool1"    : {  # 播放/暂停
                        "show" : True,
                        "title": "暂停",
                        "icon" : "",
                    },
                    "myTool2"    : {
                        "show" : True,
                        "title": "下载XML",
                        "icon" : "",
                    },
                    "saveAsImage": {
                        "show": True
                    },
                }
            },
            "series" : [
                {
                    "type"                   : "tree",
                    # 'type'                   : 'graph',
                    'layout'                 : 'orthogonal',
                    "orient"                 : 'vertical',
                    "id"                     : 0,
                    "name"                   : '',
                    "data"                   : [],
                    "top"                    : "10%",
                    "left"                   : "8%",
                    "bottom"                 : "22%",
                    "right"                  : "10%",
                    "edgeShape"              : "polyline",
                    "edgeForkPosition"       : "63%",
                    "initialTreeDepth"       : -1,
                    # "layout"                 : 'radial',
                    "lineStyle"              : {
                        "width": 2,
                    },
                    "roam"                   : True,
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
        if not os.path.exists(self.log_dir):
            return []

        for dirpath, dirnames, filenames in os.walk(self.log_dir):
            if 'pybts.json' in filenames:
                relative_path = os.path.relpath(dirpath, self.log_dir)
                pybts_data = self._get_pybts_data(project=relative_path)
                if pybts_data is None:
                    continue
                server_data = self._get_server_data(project=relative_path) or { }

                projects.append({
                    'name'  : relative_path,
                    'unread': pybts_data.get('id') - server_data.get('last_read_id', 0),
                    'total' : pybts_data['id']
                })

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

    def get_xml_data(self):
        project = request.args.get('project') or ''
        track_id = request.args.get('id') or ''
        if track_id == '':
            pybts_data = self._get_pybts_data(project=project)
            track_id = pybts_data['id']
        track_id = int(track_id)
        log_data = self._get_history_data(project=project, track_id=track_id)
        if log_data is None:
            return jsonify({ 'error': f'project {project}: {track_id} not exist' }), 500

        xml_data = utility.bt_to_xml(log_data['tree'])
        return Response(xml_data, mimetype='application/xml')

    def _get_pybts_data(self, project: str) -> Optional[dict]:
        """当前track的信息"""
        filepath = os.path.join(self.log_dir, project, 'pybts.json')
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                return json.load(f)
        return None

    def _get_history_data(self, project: str, track_id: int) -> Optional[dict]:
        filepath = os.path.join(self.log_dir, project, 'pybts-history', f'{track_id}.json')
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                return json.load(f)
        return None

    def _get_server_data(self, project) -> dict:
        json_data = { }
        filepath = os.path.join(self.log_dir, project, 'pybts-server.json')
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                json_data = json.load(f)
        return json_data

    def _write_server_data(self, project, json_data):
        filepath = os.path.join(self.log_dir, project, 'pybts-server.json')
        old_data = self._get_server_data(project)
        new_data = {
            **old_data,
            **json_data
        }
        with open(filepath, 'w') as f:
            utility.json_dump(new_data, f, ensure_ascii=False)

    def get_echarts_data(self):
        project = request.args.get('project') or ''
        track_id = request.args.get('id')
        pybts_data = self._get_pybts_data(project=project)
        if pybts_data is None:
            print(f'project {project}: {track_id} not exist')
            return jsonify({ 'error': f'project {project}: {track_id} not exist' }), 500
        if track_id == '':
            track_id = pybts_data['id']
        track_id = int(track_id)

        log_data = self._get_history_data(project=project, track_id=track_id)
        if log_data is None:
            print(f'project {project}: {track_id} not exist')
            return jsonify({ 'error': f'project {project}: {track_id} not exist' }), 500

        tree_data = utility.bt_to_echarts_json(log_data['tree'])

        del log_data['tree']
        if log_data['info'] is None:
            del log_data['info']

        # 时间戳格式化
        log_data['time'] = datetime.datetime.fromtimestamp(log_data['time'] / 1000).strftime('%Y-%m-%d %H:%M:%S')
        subtitle = yaml.dump(log_data, allow_unicode=True)

        self._write_server_data(project=project, json_data={
            'last_read_id': track_id
        })

        return jsonify({
            'tree'    : tree_data,
            'subtitle': subtitle,
            'title'   : f"{project}  {log_data['round']}-{log_data['step']} / {log_data['id']}",
            'id'      : log_data['id'],
            'page'    : log_data['id'],
            'total'   : pybts_data['id']
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
