from unittest import mock
from unittest.mock import MagicMock

import pytest
import requests_mock

from rnalysis.utils import io
from rnalysis.utils.io import *
from rnalysis.utils.io import _ensembl_lookup_post_request, _format_ids_iter
from tests import (is_ensembl_available, is_phylomedb_available,
                   is_uniprot_available)

ENSEMBL_AVAILABLE = is_ensembl_available()
UNIPROT_AVAILABLE = is_uniprot_available()
PHYLOMEDB_AVAILABLE = is_phylomedb_available()


class MockResponse(object):
    def __init__(self, status_code: int = 200, url: str = 'http://httpbin.org/get', headers: dict = 'default',
                 text: str = '', json_output: dict = dict(), content: str = ''):
        self.status_code = status_code
        self.url = url
        self.headers = {'default': 'default'} if headers == 'default' else headers
        self.text = text
        self.ok = self.status_code == 200
        self._json = json_output
        self.content = bytes(content, 'utf8')

    def raise_for_status(self):
        if not self.ok:
            raise ConnectionError('request not ok')

    def json(self):
        return self._json

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return


class AsyncMockResponse(MockResponse):
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    async def json(self):
        return self._json


def test_load_csv_bad_input():
    invalid_input = 2349
    with pytest.raises(AssertionError):
        load_table(invalid_input)


@pytest.mark.parametrize('pth', ("tests/test_files/test_load_csv.csv", "tests/test_files/test_load_csv.tsv",
                                 "tests/test_files/test_load_csv_tabs.txt",
                                 "tests/test_files/test_load_csv_other_sep.txt"))
def test_load_csv(pth):
    truth = pl.DataFrame({'idxcol': ['one', 'two', 'three'], 'othercol': [4, 5, 6]})
    loaded = load_table(pth)
    print(truth)
    print(loaded)
    assert loaded.equals(truth)


def test_load_csv_drop_columns():
    loaded = load_table('tests/test_files/counted.csv', drop_columns='cond1')
    print(loaded)
    assert list(loaded.columns) == ['', 'cond2', 'cond3', 'cond4']

    loaded = load_table('tests/test_files/counted.csv', drop_columns=['cond2', 'cond4'])
    assert list(loaded.columns) == ['', 'cond1', 'cond3']

    with pytest.raises(IndexError):
        load_table('tests/test_files/counted.csv', drop_columns=['cond1', 'cond6'])


def test_save_csv():
    try:
        df = pl.read_csv('tests/test_files/enrichment_hypergeometric_res.csv')
        save_table(df, 'tests/test_files/tmp_test_save_csv.csv')
        df_loaded = pl.read_csv('tests/test_files/tmp_test_save_csv.csv')
        assert df.equals(df_loaded)
        df = pl.read_csv('tests/test_files/enrichment_hypergeometric_res.csv')
        save_table(df, 'tests/test_files/tmp_test_save_csv.csv', '_2')
        df_loaded = pl.read_csv('tests/test_files/tmp_test_save_csv_2.csv')
        df = pl.read_csv('tests/test_files/enrichment_hypergeometric_res.csv')
        assert df.equals(df_loaded)

    except Exception as e:
        raise e
    finally:
        try:
            os.remove('tests/test_files/tmp_test_save_csv.csv')
            os.remove('tests/test_files/tmp_test_save_csv_2.csv')
        except:
            pass


def test_obo_basic_stream_connectivity():
    _ = get_obo_basic_stream()


def test_format_ids_iter():
    assert list(_format_ids_iter('one two three')) == ['one two three']
    assert list(_format_ids_iter(123)) == ['123']
    assert list(_format_ids_iter(['one', ' two', 'three; ', 'four'])) == ['one  two three;  four']
    assert list(_format_ids_iter(['1', 'two', '3', '4', 'five', '6', '7'], 3)) == ['1 two 3', '4 five 6', '7']


def test_gene_id_translator_api():
    _ = GeneIDDict({1: 2, 3: 4})
    _ = GeneIDDict()


def test_gene_id_translator_getitem():
    translator = GeneIDDict({1: 2, 3: 4})
    assert translator[1] == 2
    assert translator[3] == 4
    translator = GeneIDDict(None)
    for something in [2, 3, '1', False, True, {}, 3.141592]:
        assert translator[something] == something


def test_gene_id_translator_contains():
    translator = GeneIDDict({1: 2, 3: 4})
    assert 1 in translator and 3 in translator
    for invalid in [2, 4, '1', False]:
        assert invalid not in translator
    translator = GeneIDDict(None)
    for something in [2, 3, '1', False, True, {}, 3.141592]:
        assert something in translator


@pytest.mark.parametrize("test_input,expected", [
    ('any', {'aspect a', 'aspect b', 'aspect c'}),
    ('Asp_B', {'aspect b'}),
    (['asp_b'], {'aspect b'}),
    (['a', 'z', 'c'], {'aspect a', 'aspect c', 'z'}),
    (['asp_b', 'c', 'A'], {'aspect a', 'aspect b', 'aspect c'}),
    (['aspect z'], {'aspect z'})
])
def test_golr_annotation_iterator_parse_go_aspects(monkeypatch, test_input, expected):
    go_dict = {'a': 'aspect a', 'asp_b': 'aspect b', 'c': 'aspect c', '_a_': 'aspect a'}
    monkeypatch.setattr(GOlrAnnotationIterator, '_ASPECTS_DICT', go_dict)
    assert GOlrAnnotationIterator._parse_go_aspects(test_input) == expected


def test_golr_annotation_iterator_api(monkeypatch):
    def null_method(self):
        pass

    def parse_method(self, param):
        return set()

    monkeypatch.setattr(GOlrAnnotationIterator, '_generate_query', null_method)
    monkeypatch.setattr(GOlrAnnotationIterator, '_get_n_annotations', null_method)
    monkeypatch.setattr(GOlrAnnotationIterator, '_parse_go_aspects', parse_method)
    monkeypatch.setattr(GOlrAnnotationIterator, '_parse_evidence_types', parse_method)

    GOlrAnnotationIterator(1234)


@pytest.mark.parametrize("test_input,expected", [
    ('any', {'eva', 'evb', 'evc', 'evd', 'eve'}),
    ('bc', {'evb', 'evc'}),
    ('c', {'evc'}),
    ({'a', 'bc', 'f'}, {'eva', 'evb', 'evc', 'f'}),
    ({'a', 'ab'}, {'eva', 'evb'}),
    ({'z', 'v'}, {'z', 'v'}),
    (None, set())
])
def test_golr_annotation_iterator_parse_evidence_types(monkeypatch, test_input, expected):
    ev_dict = {'a': 'eva', 'b': 'evb', 'c': 'evc', 'ab': {'eva', 'evb'}, 'bc': {'evb', 'evc'}, 'de': {'evd', 'eve'}}
    monkeypatch.setattr(GOlrAnnotationIterator, '_EVIDENCE_TYPE_DICT', ev_dict)
    assert GOlrAnnotationIterator._parse_evidence_types(test_input) == expected


def test_golr_annotation_iterator_get_n_annotations(monkeypatch):
    num_found_truth = 126311

    def fake_request(self, params, cached_filename):
        assert isinstance(self, GOlrAnnotationIterator)
        assert isinstance(params, dict)
        assert cached_filename == 'test.json'
        with open('tests/test_files/golr_header.txt') as f:
            return f.readline()

    monkeypatch.setattr(GOlrAnnotationIterator, '_golr_request', fake_request)
    monkeypatch.setattr(GOlrAnnotationIterator, '_generate_cached_filename', lambda self, start: 'test.json')
    golr = GOlrAnnotationIterator.__new__(GOlrAnnotationIterator)
    golr.default_params = {}

    assert golr._get_n_annotations() == num_found_truth


def test_golr_annotation_iterator_generate_query():
    golr = GOlrAnnotationIterator.__new__(GOlrAnnotationIterator)
    golr.aspects = {'P', 'C'}
    golr.databases = {'DB1', 'DB2'}
    golr.evidence_types = {'IEA', 'IMP'}
    golr.excluded_databases = set()
    golr.excluded_evidence_types = {'EXP', 'IDA'}
    golr.excluded_qualifiers = {'not_a'}
    golr.qualifiers = set()
    golr.taxon_id = 6239

    aspects_iter = iter(golr.aspects)
    db_iter = iter(golr.databases)
    evidence_iter = iter(golr.evidence_types)

    query_truth = ['document_category:"annotation"', 'taxon:"NCBITaxon:6239"',
                   f'source:"{next(db_iter)}" OR source:"{next(db_iter)}"',
                   f'evidence_type:"{next(evidence_iter)}" OR evidence_type:"{next(evidence_iter)}"',
                   '-qualifier:"not_a"', '-evidence_type:"EXP"',
                   '-evidence_type:"IDA"', f'aspect:"{next(aspects_iter)}" OR aspect:"{next(aspects_iter)}"']

    assert sorted(golr._generate_query()) == sorted(query_truth)


