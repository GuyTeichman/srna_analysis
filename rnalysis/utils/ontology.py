import functools
import io as builtin_io
import queue
import re
import warnings
from typing import Dict, List, Union, Tuple, Iterable, Set
from pathlib import Path
import graphviz
import matplotlib.image as mpimg
import matplotlib.pyplot as plt
import numpy as np
from defusedxml import ElementTree
from matplotlib.cm import ScalarMappable
from typing_extensions import Literal

from rnalysis.utils import parsing


def render_graphviz_plot(graph: graphviz.Digraph, save_path: str, file_format: str):
    try:
        graph.render(Path(save_path).with_suffix(''), view=True, format=file_format)
        return True
    except graphviz.backend.execute.ExecutableNotFound:
        warnings.warn("You must install 'GraphViz' and add it to PATH in order to generate Ontology Graphs. \n"
                      "Please see https://graphviz.org/download/ for more information. ")
        return False


class KEGGEntry:
    NODE_TYPES = {'gene/enzyme': dict(shape='box', style='rounded', label=''),
                  'compound': dict(shape='circle', label=''),
                  'pathway': dict(shape='hexagon', label=''),
                  'complex': dict(shape='record', label='|'),
                  'other': dict(shape='oval', label='')}
    RELATIONSHIP_TYPES = {'ECrel': 'enzyme-enzyme',
                          'PPrel': 'protein-protein',
                          'GErel': 'gene-expression',
                          'PCrel': 'protein-compound'}
    RELATIONSHIP_SUBTYPES = {'compound': {},
                             'activation': {'color': 'red2'},
                             'inhibition': {'color': 'mediumblue', 'arrowhead': 'tee'},
                             'expression': {'color': 'red2', 'style': 'dashed'},
                             'repression': {'color': 'mediumblue', 'arrowhead': 'tee', 'style': 'dashed'},
                             'indirect effect': {'style': 'dotted'},
                             'state change': {'style': 'dotted', 'dir': 'none'},
                             'binding/association': {'style': 'dashed', 'dir': 'none'},
                             'dissociation': {'style': 'dashed', 'color': 'gray32'},
                             'missing interaction': {},
                             'phosphorylation': {'label': 'p+'},
                             'dephosphorylation': {'label': 'p-'},
                             'glycosylation': {'label': 'g+'},
                             'ubiquitination': {'label': 'u+'},
                             'methylation': {'label': 'm+'},
                             'reversible reaction': {'dir': 'both'},
                             'irreversible reaction': {},
                             'unknown': {'label': '?', 'style': 'dashed'}}

    __slots__ = {'_id': 'KEGG ID',
                 '_name': 'KEGG Entry name',
                 '_type': 'KEGG Entry type',
                 '_display_name': 'KEGG Entry display name',
                 'relationships': 'direct parent relationships of the KEGG Entry',
                 'children_relationships': 'direct children relationships of the KEGG Entry'}

    def __init__(self):
        self._id = None
        self._name = None
        self._type = None
        self._display_name = None
        self.relationships: Dict[str, Set[Tuple[int, str]]] = {subtype: set() for subtype in self.RELATIONSHIP_SUBTYPES}
        self.children_relationships: Dict[str, Set[Tuple[int, str]]] = {subtype: set() for subtype in
                                                                        self.RELATIONSHIP_SUBTYPES}

    @classmethod
    def with_properties(cls, kegg_id: int, name: str, entry_type: str, display_name: str):
        entry = cls()
        entry.set_id(kegg_id)
        entry.set_name(name)
        entry.set_type(entry_type)
        entry.set_display_name(display_name)
        return entry

    def degree(self):
        return self.in_degree() + self.out_degree()

    def in_degree(self):
        return sum([len(rel) for rel in self.relationships.values()])

    def out_degree(self):
        return sum([len(rel) for rel in self.children_relationships.values()])

    def set_id(self, kegg_id: int):
        self._id = kegg_id

    def set_name(self, name: str):
        self._name = name

    def set_type(self, entry_type: str):
        self._type = entry_type

    def set_display_name(self, display_name: str):
        self._display_name = display_name

    @property
    def type(self):
        return self._type

    @property
    def name(self):
        return self._name

    @property
    def id(self):
        return self._id

    @property
    def display_name(self):
        return self._display_name


