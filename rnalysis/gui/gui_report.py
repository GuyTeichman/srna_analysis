import itertools
import re
import shutil
import typing
import webbrowser
from pathlib import Path

import networkx
from pyvis.network import Network
from typing import Literal

from rnalysis import __version__
from rnalysis.utils import parsing, io


class Node:
    __slots__ = ('_node_id', '_node_name', '_predecessors', '_is_active', '_popup_element', '_node_type', '_filename')
    DATA_TYPES = {'Count matrix', 'Differential expression', 'Fold change', 'Other table', 'Gene set', 'Other output',
                  'Pipeline'}

    def __init__(self, node_id: int, node_name: str, predecessors: list, popup_element: str, node_type: str,
                 filename: str = None):
        self._node_id = node_id
        self._node_name = node_name
        self._predecessors = parsing.data_to_set(predecessors)
        self._popup_element = popup_element
        self._node_type = node_type
        self._is_active = True
        self._filename = None if filename is None else Path(filename)
        self._filename = filename
        if node_type in self.DATA_TYPES:
            self._node_name += f' (#{node_id})'

    @property
    def node_id(self) -> int:
        return self._node_id

    @property
    def node_name(self) -> str:
        return self._node_name

    @property
    def predecessors(self) -> typing.Set[int]:
        return self._predecessors

    @property
    def popup_element(self) -> str:
        return self._popup_element

    @property
    def node_type(self) -> str:
        return self._node_type

    @property
    def is_active(self) -> bool:
        return self._is_active

    @property
    def filename(self) -> str:
        return self._filename

    def set_active(self, is_active: bool):
        self._is_active = is_active

    def add_predecessor(self, pred: int):
        self._predecessors.add(pred)