def test_golr_annotation_iterator_golr_request_connectivity(monkeypatch):
    fake_params = {'param': 'value', 'other_param': 'other_value'}
    session = get_session(GOlrAnnotationIterator.RETRIES)
    golr_it = GOlrAnnotationIterator.__new__(GOlrAnnotationIterator)
    golr_it.session = session
    assert isinstance(golr_it._golr_request(fake_params), str)


def remove_cached_test_file(cached_filename: str):
    try:
        os.remove(get_todays_cache_dir().joinpath(cached_filename))
    except FileNotFoundError:
        pass


def test_golr_annotation_iterator_golr_request(monkeypatch):
    cached_filename = 'test.json'
    remove_cached_test_file(cached_filename)

    correct_url = GOlrAnnotationIterator.URL
    correct_params = {'param': 'value', 'other_param': 'other_value'}

    def mock_get(self, url, params: dict):
        assert url == correct_url
        assert params == correct_params
        return MockResponse(text='the correct text')

    monkeypatch.setattr(requests.Session, 'get', mock_get)
    monkeypatch.setattr(GOlrAnnotationIterator, '_generate_cached_filename', lambda self, start: 'test.json')
    session = get_session(GOlrAnnotationIterator.RETRIES)
    golr_it = GOlrAnnotationIterator.__new__(GOlrAnnotationIterator)
    golr_it.session = session
    assert golr_it._golr_request(correct_params, cached_filename) == 'the correct text'

    def mock_get_uncached(self, url, params: dict):
        raise AssertionError("This function should not be called if a cached file was found!")

    monkeypatch.setattr(requests.Session, 'get', mock_get_uncached)
    try:
        assert golr_it._golr_request(correct_params, cached_filename) == 'the correct text'
    finally:
        remove_cached_test_file(cached_filename)

    def mock_get_failed(self, url, params: dict):
        assert url == correct_url
        assert params == correct_params
        return MockResponse(text='the correct text', status_code=404)

    monkeypatch.setattr(requests.Session, 'get', mock_get_failed)
    try:
        with pytest.raises(ConnectionError):
            _ = golr_it._golr_request(correct_params)
    finally:
        remove_cached_test_file(cached_filename)


def test_golr_annotation_iterator_parsing(monkeypatch):
    truth_params = {
        "q": "*:*",
        "wt": "json",  # return format
        "rows": 5,  # how many rows to return
        # how many annotations to fetch (fetch 0 to find n_annotations, then fetch in iter_size increments
        "start": 0,  # from which annotation number to start fetching
        "fq": ['document_category:"annotation"', 'taxon:"NCBITaxon:6239"'],  # search query
        "fl": "source,bioentity_internal_id,annotation_class",  # fields
        "omitHeader": 'true'}

    records_truth = [{"source": "WB", "bioentity_internal_id": "WBGene00011482", "annotation_class": "GO:0003923"},
                     {"source": "WB", "bioentity_internal_id": "WBGene00011482", "annotation_class": "GO:0016255"},
                     {"source": "WB", "bioentity_internal_id": "WBGene00011481", "annotation_class": "GO:0004190"},
                     {"source": "WB", "bioentity_internal_id": "WBGene00011481", "annotation_class": "GO:0005783"},
                     {"source": "WB", "bioentity_internal_id": "WBGene00011481", "annotation_class": "GO:0005789"}]

    def fake_request(self, params, cached_filename):
        assert isinstance(self, GOlrAnnotationIterator)
        assert params == truth_params
        assert cached_filename == 'test.json'
        with open('tests/test_files/golr_response.txt') as f:
            return f.readline()

    monkeypatch.setattr(GOlrAnnotationIterator, '_golr_request', fake_request)
    monkeypatch.setattr(GOlrAnnotationIterator, '_generate_cached_filename', lambda self, start: 'test.json')

    request_params = {
        "q": "*:*",
        "wt": "json",  # return format
        "rows": 5,  # how many rows to return
        # how many annotations to fetch (fetch 0 to find n_annotations, then fetch in iter_size increments
        "fq": ['document_category:"annotation"', 'taxon:"NCBITaxon:6239"'],  # search query
        "fl": "source,bioentity_internal_id,annotation_class"}  # fields

    golr = GOlrAnnotationIterator.__new__(GOlrAnnotationIterator)
    golr.default_params = request_params
    golr.iter_size = 5
    golr.n_annotations = 5
    records = [i for i in golr]
    assert len(records) == len(records_truth)
    for record, true_record in zip(records, records_truth):
        assert record == true_record


def test_map_taxon_id_connectivity():
    assert map_taxon_id(6239) == (6239, 'Caenorhabditis elegans')
    assert map_taxon_id('canis lupus familiaris') == (9615, 'Canis lupus familiaris')
    with pytest.raises(ValueError):
        map_taxon_id('Lorem ipsum dolor sit amet')


def test_map_taxon_id(monkeypatch):
    taxon_name = 'c elegans'

    def mock_requests_get(url, params):
        assert url == 'https://rest.uniprot.org/taxonomy/search?'
        assert params == {'format': 'tsv', 'query': taxon_name}
        return MockResponse(text='Taxon Id\tMnemonic\tScientific name\tCommon name\tSynonym\tOther Names\tReviewed\t'
                                 'Rank\tLineage\tParent\tVirus hosts\n6239\tCAEEL\tCaenorhabditis elegans\t\t\t'
                                 'Caenorhabditis elegans (Maupas, 1900); Rhabditis elegans; Rhabditis elegans Maupas, '
                                 '1900; roundworm\treviewed\tSpecies\tEukaryota; Metazoa; Ecdysozoa; Nematoda; '
                                 'Chromadorea; Rhabditida; Rhabditina; Rhabditomorpha; Rhabditoidea; Rhabditidae; '
                                 'Peloderinae; Caenorhabditis\t6237\t\n')

    monkeypatch.setattr(requests, 'get', mock_requests_get)
    assert map_taxon_id(taxon_name) == (6239, 'Caenorhabditis elegans')


def test_map_taxon_id_no_results(monkeypatch):
    def mock_requests_get(url, params):
        return MockResponse(text='')

    monkeypatch.setattr(requests, 'get', mock_requests_get)
    map_taxon_id.cache_clear()
    with pytest.raises(ValueError):
        map_taxon_id('')


def test_map_taxon_id_multiple_results(monkeypatch):
    def mock_requests_get(url, params):
        return MockResponse(
            text='Taxon Id\tScientific name\n9615\tCanis lupus familiaris\n2509620\t'
                 'Wlobachia endosymbiont of Canis lupus familiaris\n990119\tCanis lupus x Canis lupus familiaris')

    monkeypatch.setattr(requests, 'get', mock_requests_get)
    assert map_taxon_id('') == (9615, 'Canis lupus familiaris')


def test_map_taxon_id_no_connection(monkeypatch):
    def mock_requests_get(url, params):
        return MockResponse(status_code=100)

    monkeypatch.setattr(requests, 'get', mock_requests_get)
    with pytest.raises(ConnectionError):
        map_taxon_id('name')


def test_ensmbl_lookup_post_request(monkeypatch):
    ids = ('id1', 'id2', 'id3')

    def mock_post_request(self, url, headers, data):
        assert url == 'https://rest.ensembl.org/lookup/id'
        assert headers == {"Content-Type": "application/json", "Accept": "application/json"}
        assert isinstance(data, str)
        assert json.loads(data) == {'ids': list(ids)}

        return AsyncMockResponse(json_output={this_id: {} for this_id in ids})

    monkeypatch.setattr(aiohttp.ClientSession, 'post', mock_post_request)
    assert _ensembl_lookup_post_request(ids) == {'id1': {}, 'id2': {}, 'id3': {}}


@pytest.mark.parametrize("gene_id_info,truth", [
    ({'id1': {'source': 'src1'}, 'id2': {'source': 'src1'}}, {'src1': {'id1', 'id2'}}),
    ({'id1': {'source': 'src1'}, 'id2': {'source': 'src1'}, 'id3': None}, {'src1': {'id1', 'id2'}}),
    ({'id1': {'source': 'src1'}, 'id2': {'source': 'src1'}, 'id3': {'source': 'src2'}},
     {'src1': {'id1', 'id2'}, 'src2': {'id3'}}),
    ({'id1': None, 'id2': None}, {}),
    ({}, {})
])
def test_infer_sources_from_gene_ids(monkeypatch, gene_id_info, truth):
    monkeypatch.setattr(io, '_ensembl_lookup_post_request', lambda x: gene_id_info)
    assert infer_sources_from_gene_ids([]) == truth


@pytest.mark.parametrize("gene_id_info,truth", [
    ({'id1': {'species': 'c_elegans'}, 'id2': {'species': 'c_elegans'}, 'id3': None}, 'c elegans'),
    ({'id1': {'species': 'c_elegans'}, 'id2': {'species': 'm_musculus'}, 'id3': {'species': 'm_musculus'}},
     'm musculus')])