class KEGGPathway:
    __slots__ = {'compounds': 'dict mapping compound IDs to display names',
                 'entries': 'KEGG entries',
                 'name_to_id': 'dict mapping entry names to entry IDs',
                 'id_to_group': 'dict mapping sub-component entry IDs to group IDs',
                 'pathway_id': 'KEGG ID of the pathway',
                 'pathway_name': 'Display name of the pathway'}
    LEGEND_GRAPH = graphviz.Digraph(name='cluster_legend', edge_attr=dict(fontname='Arial'),
                                    node_attr=dict(fontname='Arial', shape='plaintext'),
                                    graph_attr=dict(fontname='Arial', fontsize='20', rankdir='LR'))
    LEGEND_GRAPH.node('key1', label='<<table border="0" cellpadding="14" cellspacing="0" cellborder="0">' + '\n'.join(
        [f'<tr><td align="right" port="rel{i}">{rel}</td></tr>' for i, rel in
         enumerate(KEGGEntry.RELATIONSHIP_SUBTYPES)]) + '\n'.join(
        [f'<tr><td align="right" port="node{i}">{node}</td></tr>' for i, node in
         enumerate(KEGGEntry.NODE_TYPES)]) + '</table>>')

    LEGEND_GRAPH.node('key2',
                      label='<<table border="0" cellpadding="14" cellspacing="0" cellborder="0">' + '\n'.join(
                          [f'<tr><td port="rel{i}">&nbsp;</td></tr>' for i, rel in
                           enumerate(KEGGEntry.RELATIONSHIP_SUBTYPES)]) + '</table>>')

    for node, attrs in KEGGEntry.NODE_TYPES.items():
        LEGEND_GRAPH.node(node, rank='max', margin='0', fixedsize='true', height='0.16', width='0.4', **attrs)
    for i, (rel, attrs) in enumerate(KEGGEntry.RELATIONSHIP_SUBTYPES.items()):
        LEGEND_GRAPH.edge(f'key1:rel{i}', f'key2:rel{i}', **attrs)
    for i, (node, _) in enumerate(KEGGEntry.NODE_TYPES.items()):
        LEGEND_GRAPH.edge(f'key1:node{i}', f'{node}', style='invis')

    LEGEND_GRAPH_STR = LEGEND_GRAPH.pipe(format='png')

    del node, attrs, i, rel

    def __init__(self, kgml_tree: ElementTree, compounds: Dict[str, str]):
        self.compounds = compounds
        self.entries: Dict[int, KEGGEntry] = {}
        self.name_to_id: Dict[str, int] = {}
        self.id_to_group: Dict[int, int] = {}
        root = kgml_tree.getroot()
        self.pathway_id = root.get('name')
        self.pathway_name = root.get('title')
        self.parse_pathway(kgml_tree)

    def __getitem__(self, key) -> 'KEGGEntry':
        if key in self.entries:
            return self.entries[key]
        elif key in self.name_to_id:
            return self.__getitem__(self.name_to_id[key])
        raise KeyError(key)

    def __contains__(self, item) -> bool:
        try:
            _ = self[item]
            return True
        except KeyError:
            return False

    def parse_pathway(self, kgml_tree: ElementTree):
        for element in kgml_tree.getroot():
            if element.tag == 'entry':
                elem_id = int(element.get('id'))
                elem_name = element.get('name')
                elem_type = element.get('type')

                if elem_type == 'group':
                    ids = []
                    for sub in element:
                        if sub.tag == 'component':
                            ids.append(sub.get('id'))
                            self.id_to_group[int(sub.get('id'))] = elem_id
                    display_name = ids
                elif elem_type == 'compound':
                    display_name = self.compounds[elem_name].replace(' ', '\n')
                else:
                    display_name = element[0].get('name').split(',')[0]
                entry = KEGGEntry.with_properties(elem_id, elem_name, elem_type, display_name)
                self.entries[entry.id] = entry
                self.name_to_id[entry.name] = entry.id

        for element in kgml_tree.getroot():
            if element.tag == 'relation':
                pred = int(element.get('entry1'))
                succ = int(element.get('entry2'))
                if len(element) == 0:
                    if element.get('type') == 'PCrel':
                        rel_type = 'compound'
                        rel_symbol = '->'
                    elif element.get('type') == 'maplink':
                        rel_type = 'missing interaction'
                        rel_symbol = '->'
                    else:
                        rel_type = 'unknown'
                        rel_symbol = '?'
                    self._add_relation(pred, succ, rel_type, rel_symbol)

                for sub in element:
                    rel_type = sub.get('name')
                    rel_symbol = sub.get('value')
                    if rel_type == 'compound':
                        compound = int(rel_symbol)
                        self._add_relation(pred, compound, rel_type, '->')
                        self._add_relation(compound, succ, rel_type, '->')
                    else:
                        self._add_relation(pred, succ, rel_type, rel_symbol)

            elif element.tag == 'reaction':
                enzyme = int(element.get('id'))
                substrates = []
                products = []
                for sub_elem in element:
                    if sub_elem.tag == 'substrate':
                        substrates.append(int(sub_elem.get('id')))
                    elif sub_elem.tag == 'product':
                        products.append(int(sub_elem.get('id')))

                rel_type = 'reversible reaction' if element.get('type') == 'reversible' else 'irreversible reaction'
                rel_symbol = '<->' if rel_type == 'reversible reaction' else '->'
                for substrate in substrates:
                    self._add_relation(substrate, enzyme, rel_type, rel_symbol)
                for product in products:
                    self._add_relation(enzyme, product, rel_type, rel_symbol)

    def _add_relation(self, pred: int, succ: int, rel_type: str, rel_symbol: str):
        self.entries[pred].relationships[rel_type].add((succ, rel_symbol))
        self.entries[succ].children_relationships[rel_type].add((pred, rel_symbol))

    def plot_pathway(self, save_path: str, significant: Union[set, dict, None] = None, ylabel: str = '', dpi: int = 300,
                     graph_format: Literal['pdf', 'png', 'svg'] = 'pdf'):
        if significant is None:
            significant = {}
        elif isinstance(significant, dict):
            # colormap
            scores_no_inf = [i for i in significant.values() if i != np.inf and i != -np.inf and i < 0]
            if len(scores_no_inf) == 0:
                scores_no_inf.append(-1)
            max_score = max(np.max(scores_no_inf), 2)
            my_cmap = plt.cm.get_cmap('coolwarm')

        # generate graph
        main_graph = graphviz.Digraph()
        main_graph.attr(dpi=str(dpi), fontname='Arial', rankdir='LR', newrank='true', compound='true')

        kegg_graph = graphviz.Digraph('cluster_kegg',
                                      graph_attr=dict(dpi=str(dpi), fontname='Arial', color='white', rankdir='LR'),
                                      node_attr=dict(fontname='Arial'), edge_attr=dict(fontname='Arial'))

        for entry in self.entries:
            this_type = self.entries[entry].type
            if entry in self.id_to_group or (self.entries[entry].degree() == 0 and this_type != 'group'):
                continue
            if this_type == 'gene':
                kwargs = dict(shape='box', style='rounded')
            elif this_type == 'compound':
                kwargs = dict(shape='circle')
            elif this_type == 'map':
                kwargs = dict(shape='hexagon')
            elif this_type == 'group':
                kwargs = dict(shape='none')
            else:
                kwargs = dict(shape='oval')

            # color significant nodes according to their enrichment score
            if this_type == 'group':
                label = '<<table rows="*" cellspacing="0" cellborder="0" border="2">'
                for child in self.entries[entry].display_name:
                    child = int(child)
                    label += '<tr><td '
                    if self.entries[child].name in significant:
                        if isinstance(significant, set):
                            label += 'bgcolor="green" '
                        elif isinstance(significant, dict):
                            this_score = significant[self.entries[child].name]
                            color_norm = 0.5 * (1 + this_score / (np.floor(max_score) + 1)) * 255
                            color_norm_8bit = int(
                                color_norm) if color_norm != np.inf and color_norm != -np.inf else np.sign(
                                color_norm) * max(np.abs(scores_no_inf))
                            color = tuple([int(i * 255) for i in my_cmap(color_norm_8bit)[:-1]])
                            color_str = '#%02x%02x%02x' % color
                            label += f'bgcolor="{color_str}" '
                            if int(np.mean(color)) < 128:
                                label += 'color="#ffffff" '
                    label += f'port="loc{child}">{self.entries[child].display_name}</td></tr>'
                label += '</table>>'
            else:
                label = self[entry].display_name

            if self.entries[entry].name in significant:
                kwargs['style'] = 'rounded, filled'
                if isinstance(significant, set):
                    kwargs['fillcolor'] = 'green'
                elif isinstance(significant, dict):
                    this_score = significant[self.entries[entry].name]
                    color_norm = 0.5 * (1 + this_score / (np.floor(max_score) + 1)) * 255
                    color_norm_8bit = int(color_norm) if color_norm != np.inf and color_norm != -np.inf else np.sign(
                        color_norm) * max(np.abs(scores_no_inf))
                    color = tuple([int(i * 255) for i in my_cmap(color_norm_8bit)[:-1]])
                    kwargs['fillcolor'] = '#%02x%02x%02x' % color
                    if int(np.mean(color)) < 128:
                        kwargs['fontcolor'] = '#ffffff'

            kegg_graph.node(str(entry), label=label, **kwargs)

        # add edges from relationships
        for entry in self.entries:
            for relationship_type in self[entry].relationships:
                for child, _ in self[entry].relationships[relationship_type]:
                    if entry in self.id_to_group:
                        first_id = f"{self.id_to_group[entry]}:loc{entry}"
                    else:
                        first_id = str(entry)

                    if child in self.id_to_group:
                        second_id = f"{self.id_to_group[child]}:loc{child}"
                    else:
                        second_id = str(child)

                    kegg_graph.edge(first_id, second_id, **KEGGEntry.RELATIONSHIP_SUBTYPES[relationship_type])

        main_graph.subgraph(kegg_graph)
        main_graph.subgraph(self.LEGEND_GRAPH)
        # show graph in a matplotlib window
        res = render_graphviz_plot(main_graph, save_path, graph_format)
        if not res:
            return False
        fig, axes = plt.subplots(1, 2, figsize=(14, 9), constrained_layout=True, gridspec_kw=dict(width_ratios=[3, 1]))
        fig.suptitle(f'KEGG Pathway: {self.pathway_name}', fontsize=24)

        kegg_png_str = kegg_graph.pipe(format='png')
        for ax, png_str in zip(axes, [kegg_png_str, self.LEGEND_GRAPH_STR]):
            sio = builtin_io.BytesIO()
            sio.write(png_str)
            sio.seek(0)
            img = mpimg.imread(sio)
            ax.imshow(img, aspect='equal')
            ax.set_xticks([])
            ax.set_yticks([])
        axes[0].axis('off')
        axes[1].set_title('Legend', fontsize=14)

        # determine bounds, and enlarge the bound by a small margin (0.2%) so nothing gets cut out of the figure
        if isinstance(significant, dict) and len(significant) > 0:
            # add colorbar
            bounds = np.array([np.ceil(-max_score) - 1, (np.floor(max_score) + 1)]) * 1.002
            sm = ScalarMappable(cmap=my_cmap, norm=plt.Normalize(*bounds))
            sm.set_array(np.array([]))
            cbar_label_kwargs = dict(label=ylabel, fontsize=12, labelpad=4)
            cbar = fig.colorbar(sm, ticks=range(int(bounds[0]), int(bounds[1]) + 1), location='bottom')
            cbar.set_label(**cbar_label_kwargs)
            cbar.ax.tick_params(labelsize=10, pad=2)

        plt.show()
        return True


