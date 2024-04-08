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

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATES_DIR = os.path.join(BASE_DIR, 'templates')
STATIC_DIR = os.path.join(TEMPLATES_DIR, 'static')


# TODO: 正在运行的项目要有UI展示
# TODO: 项目名称过长的话要有相应的处理（加tooltip）

class Server:

    def __init__(self,
                 title: str = 'PYBT',
                 log_dir: str = '',
                 update_interval: int = 1,
                 debug: bool = False,
                 host: str = '0.0.0.0', port: int = 10000):
        self.title = title
        self.update_interval = update_interval  # 每隔1s刷新一次
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

        self.last_read_id = 0
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
                        "position"       : "bottom",
                        'distance'       : 10,
                        "verticalAlign"  : "middle",
                        "align"          : "center",
                        "fontSize"       : 14,
                        'overflow'       : 'breakAll'
                    },
                    "leaves"                 : {
                        "label": {
                            "backgroundColor": "#fff",
                            "position"       : "bottom",
                            'distance'       : 10,
                            "verticalAlign"  : "middle",
                            "align"          : "center",
                            "fontSize"       : 14,
                            'overflow'       : 'breakAll'
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

                projects.append({
                    'name'  : relative_path,
                    'unread': pybts_data.get('id') - self.last_read_id,
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

        self.last_read_id = track_id

        return jsonify({
            'tree'    : tree_data,
            'subtitle': subtitle,
            'title'   : f"{project}  {log_data['round']}-{log_data['step']} / {log_data['id']}",
            'id'      : log_data['id'],
            'page'    : log_data['id'],
            'total'   : pybts_data['id']
        })