def test_infer_taxon_from_gene_ids(monkeypatch, gene_id_info, truth):
    monkeypatch.setattr(io, 'map_taxon_id', lambda x: x)
    monkeypatch.setattr(io, '_ensembl_lookup_post_request', lambda x: gene_id_info)
    assert infer_taxon_from_gene_ids([])[0] == truth


def test_infer_taxon_from_gene_ids_no_species(monkeypatch):
    gene_id_info = {'id1': None, 'id2': None}
    monkeypatch.setattr(io, '_ensembl_lookup_post_request', lambda x: gene_id_info)
    with pytest.raises(ValueError):
        infer_taxon_from_gene_ids([])


ids_uniprot = ['P34544', 'Q27395', 'P12844']
ids_wormbase = ['WBGene00019883', 'WBGene00023497', 'WBGene00003515']
entrez_to_wb_truth = {'176183': 'WBGene00019883', '173203': 'WBGene00012343'}
wb_to_entrez_truth = {val: key for key, val in zip(entrez_to_wb_truth.keys(), entrez_to_wb_truth.values())}
mapped_ids_truth = {uniprot: wb for uniprot, wb in zip(ids_uniprot, ids_wormbase)}
mapped_ids_truth_rev = {b: a for a, b in zip(mapped_ids_truth.keys(), mapped_ids_truth.values())}


@pytest.mark.parametrize('ids,map_from,map_to,expected_dict',
                         [(ids_uniprot, 'UniProtKB', 'WormBase', mapped_ids_truth),
                          (ids_wormbase, 'WormBase', 'UniProtKB', mapped_ids_truth_rev)])
@pytest.mark.skipif(not UNIPROT_AVAILABLE, reason='UniProt REST API is not available at the moment')
def test_map_gene_ids_connectivity(ids, map_from, map_to, expected_dict):
    mapped_ids = GeneIDTranslator(map_from, map_to).run(ids)
    for geneid in ids:
        assert geneid in mapped_ids
        assert mapped_ids[geneid] == expected_dict[geneid]
    assert mapped_ids.mapping_dict == expected_dict


@pytest.mark.parametrize('id_type', ['UniProtKB', 'Entrez', 'WormBase'])
def test_map_gene_ids_to_same_set(id_type):
    mapper = GeneIDTranslator(id_type, id_type).run(['it', 'doesnt', 'matter', 'what', 'is', 'in', 'here'])
    assert mapper.mapping_dict is None
    for i in ['it', 'not', False, 42, 3.14]:
        assert i in mapper
        assert mapper[i] == i


@pytest.mark.skipif(not UNIPROT_AVAILABLE, reason='UniProt REST API is not available at the moment')
@pytest.mark.parametrize('ids,map_from,map_to,req_from,req_to,req_query,txt,truth',
                         [(['P34544', 'Q27395', 'P12844'], 'UniProtKB', 'WormBase', 'ACC', 'WORMBASE_ID',
                           'P34544 Q27395 P12844',
                           'From\tTo\nP34544\tWBGene00019883\nQ27395\tWBGene00023497\nP12844\tWBGene00003515\n',
                           {'P34544': 'WBGene00019883', 'Q27395': 'WBGene00023497', 'P12844': 'WBGene00003515'}
                           )])
def test_map_gene_ids_request(monkeypatch, ids, map_from, map_to, req_from, req_to, req_query, txt, truth):
    legal_types = get_legal_gene_id_types()

    def mock_get(url, params=None):
        if params is None:
            return
        assert url == 'https://www.uniprot.org/uploadlists/'
        assert params == {'from': req_from,
                          'to': req_to,
                          'format': 'tab',
                          'query': req_query,
                          'columns': 'id'}
        return MockResponse(text=txt)

    monkeypatch.setattr(requests, 'get', mock_get)
    monkeypatch.setattr(io, 'get_legal_gene_id_types', lambda: legal_types)
    res = GeneIDTranslator(map_from, map_to).run(ids)
    for gene_id in truth:
        assert res[gene_id] == truth[gene_id]


@pytest.mark.parametrize('ids,map_from,map_to,txt,rev_txt,truth',
                         [(['WBGene00000003', 'WBGene00000004'], 'WormBase', 'UniProtKB',
                           'From\tEntry\tAnnotation\nWBGene00000003\tQ19151\t110\nWBGene00000004\tA0A0K3AVL7\t57\nWBGene00000004\tO17395\t137.2\n'
                           , '', {'WBGene00000003': 'Q19151', 'WBGene00000004': 'O17395'}),
                          (
                              ['id1', 'id2'], 'UniProtKB', 'WormBase',
                              'From\tTo\nid1\tWBID1\nid2\tWBID2.2\nid2\tWBID2.1\n',
                              'From\tEntry\tAnnotation\nWBID1\tid1\t112.5\nWBID2.1\tid2\t112.5\nWBID2.2\tid2\t235\n'
                              , {'id1': 'WBID1', 'id2': 'WBID2.2'})
                          ])
def test_map_gene_ids_with_duplicates(monkeypatch, ids, map_from, map_to, txt, rev_txt, truth):
    def mock_abbrev_dict():
        d = {'WormBase': 'WormBase',
             'UniProtKB_to': 'UniProtKB',
             'UniProtKB_from': 'UniProtKB_AC-ID',
             'UniProtKB': 'UniProtKB'}
        return d, d

    def mock_get_mapping_results(self, to_db: str, from_db: str, ids: List[str], session):
        mock_abbrev_dict_to, mock_abbrev_dict_from = mock_abbrev_dict()
        if to_db == 'UniProtKB_to':
            return_txt = txt if map_to == 'UniProtKB' else rev_txt
        elif from_db == 'UniProtKB_from':
            return_txt = txt if map_from == 'UniProtKB' else rev_txt
        else:
            raise ValueError(self.map_to, self.map_from)
        return return_txt.split('\n')

    monkeypatch.setattr(io, '_get_id_abbreviation_dicts', mock_abbrev_dict)
    monkeypatch.setattr(GeneIDTranslator, 'get_mapping_results', mock_get_mapping_results)
    res = GeneIDTranslator(map_from, map_to).run(ids)
    for gene_id in truth:
        assert res[gene_id] == truth[gene_id]


def test_get_todays_cache_dir():
    today = date.today()
    today_str = str(today.year) + '_' + str(today.month).zfill(2) + '_' + str(today.day).zfill(2)
    cache_dir_truth = os.path.join(appdirs.user_cache_dir('RNAlysis'), today_str)
    assert cache_dir_truth == str(get_todays_cache_dir())


def test_load_cached_file():
    cached_filename = 'test.txt'
    remove_cached_test_file(cached_filename)

    cache_content_truth = "testing\n123"
    cache_dir = get_todays_cache_dir()
    path = os.path.join(cache_dir, cached_filename)

    assert load_cached_file(cached_filename) is None

    with open(path, 'x') as f:
        f.write(cache_content_truth)

    try:
        assert load_cached_file(cached_filename) == cache_content_truth
    finally:
        remove_cached_test_file(cached_filename)


def test_cache_file():
    cached_filename = 'test.txt'
    remove_cached_test_file(cached_filename)

    cache_content_truth = "testing\n123"
    cache_dir = get_todays_cache_dir()
    path = os.path.join(cache_dir, cached_filename)

    cache_file(cache_content_truth, cached_filename)
    try:
        with open(path, 'r') as f:
            assert f.read() == cache_content_truth
    finally:
        remove_cached_test_file(cached_filename)


@pytest.mark.parametrize("gene_set,expected_split", [
    ({1, 2, 3}, ['1', '2', '3']),
    ({'geneA', 'geneB', 'geneC', 'geneD'}, ["geneA", "geneB", "geneC", "geneD"])
])
def test_save_gene_set(gene_set, expected_split):
    pth = 'tests/test_files/tmp_saved_gene_set.txt'
    try:
        save_gene_set(gene_set, pth)
        with open(pth) as f:
            split = f.read().split('\n')
        assert sorted(split) == sorted(expected_split)
    finally:
        try:
            os.unlink(pth)
        except FileNotFoundError:
            pass


@pytest.mark.parametrize("args", [(6239,), (6239, 'all'), (6239, ['id1', 'id2'])])
def test_kegg_annotation_iterator_api(args):
    _ = KEGGAnnotationIterator(*args)


@pytest.mark.parametrize('arguments,url_truth', [('argument', 'https://rest.kegg.jp/operation/argument'),
                                                 (['arg1', 'arg2', 'arg3'],
                                                  'https://rest.kegg.jp/operation/arg1/arg2/arg3'),
                                                 (['argument'], 'https://rest.kegg.jp/operation/argument')], )