class GOTerm:
    __slots__ = {'_id': 'GO ID', '_name': 'GO Term name',
                 '_namespace': 'biological_process, cellular_component or molecular_function',
                 '_level': "GO Term's level in the DAG Tree",
                 'relationships': 'direct parent relationships of the GO Term',
                 'children_relationships': 'direct children relationships of the GO Term'}

    def __init__(self):
        self._id: str = None
        self._name: str = None
        self._namespace: str = None
        self._level: int = None
        self.relationships: Dict[str, List[str]] = {'is_a': [], 'part_of': []}
        self.children_relationships: Dict[str, List[str]] = {'is_a': [], 'part_of': []}

    @classmethod
    def with_properties(cls, go_id: str, name: str, namespace: str, level: int):
        go_term = cls()
        go_term.set_id(go_id)
        go_term.set_name(name)
        go_term.set_namespace(namespace)
        go_term.set_level(level)
        return go_term

    @property
    def id(self) -> str:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    @property
    def namespace(self) -> str:
        return self._namespace

    @property
    def level(self) -> int:
        return self._level

    def set_id(self, go_id: str):
        self._id = go_id

    def set_name(self, name: str):
        self._name = name

    def set_namespace(self, namespace: str):
        self._namespace = namespace

    def set_level(self, level: int):
        self._level = level

    @functools.lru_cache(maxsize=2)
    def get_parents(self, relationships: Union[str, tuple] = ('is_a', 'part_of')) -> List[str]:
        relationships_filt = [rel for rel in parsing.data_to_list(relationships) if rel in self.relationships]
        go_ids = [go_id for rel in relationships_filt for go_id in self.relationships[rel]]
        return go_ids

    @functools.lru_cache(maxsize=2)
    def get_children(self, relationships: Union[str, Tuple[str]] = ('is_a', 'part_of')) -> List[str]:
        relationships_filt = [rel for rel in parsing.data_to_list(relationships) if rel in self.children_relationships]
        go_ids = [go_id for rel in relationships_filt for go_id in self.children_relationships[rel]]
        return go_ids