class ReportGenerator:
    CSS_TEMPLATE_PATHS = [Path(__file__).parent.parent.joinpath('data_files/report_templates/vis-network.min.css'),
                          Path(__file__).parent.parent.joinpath('data_files/report_templates/bootstrap.min.css')]
    JS_TEMPLATE_PATHS = [Path(__file__).parent.parent.joinpath('data_files/report_templates/vis-network.min.js'),
                         Path(__file__).parent.parent.joinpath('data_files/report_templates/bootstrap.bundle.min.js')]
    NODE_STYLES = {'root': dict(shape='box', color='#00D4D8'),
                   'Count matrix': dict(color='#0D47A1'),
                   'Differential expression': dict(color='#BF360C'),
                   'Fold change': dict(color='#00838F'),
                   'Other table': dict(color='#F7B30A'),
                   'Gene set': dict(color='#BA68C8'),
                   'Function': dict(shape='triangleDown', color='#00D4D8'),
                   'Other output': dict(shape='square', color='#228B22'),
                   'Pipeline': dict(shape='diamond', color='#FF66B8')}
    ROOT_FNAME = 'session.rnal'
    TITLE = f"Data analysis report (<i>RNAlysis</i> version {__version__})"

    def __init__(self):
        self.graph = networkx.DiGraph()
        self.nodes: typing.Dict[int, Node] = {}
        self.create_legend()
        href = Path('data').joinpath(self.ROOT_FNAME).as_posix()
        root_desc = f'<a href="{href}" target="_blank" rel="noopener noreferrer">Open RNAlysis session</a>'
        self.add_node('Started RNAlysis session', 0, [], root_desc, node_type='root', filename=self.ROOT_FNAME)

    def create_legend(self):
        x = -750
        y = -350
        step = 75
        for node_type, kwargs in self.NODE_STYLES.items():
            if node_type in {'root'}:
                continue
            self.graph.add_node(node_type, label=node_type.capitalize(), fixed=True, physics=False, x=x, y=y,
                                font={'size': 16}, widthConstraint=100, **kwargs)
            y += step

    def add_node(self, name: str, node_id: int, predecessors: typing.List[int] = (0,), popup_element: str = '',
                 node_type: Literal[tuple(NODE_STYLES)] = 'Other table', filename: str = None):
        if node_id in self.nodes:
            if self.nodes[node_id].is_active:
                return
            node = self.nodes[node_id]
            node.set_active(True)

            for pred in predecessors:
                if not self.nodes[pred].is_active:
                    self.add_node('', pred)
        else:
            node = Node(node_id, name, predecessors, popup_element, node_type, filename)
            self.nodes[node_id] = node
        kwargs = self.NODE_STYLES[node.node_type]
        self.graph.add_node(node.node_id, label=node.node_name, title=node.popup_element, **kwargs)
        for pred in predecessors:
            self.graph.add_edge(pred, node_id)

    def trim_node(self, node_id: int):
        """
        Removes a node from the report graph if it is a leaf node with no outgoing edges, \
        and trims any of its predecessors that are of type 'Function' and are also now leaf nodes.

        :param node_id: The ID of the node to be trimmed.
        :type node_id: int

        This method checks if the specified node is present in the report graph, and if it is a leaf node \
        with no outgoing edges. If both conditions are met, the node is removed from the graph, \
        its corresponding `ReportNode` object is set to inactive, and any of its predecessors that are of type \
        'Function' are recursively checked to see if they are now leaf nodes themselves (i.e., have no outgoing edges).\
         If a predecessor is a leaf node, it is also trimmed from the graph and marked as inactive.

        This method is used for pruning the report graph of unnecessary nodes when a tab is closed \
        or an action is undone.
            """
        if node_id in self.graph and self.graph.out_degree(node_id) == 0:
            predecessors = self.graph.predecessors(node_id)
            self.graph.remove_node(node_id)
            self.nodes[node_id].set_active(False)
            for pred in predecessors:
                if self.nodes[pred].node_type == 'Function':
                    self.trim_node(pred)

    def _modify_html(self, html: str) -> str:
        if html.count(self.TITLE) > 1:
            html = re.sub(r'<center>.+?<\/h1>\s+<\/center>', '', html, 1, re.DOTALL)
        # remove comments from file
        comment_regex = r"<!--[\s\S]*?-->"
        html = re.sub(comment_regex, "", html)

        for css_pth in self.CSS_TEMPLATE_PATHS:
            css_line = f'<link rel="stylesheet" href="assets/{css_pth.name}"/>'
            html = re.sub(r'<link(?:\s+[\w-]+="[^"]*")*\s+href="[^"]+"\s+(?:[\w-]+="[^"]*"\s+)*?\/>', css_line, html, 1,
                          re.DOTALL)

        for js_pth in self.JS_TEMPLATE_PATHS:
            js_line = f'<script src="assets/{js_pth.name}"></script>'
            html = re.sub(r'<script\s+src\s*=\s*"(https?:\/\/[^"]+\.js)"[^>]*><\/script>', js_line, html, 1, re.DOTALL)

        return html

    def _report_from_nx(self, show_buttons: bool) -> Network:
        vis_report = Network(directed=True, layout=False, heading=self.TITLE)
        vis_report.from_nx(self.graph)
        enabled_str = 'true' if show_buttons else 'false'

        vis_report.set_options("""const options = {
            "configure": {"""
                               f'"enabled": {enabled_str}'
                               """
            },
            "layout": {
                "hierarchical": {
                    "enabled": false,
                    "levelSeparation": 250,
                    "nodeSpacing": 250,
                    "treeSpacing": 250,
                    "direction": "LR",
                    "sortMethod": "directed"
                }
            },
            "physics": {
                "solver": "repulsion"
            },
            "interaction": {
            "navigationButtons": true
            }
        }""")
        return vis_report

    def generate_report(self, save_path: Path, show_buttons: bool = True):
        assert save_path.exists() and save_path.is_dir()
        save_file = save_path.joinpath('report.html').as_posix()
        vis_report = self._report_from_nx(show_buttons)
        html = self._modify_html(vis_report.generate_html(save_file))

        with open(save_file, 'w') as f:
            f.write(html)

        assets_path = save_path.joinpath('assets')
        if assets_path.exists():
            shutil.rmtree(assets_path)
        assets_path.mkdir()
        for item in itertools.chain(self.CSS_TEMPLATE_PATHS, self.JS_TEMPLATE_PATHS):
            with open(item, encoding="utf-8") as f:
                content = f.read()
            with open(assets_path.joinpath(item.name), 'w', encoding="utf-8") as outfile:
                outfile.write(content)

        data_path = save_path.joinpath('data')
        if data_path.exists():
            shutil.rmtree(data_path)
        data_path.mkdir()

        for ind, node in self.nodes.items():
            if ind == 0:  # skip the root node
                continue
            if node.is_active and node.filename is not None:
                content: bytes = io.load_cached_gui_file(node.filename, load_as_obj=False)
                if content is not None:
                    with open(data_path.joinpath(node.filename), 'wb') as f:
                        f.write(content)
        webbrowser.open(save_file)