def test_kegg_annotation_iterator_kegg_request(monkeypatch, arguments, url_truth):
    truth = '{"sample": "json", "lorem": "ipsum"}'
    cached = []

    def mock_get_cached_file(filename):
        return None

    def mock_cache_file(content, filename):
        assert filename == 'cached_filename.csv'
        assert content == truth
        cached.append(True)

    def mock_get(self, url):
        assert url == url_truth
        return MockResponse(text=truth)

    monkeypatch.setattr(io, 'load_cached_file', mock_get_cached_file)
    monkeypatch.setattr(requests.Session, 'get', mock_get)
    monkeypatch.setattr(io, 'cache_file', mock_cache_file)
    session = get_session(KEGGAnnotationIterator.RETRIES)
    assert KEGGAnnotationIterator._kegg_request(session, 'operation', arguments, 'cached_filename.csv') == (
        truth, False)
    assert cached == [True]


def test_kegg_annotation_iterator_kegg_request_cached(monkeypatch):
    truth = {"sample": "json", "lorem": "ipsum"}

    def mock_get_cached_file(filename):
        return truth

    monkeypatch.setattr(io, 'load_cached_file', mock_get_cached_file)
    session = get_session(KEGGAnnotationIterator.RETRIES)
    assert KEGGAnnotationIterator._kegg_request(session, 'operation', 'argument', 'cached_filename.csv') == (
        truth, True)


PATHWAY_NAMES_TRUTH = {'cel00010': 'Glycolysis / Gluconeogenesis - Caenorhabditis elegans (nematode)',
                       'cel00020': 'Citrate cycle (TCA cycle) - Caenorhabditis elegans (nematode)',
                       'cel00030': 'Pentose phosphate pathway - Caenorhabditis elegans (nematode)',
                       'cel00040': 'Pentose and glucuronate interconversions - Caenorhabditis elegans (nematode)',
                       'cel00051': 'Fructose and mannose metabolism - Caenorhabditis elegans (nematode)',
                       'cel00052': 'Galactose metabolism - Caenorhabditis elegans (nematode)', }


def test_kegg_annotation_iterator_get_pathways(monkeypatch):
    truth = (PATHWAY_NAMES_TRUTH, 6)
    organism_code = 'cel'

    def mock_kegg_request(self, session, operation, arguments, cached_filename=None):
        assert operation == 'list'
        assert arguments == ['pathway', organism_code]
        assert cached_filename == KEGGAnnotationIterator.PATHWAY_NAMES_CACHED_FILENAME

        with open('tests/test_files/kegg_pathways.txt') as f:
            return f.read(), True

    monkeypatch.setattr(KEGGAnnotationIterator, '_kegg_request', mock_kegg_request)

    kegg = KEGGAnnotationIterator.__new__(KEGGAnnotationIterator)
    kegg.organism_code = organism_code
    kegg.session = get_session(kegg.RETRIES)
    assert kegg.get_pathways() == truth


def test_kegg_annotation_iterator_get_compounds(monkeypatch):
    reqs_made = []
    truth = {'C00001': 'H2O',
             'C00002': 'ATP',
             'C00003': 'NAD+',
             'C00004': 'NADH',
             'C00005': 'NADPH',
             'C00006': 'NADP+',
             'C00007': 'Oxygen',
             'C00008': 'ADP',
             'C00009': 'Orthophosphate',
             'C00010': 'CoA',
             'C00011': 'CO2',
             'C00012': 'Peptide', }

    def mock_kegg_request(session, operation, arguments, cached_filename=None):
        assert operation == 'list'
        assert len(arguments) == 1
        if arguments[0] == 'compound':
            assert cached_filename == KEGGAnnotationIterator.COMPOUND_LIST_CACHED_FILENAME
        else:
            assert cached_filename == KEGGAnnotationIterator.GLYCAN_LIST_CACHED_FILENAME
        reqs_made.append(arguments[0])
        with open('tests/test_files/kegg_compounds.txt') as f:
            return f.read(), True

    monkeypatch.setattr(KEGGAnnotationIterator, '_kegg_request', mock_kegg_request)

    kegg = KEGGAnnotationIterator.__new__(KEGGAnnotationIterator)
    kegg.session = get_session(kegg.RETRIES)
    res = kegg.get_compounds()
    assert res == truth
    assert sorted(reqs_made) == ['compound', 'glycan']


def are_xml_elements_equal(e1, e2):
    if e1.tag != e2.tag: return False
    if e1.text != e2.text: return False
    if e1.tail != e2.tail: return False
    if e1.attrib != e2.attrib: return False
    if len(e1) != len(e2): return False
    return all(are_xml_elements_equal(c1, c2) for c1, c2 in zip(e1, e2))


@pytest.mark.parametrize('pathway_id,expected_fname', [('hsa:00001', 'kgml_hsa:00001.xml')])
def test_kegg_annotation_iterator_get_pathway_kgml(monkeypatch, pathway_id, expected_fname):
    pth = 'tests/test_files/test_kgml.xml'
    with open(pth) as f:
        truth = ElementTree.parse(f)

    def mock_kegg_request(session, operation, arguments, cached_filename=None):
        assert operation == 'get'
        assert arguments == [pathway_id, 'kgml']
        assert cached_filename == expected_fname
        with open(pth) as f:
            return f.read(), True

    monkeypatch.setattr(KEGGAnnotationIterator, '_kegg_request', mock_kegg_request)

    kegg = KEGGAnnotationIterator.__new__(KEGGAnnotationIterator)
    kegg.session = get_session(kegg.RETRIES)
    assert are_xml_elements_equal(kegg.get_pathway_kgml(pathway_id).getroot(), truth.getroot())


def test_kegg_annotation_iterator_get_custom_pathways(monkeypatch):
    truth = {'path:cel00010': None, 'path:cel00030': None, 'path:cel00051': None}

    def mock_kegg_request(self, operation, arguments):
        return 'cel', False

    monkeypatch.setattr(KEGGAnnotationIterator, '_kegg_request', mock_kegg_request)

    kegg = KEGGAnnotationIterator(6239, [i for i in truth.keys()])
    assert kegg.pathway_names == truth


def test_kegg_annotation_iterator_get_pathway_annotations(monkeypatch):
    truth = {'cel00010': ['Glycolysis / Gluconeogenesis - Caenorhabditis elegans (nematode)',
                          {'cel:CELE_F14B4.2', 'cel:CELE_Y87G2A.8', 'cel:CELE_C50F4.2', 'cel:CELE_Y71H10A.1'}],
             'cel00020': ['Citrate cycle (TCA cycle) - Caenorhabditis elegans (nematode)',
                          {'cel:CELE_T20G5.2', 'cel:CELE_B0365.1', 'cel:CELE_D1005.1'}],
             'cel00030': ['Pentose phosphate pathway - Caenorhabditis elegans (nematode)',
                          {'cel:CELE_Y87G2A.8', 'cel:CELE_B0035.5'}],
             'cel00040': ['Pentose and glucuronate interconversions - Caenorhabditis elegans (nematode)',
                          {'cel:CELE_Y105E8B.9', 'cel:CELE_B0310.5', 'cel:CELE_T04H1.7', 'cel:CELE_T04H1.8'}],
             'cel00051': ['Fructose and mannose metabolism - Caenorhabditis elegans (nematode)',
                          {'cel:CELE_C05C8.7', 'cel:CELE_ZK632.4'}],
             'cel00052': ['Galactose metabolism - Caenorhabditis elegans (nematode)', {'cel:CELE_C01B4.6'}]}
    args_truth = ['cel00010+cel00020+cel00030', 'cel00040+cel00051+cel00052']

    def mock_kegg_request(self, session, operation, arguments, fname):
        assert operation == 'get'
        assert arguments == args_truth[0] or arguments == args_truth[1]
        if arguments == args_truth[0]:
            pth = 'tests/test_files/kegg_annotation_1of2.txt'
        else:
            pth = 'tests/test_files/kegg_annotation_2of2.txt'
        with open(pth) as f:
            return f.read(), False

    monkeypatch.setattr(KEGGAnnotationIterator, '_kegg_request', mock_kegg_request)
    monkeypatch.setattr(KEGGAnnotationIterator, 'REQ_MAX_ENTRIES', 3)
    kegg = KEGGAnnotationIterator.__new__(KEGGAnnotationIterator)
    kegg.pathway_annotations = None
    kegg.taxon_id = 6239
    kegg.organism_code = 'cel'
    kegg.session = get_session(kegg.RETRIES)
    kegg.pathway_names = PATHWAY_NAMES_TRUTH
    assert {key: [name, ann] for key, name, ann in kegg.get_pathway_annotations()} == truth


def test_kegg_annotation_iterator_get_pathway_annotations_cached():
    annotation = {'a': 1, 'b': 2, 'c': 3}
    names = {'a': 'namea', 'b': 'nameb', 'c': 'namec'}
    truth = {'a': ['namea', 1], 'b': ['nameb', 2], 'c': ['namec', 3]}
    kegg = KEGGAnnotationIterator.__new__(KEGGAnnotationIterator)
    kegg.pathway_annotations = annotation
    kegg.pathway_names = names
    assert {key: [name, ann] for key, name, ann in kegg.get_pathway_annotations()} == truth