def parse_go_id(sequence: str) -> str:
    return re.findall("GO:[0-9]{7}", sequence)[0]


class DAGTree:
    __slots__ = {'data_version': 'version of the go-basic.obo file',
                 'go_terms': 'dictionary of GO Terms in the DAG Tree',
                 'alt_ids': 'mapping of alternative GO IDs to their main GO ID',
                 'namespaces': "namespaces included in the DAGTree",
                 'levels': 'list of levels in the DAG Tree',
                 'parent_relationship_types': 'the types of relationships that constitute parenthood in the DAG Tree',
                 '_upper_induced_graphs': 'memoized upper-induced graphs'}

    def __init__(self, line_iterator: Iterable[str],
                 parent_relationship_types: Union[str, Iterable[str]] = ('is_a', 'part_of')):
        self.data_version = None
        self.go_terms: Dict[str, GOTerm] = {}
        self.alt_ids: Dict[str, str] = {}
        self.namespaces: Set[str] = set()
        self.levels: List[dict] = []
        self.parent_relationship_types: tuple = parsing.data_to_tuple(parent_relationship_types)

        self._upper_induced_graphs: Dict[str, Set[str]] = {}

        self._parse_file(line_iterator)
        self._populate_levels()
        self._populate_children()

    def __getitem__(self, key) -> 'GOTerm':
        if key in self.go_terms:
            return self.go_terms[key]
        elif key in self.alt_ids:
            return self.go_terms[self.alt_ids[key]]
        raise KeyError(key)

    def __contains__(self, item):
        try:
            _ = self[item]
            return True
        except KeyError:
            return False

    def _parse_file(self, line_iterator: Iterable[str]):
        current_term = None
        in_frame = False
        for line in line_iterator:
            line = line.strip()
            if in_frame:
                if line.startswith('id: '):
                    current_term.set_id(parse_go_id(line))
                elif line.startswith('namespace: '):
                    current_term.set_namespace(line[11:])
                    if current_term.namespace not in self.namespaces:
                        self.namespaces.add(current_term.namespace)
                elif line.startswith('name: '):
                    current_term.set_name(line[6:])
                elif line.startswith('alt_id: '):
                    self.alt_ids[parse_go_id(line)] = current_term.id
                elif line.startswith('is_a: '):
                    current_term.relationships['is_a'].append(parse_go_id(line))
                elif line.startswith('relationship: '):
                    relationship_type = line.split(' ')[1]
                    if relationship_type not in current_term.relationships:
                        current_term.relationships[relationship_type] = []
                    current_term.relationships[relationship_type].append(parse_go_id(line))
                elif line.startswith('is_obsolete: true'):
                    in_frame = False
                elif line == '':
                    self.go_terms[current_term.id] = current_term
                    in_frame = False
            else:
                if line.startswith('[Term]'):
                    current_term = GOTerm()
                    in_frame = True
                elif line.startswith('data-version:'):
                    self.data_version = line[14:]

        if in_frame:  # add last go term to the set, if it was not already added
            self.go_terms[current_term.id] = current_term

    def _populate_levels(self):
        levels_dict = {}
        for go_term in self.go_terms.values():
            if go_term.level is None:
                go_term.set_level(self._get_term_level_rec(go_term))
            if go_term.level not in levels_dict:
                levels_dict[go_term.level] = {}
            levels_dict[go_term.level][go_term.id] = go_term
        if len(levels_dict) == 0:
            self.levels = [{}]
        else:
            self.levels = [levels_dict[i] for i in range(0, max(levels_dict.keys()) + 1)]

    def _get_term_level_rec(self, go_term: GOTerm):
        if go_term.level is not None:
            pass
        elif len(go_term.get_parents(self.parent_relationship_types)) == 0:
            go_term.set_level(0)
        else:
            go_term.set_level(1 + max([self._get_term_level_rec(self[parent_id]) for parent_id in
                                       go_term.get_parents(self.parent_relationship_types)]))
        return go_term.level

    def _populate_children(self):
        for go_id in self.level_iter():
            for rel_type in self.parent_relationship_types:
                for parent_id in self[go_id].get_parents(rel_type):
                    if rel_type not in self[parent_id].children_relationships:
                        self[parent_id].children_relationships[rel_type] = []
                    self[parent_id].children_relationships[rel_type].append(go_id)

    def level_iter(self, namespace: str = 'all'):
        if namespace == 'all':
            for level in self.levels[::-1]:
                for go_id in level:
                    yield go_id
        else:
            for level in self.levels[::-1]:
                for go_id in level:
                    if self[go_id].namespace == namespace:
                        yield go_id

    def upper_induced_graph_iter(self, go_id: str):
        if go_id in self._upper_induced_graphs:
            for upper_induced_node in self._upper_induced_graphs[go_id]:
                yield upper_induced_node

        else:
            # put go_id's parents into the queue
            node_queue = queue.SimpleQueue()
            processed_nodes = set()
            parents = self[go_id].get_parents(self.parent_relationship_types)
            for parent in parents:
                node_queue.put(parent)
            processed_nodes.update(parents)
            # iterate over the queue until it is empty (meaning we reached the top of the graph)
            while not node_queue.empty():
                this_node = node_queue.get()
                yield this_node
                # if this_node's upper-induced graph was already calculated, yield those unprocessed nodes
                if this_node in self._upper_induced_graphs:
                    for upper_induced_node in self._upper_induced_graphs[this_node]:
                        if upper_induced_node not in processed_nodes:
                            yield upper_induced_node
                    processed_nodes.update(self._upper_induced_graphs[this_node])
                # if this_node's upper-induced graph was yet to be calculated, add its unprocessed parents to the queue
                else:
                    parents = self[this_node].get_parents(self.parent_relationship_types)
                    for parent in parents:
                        if parent not in processed_nodes:
                            node_queue.put(parent)
                    processed_nodes.update(parents)
            # memoize the function's output for go_id
            self._upper_induced_graphs[go_id] = processed_nodes