@pytest.mark.parametrize('taxon_id,truth', [
    (6239, 'cel'),
    (270351, 'maqu'),
    (9606, 'hsa'),
    (6238, 'cbr')
])
def test_kegg_annotation_iterator_get_kegg_organism_code(monkeypatch, taxon_id, truth):
    def mock_get_tree(_):
        with open('tests/test_files/kegg_taxon_tree_truth.json') as f:
            return json.loads(f.read())

    monkeypatch.setattr(KEGGAnnotationIterator, '_get_taxon_tree', mock_get_tree)
    session = get_session(KEGGAnnotationIterator.RETRIES)
    assert KEGGAnnotationIterator.get_kegg_organism_code(taxon_id, session) == truth


def test_kegg_annotation_iterator_get_taxon_tree(monkeypatch):
    truth = {"sample": "json", "lorem": "ipsum"}
    truth_text = '{"sample": "json", "lorem": "ipsum"}'
    cached = []

    def mock_get_cached_file(filename):
        return None

    def mock_cache_file(content, filename):
        assert filename == 'kegg_taxon_tree.json'
        assert content == truth_text
        cached.append(True)

    def mock_get(self, url, params):
        assert url == 'https://www.genome.jp/kegg-bin/download_htext?htext=br08610'
        assert params == {'format': 'json'}
        return MockResponse(content=truth_text)

    monkeypatch.setattr(io, 'load_cached_file', mock_get_cached_file)
    monkeypatch.setattr(requests.Session, 'get', mock_get)
    monkeypatch.setattr(io, 'cache_file', mock_cache_file)

    session = get_session(KEGGAnnotationIterator.RETRIES)
    assert KEGGAnnotationIterator._get_taxon_tree(session) == truth
    assert cached == [True]


def test_kegg_annotation_iterator_get_taxon_tree_cached(monkeypatch):
    truth = {"sample": "json", "lorem": "ipsum"}

    def mock_get_cached_file(filename):
        return '{"sample":"json","lorem":"ipsum"}'

    monkeypatch.setattr(io, 'load_cached_file', mock_get_cached_file)
    session = get_session(KEGGAnnotationIterator.RETRIES)
    assert KEGGAnnotationIterator._get_taxon_tree(session) == truth


class MockProcess:
    def __init__(self, returncode: int):
        self.stdout = [b'things', b'to', b'print']
        self.stderr = [b'more', b'things']
        self.returncode = returncode

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return

    def wait(self):
        return


@pytest.mark.parametrize("stdout", [True, False])
@pytest.mark.parametrize("stderr", [True, False])
def test_run_subprocess(stdout, stderr):
    run_subprocess(['python3', '--version'], stdout, stderr)


@pytest.mark.parametrize('this_version,response,expected', [
    ('3.0.0', MockResponse(status_code=503), False),
    ('3.0.0', MockResponse(text='{"info":{"author":"Guy Teichman","version":"3.1.0"}}'), True),
    ('3.1.1', MockResponse(text='{"info":{"author":"Guy Teichman","version":"3.1.0"}}'), False),
    ('3.1.1', MockResponse(text='{"info":{"author":"Guy Teichman","version":"3.1.1"}}'), False),
])
def test_is_rnalysis_outdated(monkeypatch, this_version, response, expected):
    monkeypatch.setattr(requests, 'get', lambda *args, **kwargs: response)
    monkeypatch.setattr(io, '__version__', this_version)
    assert is_rnalysis_outdated() == expected


@pytest.mark.parametrize('path,expected', [
    ('tests/test_files/test_fastqs/outdir/paired_1_trimmed_truth.fastq.gz', 95),
    ('tests/test_files/test_fastqs/outdir/test_fastq_trimmed_truth.fastq.gz', 7396)
])
def test_get_gunzip_size(path, expected):
    res = get_gunzip_size(path)
    assert res == expected


@pytest.mark.parametrize('item, filename', [
    (pl.DataFrame({'A': [1, 2], 'B': [3, 4]}), 'test1.csv'),
    ({'gene1', 'gene2', 'gene3'}, 'test2.txt'),
    ('this is a test', 'test3.txt'),
    (plt.figure(), 'test4.png')
])
def test_cache_gui_file(item, filename):
    try:
        cache_gui_file(item, filename)
        # Check if the file is created
        assert Path(get_gui_cache_dir(), filename).exists()
    finally:
        # Clean up after the test
        if Path(get_gui_cache_dir(), filename).exists():
            Path(get_gui_cache_dir(), filename).unlink()


@pytest.mark.parametrize("item, filename, load_as_obj, expected_output", [
    (pl.DataFrame({"": ['h', 'i', 'j'], "a": [1, 2, 3], "b": [4, 5, 6]}), "test.csv", True,
     pl.DataFrame({"": ['h', 'i', 'j'], "a": [1, 2, 3], "b": [4, 5, 6]})),
    ({"apple", "banana", "cherry"}, "test.txt", True, {"apple", "banana", "cherry"}),
    ("test", "test.txt", True, {"test"}),
    ("test123", "test.txt", False, b"test123"),
    (pl.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]}), "test.csv", False, b"a,b\n1,4\n2,5\n3,6\n"),
    ({"apple", "banana", "cherry"}, "test.txt", False,
     bytes("\n".join({"apple", "banana", "cherry"}), encoding='utf-8')),
    ("test", "test.txt", False, b"test")
])
def test_load_cached_gui_file(item, filename, load_as_obj, expected_output):
    directory = get_gui_cache_dir()
    if not directory.exists():
        directory.mkdir(parents=True)
    path = directory.joinpath(filename)

    try:
        cache_gui_file(item, filename)
        res = load_cached_gui_file(filename, load_as_obj)
        if isinstance(res, pl.DataFrame):
            assert res.equals(item)
        elif isinstance(res, bytes):
            assert res.replace(b'\r', b'') == expected_output
        else:
            assert res == expected_output
    finally:
        if os.path.exists(path):
            os.remove(path)


def test_get_next_link():
    headers = {"Link": '<https://www.rest.uniprot.org/next-batch>; rel="next"'}
    result = GeneIDTranslator.get_next_link(headers)
    assert result == "https://www.rest.uniprot.org/next-batch"


def test_combine_batches_json():
    all_results = {"results": [], "failedIds": []}
    batch_results = {"results": [{"accession": "P29307", "identifier": "7157"}], "failedIds": []}
    file_format = "json"
    assert GeneIDTranslator.combine_batches(all_results, batch_results, file_format) == {
        "results": [{"accession": "P29307", "identifier": "7157"}], "failedIds": []}


def test_combine_batches_tsv():
    all_results = ["accession\tannotation_score", "P12345\t1.0"]
    batch_results = ["accession\tannotation_score", "Q67890\t0.8", "P12355\t1.0"]
    file_format = "tsv"
    combined_results = GeneIDTranslator.combine_batches(all_results, batch_results, file_format)
    assert combined_results == ["accession\tannotation_score", "P12345\t1.0", "Q67890\t0.8", "P12355\t1.0"]


def test_combine_batches_other():
    all_results = "some text"
    batch_results = "more text"
    file_format = "unknown"
    combined_results = GeneIDTranslator.combine_batches(all_results, batch_results, file_format)
    assert combined_results == "some textmore text"


def test_decode_results_json():
    response_mock = MagicMock(spec=requests.Response)
    response_mock.text = '{"id": 1, "name": "John"}'
    response_mock.json.return_value = {'id': 1, 'name': 'John'}

    result = GeneIDTranslator.decode_results(response_mock, 'json')
    assert result == {'id': 1, 'name': 'John'}


def test_decode_results_tsv():
    response_mock = MagicMock(spec=requests.Response)
    response_mock.text = "id\tname\n1\tJohn\n2\tJane\n"

    result = GeneIDTranslator.decode_results(response_mock, 'tsv')
    assert result == ['id\tname', '1\tJohn', '2\tJane']


def test_decode_results_with_invalid_file_format():
    response_mock = MagicMock(spec=requests.Response)
    response_mock.text = 'Invalid format'

    result = GeneIDTranslator.decode_results(response_mock, 'csv')
    assert result == 'Invalid format'


def test_check_id_mapping_results_ready_with_results():
    with requests_mock.Mocker() as m:
        # Mock the response from the server
        m.get("https://rest.uniprot.org/idmapping/status/123", json={"results": ['content']})
        # Call the function
        session = requests.Session()
        ready = GeneIDTranslator.check_id_mapping_results_ready(session, "123", 0.1)
        # Check the result
        assert ready


def test_check_id_mapping_results_ready_with_failed_ids():
    with requests_mock.Mocker() as m:
        # Mock the response from the server
        m.get("https://rest.uniprot.org/idmapping/status/123", json={"failedIds": ['content']})
        # Call the function
        session = requests.Session()
        ready = GeneIDTranslator.check_id_mapping_results_ready(session, "123", 0.1)
        # Check the result
        assert ready


def test_check_id_mapping_results_ready_running():
    with requests_mock.Mocker() as m:
        # Mock the response from the server
        count = 0

        def request_callback(request, context):
            nonlocal count
            count += 1
            if count < 5:
                return {"jobStatus": "RUNNING"}
            else:
                return {"results": ['data'], "status_code": 200}

        m.get("https://rest.uniprot.org/idmapping/status/123", json=request_callback)

        # Call the function
        session = requests.Session()
        ready = GeneIDTranslator.check_id_mapping_results_ready(session, "123", 0.1)
        # Check the result
        assert ready
        assert count == 5


def test_check_id_mapping_results_ready_error():
    with requests_mock.Mocker() as m:
        # Mock the response from the server
        m.get("https://rest.uniprot.org/idmapping/status/123", json={"jobStatus": "ERROR"})

        # Call the function
        session = requests.Session()

        # Check that an exception is raised
        with pytest.raises(Exception):
            GeneIDTranslator.check_id_mapping_results_ready(session, "https://rest.uniprot.org", "123", 0.1)


# Test cases for the OrthologDict class
class TestOrthologDict:

    # Test the initialization of OrthologDict
    def test_init(self):
        ortholog_dict = OrthologDict()
        assert len(ortholog_dict) == 0  # Check that it's empty when initialized without mapping_dict

        mapping_dict = {'gene1': 'ortho1', 'gene2': 'ortho2'}
        ortholog_dict = OrthologDict(mapping_dict)
        assert len(ortholog_dict) == len(mapping_dict)  # Check that it contains the correct number of items
        assert 'gene1' in ortholog_dict  # Check that a key is present in the mapping

    # Test getting an item from OrthologDict
    def test_getitem(self):
        mapping_dict = {'gene1': 'ortho1', 'gene2': 'ortho2'}
        ortholog_dict = OrthologDict(mapping_dict)
        assert ortholog_dict['gene1'] == 'ortho1'  # Check that we can get an item

        with pytest.raises(KeyError):
            _ = ortholog_dict['gene3']  # Check that getting a non-existent item raises a KeyError

    # Test checking for item existence in OrthologDict
    def test_contains(self):
        mapping_dict = {'gene1': 'ortho1', 'gene2': 'ortho2'}
        ortholog_dict = OrthologDict(mapping_dict)
        assert 'gene1' in ortholog_dict  # Check that an existing key is in the OrthologDict
        assert 'gene3' not in ortholog_dict  # Check that a non-existent key is not in the OrthologDict


@pytest.mark.parametrize(
    "translated_ids, mapping_one2one, mapping_one2many, expected_one2one, expected_one2many",
    [
        # Both mappings are empty
        (['trans1', 'trans2'], {}, {}, {}, {}),

        # One-to-one mapping contains keys, one-to-many mapping is empty
        (
            ['trans1', 'trans2'], {'trans1': 'ortho1', 'trans2': 'ortho2'}, {}, {'gene1': 'ortho1', 'gene2': 'ortho2'},
            {}),

        # One-to-many mapping contains keys, one-to-one mapping is empty
        (['trans1', 'trans2'], {}, {'trans1': ['ortho1', 'ortho3'], 'trans2': ['ortho2']}, {},
         {'gene1': ['ortho1', 'ortho3'], 'gene2': ['ortho2']}),

        # Both mappings contain the same keys
        (['trans1', 'trans2'], {'trans1': 'ortho1', 'trans2': 'ortho2'},
         {'trans1': ['ortho1', 'ortho3'], 'trans2': ['ortho2']},
         {'gene1': 'ortho1', 'gene2': 'ortho2'}, {'gene1': ['ortho1', 'ortho3'], 'gene2': ['ortho2']}),

        # One-to-one mapping has extra keys
        (['trans1', 'trans2'], {'trans1': 'ortho1', 'trans2': 'ortho2', 'trans3': 'ortho3'},
         {'trans1': ['ortho1', 'ortho3'], 'trans2': ['ortho2']},
         {'gene1': 'ortho1', 'gene2': 'ortho2'}, {'gene1': ['ortho1', 'ortho3'], 'gene2': ['ortho2']}),

        # One-to-many mapping has extra keys
        (['trans1', 'trans2'], {'trans1': 'ortho1', 'trans2': 'ortho2'},
         {'trans1': ['ortho1', 'ortho3'], 'trans2': ['ortho2'], 'trans3': ['ortho4']},
         {'gene1': 'ortho1', 'gene2': 'ortho2'}, {'gene1': ['ortho1', 'ortho3'], 'gene2': ['ortho2']}),

        # Both mappings have extra keys
        (['trans1', 'trans2'], {'trans1': 'ortho1', 'trans2': 'ortho2', 'trans3': 'ortho3'},
         {'trans1': ['ortho1', 'ortho3'], 'trans2': ['ortho2'], 'trans4': ['ortho4']},
         {'gene1': 'ortho1', 'gene2': 'ortho2'}, {'gene1': ['ortho1', 'ortho3'], 'gene2': ['ortho2']}),

        # Both mappings are empty, translated_ids contain unmapped IDs
        (['trans1', 'trans3'], {}, {}, {}, {}),

        # One-to-one mapping contains keys, translated_ids contain unmapped IDs
        (['trans1', 'trans3'], {'trans1': 'ortho1', 'trans2': 'ortho2'}, {}, {'gene1': 'ortho1'}, {}),

        # One-to-many mapping contains keys, translated_ids contain unmapped IDs
        (['trans1', 'trans3'], {}, {'trans1': ['ortho1', 'ortho3'], 'trans2': ['ortho2']}, {},
         {'gene1': ['ortho1', 'ortho3']}),

        # Both mappings contain the same keys, translated_ids contain unmapped IDs
        (['trans1', 'trans3'], {'trans1': 'ortho1', 'trans2': 'ortho2'},
         {'trans1': ['ortho1', 'ortho3'], 'trans2': ['ortho2']},
         {'gene1': 'ortho1'}, {'gene1': ['ortho1', 'ortho3']}),
    ]
)
def test_translate_mappings(translated_ids, mapping_one2one, mapping_one2many, expected_one2one, expected_one2many):
    ids = ['gene1', 'gene2']
    result_one2one, result_one2many = translate_mappings(ids, translated_ids, mapping_one2one, mapping_one2many)
    assert result_one2one == expected_one2one
    assert result_one2many == expected_one2many


class TestOrthologDict:
    def test_empty_dict(self):
        ortholog_dict = OrthologDict()
        assert len(ortholog_dict) == 0
        assert 'gene1' not in ortholog_dict
        with pytest.raises(KeyError):
            ortholog_dict['gene1']

    def test_non_empty_dict(self):
        mapping_dict = {'gene1': 'ortholog1', 'gene2': 'ortholog2'}
        ortholog_dict = OrthologDict(mapping_dict)
        assert len(ortholog_dict) == 2
        assert 'gene1' in ortholog_dict
        assert ortholog_dict['gene1'] == 'ortholog1'
        assert 'gene2' in ortholog_dict
        assert ortholog_dict['gene2'] == 'ortholog2'

    def test_non_existing_key(self):
        ortholog_dict = OrthologDict({'gene1': 'ortholog1'})
        assert 'gene2' not in ortholog_dict
        with pytest.raises(KeyError):
            ortholog_dict['gene2']

    def test_none_mapping_dict(self):
        ortholog_dict = OrthologDict(None)
        assert len(ortholog_dict) == 0
        assert 'gene1' not in ortholog_dict
        with pytest.raises(KeyError):
            ortholog_dict['gene1']


@pytest.mark.skipif(not PHYLOMEDB_AVAILABLE,
                    reason="No internet connection or FTP server is down. Skipping PhylomeDBOrthologMapper tests.")
class TestPhylomeDBOrthologMapper:

    # Define a fixture to create an instance of PhylomeDBOrthologMapper for testing
    @pytest.fixture
    def ortholog_mapper(self):
        # Supply legal species
        legal_species = PhylomeDBOrthologMapper.get_legal_species()
        map_to_organism = legal_species[0, 0]  # Use the first legal species
        map_from_organism = legal_species[1, 0]  # Use the second legal species
        return PhylomeDBOrthologMapper(map_to_organism=map_to_organism, map_from_organism=map_from_organism,
                                       gene_id_type='gene_type')

    @staticmethod
    def mock_translate_ids(self, ids):
        return ['gene1', 'gene2'], ['trans_gene1', 'trans_gene2']

    # Test the constructor of PhylomeDBOrthologMapper
    def test_constructor(self, ortholog_mapper):
        assert ortholog_mapper.map_to_organism in PhylomeDBOrthologMapper.get_legal_species()['taxid']
        assert ortholog_mapper.map_from_organism in PhylomeDBOrthologMapper.get_legal_species()['taxid']
        assert ortholog_mapper.gene_id_type == 'gene_type'

    # Test the _connect method
    def test_connect(self):
        ftp = PhylomeDBOrthologMapper._connect()
        ftp.quit()

    # Test the translate_ids method
    def test_translate_ids(self, ortholog_mapper, monkeypatch):
        ids = ('gene1', 'gene2')

        # Monkeypatch GeneIDTranslator to return the same translation
        class MockGeneIDTranslator:
            def __init__(self, gene_id_type, target_gene_id_type):
                assert gene_id_type == 'gene_type'
                assert target_gene_id_type == 'UniProtKB AC/ID'

            def run(self, ids):
                assert ids == ('gene1', 'gene2')
                return GeneIDDict({'gene1': 'trans_gene1', 'gene2': 'trans_gene2'})

        monkeypatch.setattr(io, 'GeneIDTranslator', MockGeneIDTranslator)

        translated_ids = ortholog_mapper.translate_ids(ids)
        assert isinstance(translated_ids, tuple)
        assert isinstance(translated_ids[0], list)
        assert isinstance(translated_ids[1], list)
        assert translated_ids == (['gene1', 'gene2'], ['trans_gene1', 'trans_gene2'])

    # Test the _get_taxon_map method
    @pytest.mark.parametrize('taxon_ind', [0, -1])
    def test_get_taxon_file(self, ortholog_mapper, taxon_ind):
        legal_species = PhylomeDBOrthologMapper.get_legal_species()
        taxon_id = legal_species[taxon_ind, 0]
        target_id = legal_species[taxon_ind + 1, 0]
        taxon_map = ortholog_mapper._get_taxon_map(taxon_id, target_id)
        cached_df = ortholog_mapper._get_taxon_map(taxon_id, target_id)
        assert taxon_map == cached_df

        assert isinstance(taxon_map, dict) and len(taxon_map) > 0
        sample = taxon_map.popitem()
        assert isinstance(sample, tuple)
        assert isinstance(sample[0], str)
        assert isinstance(sample[1], tuple)
        assert isinstance(sample[1][0], str)
        assert isinstance(sample[1][1], float)


    # Test the get_legal_species method
    def test_get_legal_species(self, ortholog_mapper):
        species = ortholog_mapper.get_legal_species()
        assert species[species.columns[0]].dtype == pl.UInt32
        assert 6239 in species[species.columns[0]]

        species_cached = ortholog_mapper.get_legal_species()
        assert species.equals(species_cached)

    # Test the _get_id_conversion_maps method
    def test_get_id_conversion_map(self, ortholog_mapper):
        map_fwd, map_rev = ortholog_mapper._get_id_conversion_maps()
        assert isinstance(map_fwd, dict) and isinstance(map_rev, dict)
        assert len(map_fwd) == len(map_rev)

        map_fwd_cache, map_rev_cache = ortholog_mapper._get_id_conversion_maps()
        assert len(map_fwd_cache) == len(map_rev_cache)
        assert len(map_fwd) == len(map_fwd_cache)

    @pytest.mark.parametrize('filter_consistency_score,non_unique_mode', [
        (False, 'first'),
        (True, 'last'),
        (True, 'random')
    ])
    def test_get_orthologs(self, filter_consistency_score, non_unique_mode):
        ortholog_mapper = PhylomeDBOrthologMapper(map_to_organism=9606, map_from_organism=6239,
                                                  gene_id_type='UniProtKB AC/ID')
        ids = ('G5EDF7', 'P34544')
        consistency_score_threshold = 0.5
        ortholog_one2one, ortholog_one2many = ortholog_mapper.get_orthologs(
            ids, non_unique_mode, consistency_score_threshold, filter_consistency_score)

        assert isinstance(ortholog_one2one, OrthologDict)
        assert isinstance(ortholog_one2many, OrthologDict)

        assert list(ortholog_one2one.mapping_dict.keys()) == ['G5EDF7', 'P34544']
        assert list(ortholog_one2many.mapping_dict.keys()) == ['G5EDF7', 'P34544']

        if non_unique_mode == 'first':
            assert ortholog_one2one['G5EDF7'] == 'P52564'
            assert ortholog_one2one['P34544'] == 'Q15047'


class TestOrthoInspectorOrthologMapper:

    # Define a fixture to create an instance of OrthoInspectorOrthologMapper for testing
    @pytest.fixture
    def ortholog_mapper(self):
        # Supply legal species and a valid database for testing
        return OrthoInspectorOrthologMapper(map_to_organism='organism1', map_from_organism='organism2',
                                            gene_id_type='gene_type')

    # Test the constructor of OrthoInspectorOrthologMapper
    def test_constructor(self, ortholog_mapper):
        assert ortholog_mapper.map_to_organism == 'organism1'
        assert ortholog_mapper.map_from_organism == 'organism2'
        assert ortholog_mapper.gene_id_type == 'gene_type'

    # Test the translate_ids method
    def test_translate_ids(self, ortholog_mapper, monkeypatch):
        ids = ('gene1', 'gene2')

        # Monkeypatch GeneIDTranslator to return the same translation
        class MockGeneIDTranslator:
            def __init__(self, gene_id_type, target_gene_id_type, session=None):
                assert gene_id_type == 'gene_type'
                assert target_gene_id_type == 'UniProtKB AC/ID'
                assert session is None or isinstance(session, requests.Session)

            def run(self, run_ids):
                assert run_ids == ('gene1', 'gene2')
                return GeneIDDict({'gene1': 'trans_gene1', 'gene2': 'trans_gene2'})

        monkeypatch.setattr(io, 'GeneIDTranslator', MockGeneIDTranslator)

        translated_ids = ortholog_mapper.translate_ids(ids)
        assert isinstance(translated_ids, tuple)
        assert isinstance(translated_ids[0], list)
        assert isinstance(translated_ids[1], list)
        assert translated_ids == (['gene1', 'gene2'], ['trans_gene1', 'trans_gene2'])

    # Test the get_cache_filename method
    def test_get_cache_filename(self, ortholog_mapper):
        filename = ortholog_mapper.get_cache_filename()
        assert isinstance(filename, str)
        assert filename == 'orthoinspector_organism2_organism1.json'

    # Test the get_databases method
    def test_get_databases(self, ortholog_mapper):
        databases = ortholog_mapper.get_databases()
        assert isinstance(databases, frozenset)
        assert len(databases) >= 4  # the current number of OrthoInspector databases

    # Test the get_database_organisms method
    def test_get_database_organisms(self, ortholog_mapper):
        db_organisms = ortholog_mapper.get_database_organisms()
        assert isinstance(db_organisms, dict)
        assert len(db_organisms) >= 11  # the current number of OrthoInspector databases
        assert abs(len(list(db_organisms.values())) - len(
            set(db_organisms.values()))) <= 2  # check that all databases are unique, with 2 allowed exceptions due to the newly-added databases

    @pytest.mark.parametrize('database,non_unique_mode', [
        ('auto', 'first'),
        ('Eukaryota2016', 'last'),
        ('Eukaryota2016', 'random')])
    def test_get_orthologs(self, database, non_unique_mode):
        mapper = OrthoInspectorOrthologMapper(map_to_organism=6238, map_from_organism=6239,
                                              gene_id_type='UniProtKB AC/ID')
        ids = ('G5EDF7', 'P34544')
        ortholog_one2one, ortholog_one2many = mapper.get_orthologs(ids, non_unique_mode, database)

        assert isinstance(ortholog_one2one, OrthologDict)
        assert isinstance(ortholog_one2many, OrthologDict)

        assert list(ortholog_one2one.mapping_dict.keys()) == ['G5EDF7', 'P34544']
        assert list(ortholog_one2many.mapping_dict.keys()) == ['G5EDF7', 'P34544']

        if non_unique_mode == 'first':
            assert ortholog_one2one.mapping_dict == {'G5EDF7': 'A8XPU4', 'P34544': 'A8XT55'}


class TestPantherOrthologMapper:

    # Define a fixture to create an instance of PantherOrthologMapper for testing
    @pytest.fixture
    def ortholog_mapper(self):
        # Supply valid parameters for the class constructor
        return PantherOrthologMapper(map_to_organism='organism1', map_from_organism='organism2',
                                     gene_id_type='gene_type')

    # Test the constructor of PantherOrthologMapper
    def test_constructor(self, ortholog_mapper):
        assert ortholog_mapper.map_to_organism == 'organism1'
        assert ortholog_mapper.map_from_organism == 'organism2'
        assert ortholog_mapper.gene_id_type == 'gene_type'

    # Test the translate_ids method
    def test_translate_ids(self, ortholog_mapper, monkeypatch):
        ids = ('gene1', 'gene2')

        # Monkeypatch GeneIDTranslator to return the same translation
        class MockGeneIDTranslator:
            def __init__(self, gene_id_type, target_gene_id_type, session=None):
                assert gene_id_type == 'gene_type'
                assert target_gene_id_type == 'UniProtKB AC/ID'
                assert session is None or isinstance(session, requests.Session)

            def run(self, ids):
                assert ids == ('gene1', 'gene2')
                return GeneIDDict({'gene1': 'trans_gene1', 'gene2': 'trans_gene2'})

        monkeypatch.setattr(io, 'GeneIDTranslator', MockGeneIDTranslator)

        translated_ids = ortholog_mapper.translate_ids(ids)
        assert isinstance(translated_ids, tuple)
        assert isinstance(translated_ids[0], list)
        assert isinstance(translated_ids[1], list)
        assert translated_ids == (['gene1', 'gene2'], ['trans_gene1', 'trans_gene2'])

    @pytest.mark.parametrize('filter_least_diverged,non_unique_mode', [
        (True, 'first'),
        (False, 'last'),
        (True, 'random')])
    def test_get_orthologs(self, filter_least_diverged, non_unique_mode):
        ids = ('G5EDF7', 'P34544')
        ortholog_mapper = PantherOrthologMapper(map_to_organism=9606, map_from_organism=6239,
                                                gene_id_type='UniProtKB AC/ID')
        filter_least_diverged = True

        ortholog_one2one, ortholog_one2many = ortholog_mapper.get_orthologs(ids, non_unique_mode, filter_least_diverged)

        assert isinstance(ortholog_one2one, OrthologDict)
        assert isinstance(ortholog_one2many, OrthologDict)

        assert list(ortholog_one2one.mapping_dict.keys()) == ['G5EDF7', 'P34544']
        assert list(ortholog_one2many.mapping_dict.keys()) == ['G5EDF7', 'P34544']

        if non_unique_mode == 'first':
            assert ortholog_one2one['G5EDF7'] == 'P52564'
            assert ortholog_one2one['P34544'] == 'Q15047'

    def test_get_paralogs(self):
        ids = ('G5EDF7', 'P34707')

        truth = {'G5EDF7': ['Q10664',
                            'O01706',
                            'Q20347',
                            'Q21307',
                            'G5EDT6',
                            'Q58AU7',
                            'Q58AU8',
                            'Q8MPS3',
                            'G5ECN5',
                            'Q9TYV7'],
                 'P34707': ['A0A0M7REQ4']}
        ortholog_mapper = PantherOrthologMapper(map_to_organism=6239, map_from_organism=6239,
                                                gene_id_type='UniProtKB AC/ID')

        paralogs = ortholog_mapper.get_paralogs(ids)

        assert isinstance(paralogs, OrthologDict)
        assert len(paralogs.mapping_dict) == len(truth)
        for key in truth:
            assert key in paralogs.mapping_dict
            assert sorted(paralogs.mapping_dict[key]) == sorted(truth[key])


class TestEnsemblOrthologMapper:

    # Define a fixture to create an instance of EnsemblOrthologMapper for testing
    @pytest.fixture
    def ortholog_mapper(self):
        # Supply valid parameters for the class constructor
        return EnsemblOrthologMapper(map_to_organism='organism1', map_from_organism='organism2',
                                     gene_id_type='gene_type')

    # Test the constructor of EnsemblOrthologMapper
    def test_constructor(self, ortholog_mapper):
        assert ortholog_mapper.map_to_organism == 'organism1'  # Replace with a valid organism
        assert ortholog_mapper.map_from_organism == 'organism2'  # Replace with a valid organism
        assert ortholog_mapper.gene_id_type == 'gene_type'  # Replace with a valid gene ID type

    # Test the translate_ids method
    def test_translate_ids(self, ortholog_mapper, monkeypatch):
        ids = ('gene1', 'gene2')

        # Monkeypatch GeneIDTranslator to return the same translation
        class MockGeneIDTranslator:
            def __init__(self, gene_id_type, target_gene_id_type, session=None):
                assert gene_id_type == 'gene_type'
                assert target_gene_id_type == 'Ensembl Genomes'
                assert session is None or isinstance(session, requests.Session)

            def run(self, ids):
                assert ids == ('gene1', 'gene2')
                return GeneIDDict({'gene1': 'trans_gene1', 'gene2': 'trans_gene2'})

        monkeypatch.setattr(io, 'GeneIDTranslator', MockGeneIDTranslator)

        translated_ids = ortholog_mapper.translate_ids(ids)
        assert isinstance(translated_ids, tuple)
        assert isinstance(translated_ids[0], list)
        assert isinstance(translated_ids[1], list)
        assert translated_ids == (['gene1', 'gene2'], ['trans_gene1', 'trans_gene2'])

    @pytest.mark.skipif(not ENSEMBL_AVAILABLE, reason='Ensembl API is not available at the moment')
    @pytest.mark.parametrize('filter_percent_identity,truth', [
        (True, {'G5EDF7': 'WBGene00003368', 'P34707': 'WBGene00020961'}),
        (False, {'G5EDF7': ['WBGene00018034',
                            'WBGene00018035',
                            'WBGene00003185',
                            'WBGene00003186',
                            'WBGene00012162',
                            'WBGene00003368',
                            'WBGene00003472'],
                 'P34707': ['WBGene00020961']})])
    def test_get_paralogs(self, filter_percent_identity, truth):
        ids = ('G5EDF7', 'P34707')
        ortholog_mapper = EnsemblOrthologMapper(map_to_organism=6239, map_from_organism=6239,
                                                gene_id_type='UniProtKB AC/ID')

        paralogs = ortholog_mapper.get_paralogs(ids, filter_percent_identity)

        assert isinstance(paralogs, OrthologDict)
        for key in truth:
            assert key in paralogs.mapping_dict
            assert sorted(paralogs.mapping_dict[key]) == sorted(truth[key])

    @pytest.mark.skipif(not ENSEMBL_AVAILABLE, reason='Ensembl API is not available at the moment')
    @pytest.mark.parametrize('non_unique_mode', ['first', 'last', 'random'])
    def test_get_orthologs(self, non_unique_mode):
        ids = ('G5EDF7', 'P34544')

        ortholog_mapper = EnsemblOrthologMapper(map_to_organism=9606, map_from_organism=6239,
                                                gene_id_type='UniProtKB AC/ID')

        ortholog_one2one, ortholog_one2many = ortholog_mapper.get_orthologs(ids, non_unique_mode)

        assert isinstance(ortholog_one2one, OrthologDict)
        assert isinstance(ortholog_one2many, OrthologDict)

        assert list(ortholog_one2one.mapping_dict.keys()) == ['G5EDF7', 'P34544']
        assert list(ortholog_one2many.mapping_dict.keys()) == ['G5EDF7', 'P34544']

        if non_unique_mode == 'first':
            assert ortholog_one2one['G5EDF7'] == 'ENSG00000085511'
            assert ortholog_one2one['P34544'] == 'ENSG00000165671'


class TestRunRScript:
    @mock.patch('rnalysis.utils.io.run_subprocess')
    def test_non_zero_return_code(self, mock_run_subprocess):
        # Set up the mock to return a non-zero return code
        def conditional_return(*args, **kwargs):
            if args[0][1] == "--help":
                return 0, ''
            else:
                return 1, ["warning1", "warning2", "Error: Something went wrong", "traceback"]

        # Set the side_effect to the conditional function
        mock_run_subprocess.side_effect = conditional_return

        # Define the script path and R installation folder
        script_path = "tests/test_files/test_r_script.R"
        r_installation_folder = "auto"

        # Execute the function with the mock in place
        with pytest.raises(ChildProcessError) as context:
            run_r_script(script_path, r_installation_folder)

        # Check if the expected error message is in the exception message
        expected_error_message = "R script failed to execute: 'Error: Something went wrongtraceback'. See full error report below."
        assert expected_error_message in str(context.value)

    @pytest.mark.parametrize('r_path,expected', [
        ('auto', ['Rscript', "tests/test_files/test_r_script.R"]),
        ('D:/Program Files/R', ["D:/Program Files/R/bin/Rscript", "tests/test_files/test_r_script.R"])
    ])
    def test_run_r_script(self, monkeypatch, r_path, expected):
        script_path = 'tests/test_files/test_r_script.R'

        ran = []

        def mock_popen(process, stdout, stderr, shell=False):
            if ran:
                assert process == expected
                ran.append(2)
            else:
                assert process == [expected[0], '--help']
                ran.append(1)
            return MockProcess(0)

        monkeypatch.setattr(subprocess, 'Popen', mock_popen)

        run_r_script(script_path, r_path)
        assert ran == [1, 2]

    def test_run_r_script_not_installed(self, monkeypatch):
        def mock_popen(process, stdout, stderr, shell=False):
            return MockProcess(1)

        monkeypatch.setattr(subprocess, 'Popen', mock_popen)
        with pytest.raises(FileNotFoundError):
            run_r_script('tests/test_files/test_r_script.R')
