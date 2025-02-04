import logging
import re
from unittest.mock import Mock, patch

import matplotlib
import polars.selectors as cs
import pytest

import rnalysis.gui.gui_report

matplotlib.use('Agg')
from rnalysis.gui.gui import *

LEFT_CLICK = QtCore.Qt.MouseButton.LeftButton
RIGHT_CLICK = QtCore.Qt.MouseButton.RightButton


def _pytestqt_graceful_shutdown():
    app = QtWidgets.QApplication.instance()
    if app is not None:
        for w in app.topLevelWidgets():
            try:
                w.close()
            except RuntimeError:
                continue


@pytest.fixture(autouse=True)
def mainwindow_setup(monkeypatch):
    monkeypatch.setattr(QtWidgets.QMessageBox, 'question', lambda *args, **kwargs: QtWidgets.QMessageBox.StandardButton.Yes)
    monkeypatch.setattr(gui_widgets.ThreadStdOutStreamTextQueueReceiver, 'run', lambda self: None)
    monkeypatch.setattr(gui_quickstart.QuickStartWizard, '__init__', lambda *args, **kwargs: None)


@pytest.fixture
def blank_icon():
    pixmap = QtGui.QPixmap(32, 32)
    pixmap.fill(QtCore.Qt.GlobalColor.transparent)
    return QtGui.QIcon(pixmap)


@pytest.fixture
def red_icon():
    pixmap = QtGui.QPixmap(32, 32)
    pixmap.fill(QtCore.Qt.GlobalColor.red)
    return QtGui.QIcon(pixmap)


@pytest.fixture
def green_icon():
    pixmap = QtGui.QPixmap(32, 32)
    pixmap.fill(QtCore.Qt.GlobalColor.green)
    return QtGui.QIcon(pixmap)


@pytest.fixture
def use_temp_settings_file():
    settings.make_temp_copy_of_settings_file()
    yield
    settings.set_temp_copy_of_settings_file_as_default()
    settings.remove_temp_copy_of_settings_file()


@pytest.fixture
def available_objects_no_tabpages(blank_icon, red_icon, green_icon):
    return {'first tab': (None, blank_icon), 'second tab': (None, red_icon), 'third tab': (None, green_icon),
            'fourth tab': (None, red_icon)}


@pytest.fixture
def available_objects(qtbot, red_icon, green_icon):
    qtbot, first = widget_setup(qtbot, SetTabPage, 'first tab',
                                {'WBGene00000002', 'WBGene00000006', 'WBGene00000015', 'WBGene00000017'})

    qtbot, second = widget_setup(qtbot, FilterTabPage, undo_stack=QtGui.QUndoStack())
    second.start_from_filter_obj(filtering.DESeqFilter('tests/test_files/test_deseq.csv'), 1)
    second.rename('second tab')

    qtbot, third = widget_setup(qtbot, FilterTabPage, undo_stack=QtGui.QUndoStack())
    third.start_from_filter_obj(filtering.CountFilter('tests/test_files/counted.tsv'), 2)
    third.rename('third tab')

    yield {'first tab': (first, red_icon), 'second tab': (second, red_icon), 'third tab': (third, green_icon)}
    _pytestqt_graceful_shutdown()


@pytest.fixture
def four_available_objects_and_empty(qtbot, red_icon, green_icon, blank_icon):
    qtbot, first = widget_setup(qtbot, SetTabPage, 'first tab',
                                {'WBGene00008447', 'WBGene00044258', 'WBGene00045410', 'WBGene00010100'})

    qtbot, second = widget_setup(qtbot, FilterTabPage, undo_stack=QtGui.QUndoStack())
    second.start_from_filter_obj(filtering.DESeqFilter('tests/test_files/test_deseq_set_ops_1.csv'), 2)
    second.rename('second tab')

    qtbot, third = widget_setup(qtbot, FilterTabPage, undo_stack=QtGui.QUndoStack())
    third.start_from_filter_obj(filtering.DESeqFilter('tests/test_files/test_deseq_set_ops_2.csv'), 3)
    third.rename('third tab')

    qtbot, fourth = widget_setup(qtbot, FilterTabPage, undo_stack=QtGui.QUndoStack())
    fourth.start_from_filter_obj(filtering.CountFilter('tests/test_files/counted.tsv'), 4)
    fourth.rename('fourth tab')

    qtbot, empty = widget_setup(qtbot, FilterTabPage, undo_stack=QtGui.QUndoStack())

    yield {'first tab': (first, red_icon), 'second tab': (second, red_icon), 'third tab': (third, red_icon),
           'fourth tab': (fourth, green_icon), 'empty tab': (empty, blank_icon)}
    _pytestqt_graceful_shutdown()


@pytest.fixture
def main_window(qtbot, monkeypatch, use_temp_settings_file):
    settings.set_show_tutorial_settings(False)
    qtbot, window = widget_setup(qtbot, MainWindow, gather_stdout=True)
    # warnings.showwarning = customwarn
    # sys.excepthook = window.excepthook
    builtins.input = window.input
    window._toggle_reporting(True)
    yield window
    window.close()
    _pytestqt_graceful_shutdown()


@pytest.fixture
def main_window_with_tabs(main_window, monkeypatch):
    monkeypatch.setattr(QtWidgets.QFileDialog, 'getOpenFileName',
                        lambda *args, **kwargs: ('tests/test_files/test_session.rnal', '.rnal'))
    monkeypatch.setattr(QtWidgets.QApplication, 'processEvents', lambda *args, **kwargs: None)
    main_window.load_session_action.trigger()
    return main_window


@pytest.fixture
def tab_widget(qtbot):
    qtbot, window = widget_setup(qtbot, ReactiveTabWidget)
    yield window
    window.close()
    _pytestqt_graceful_shutdown()


@pytest.fixture
def multi_keep_window(qtbot):
    objs = [filtering.DESeqFilter('tests/test_files/test_deseq.csv'),
            filtering.CountFilter('tests/test_files/counted.tsv'),
            filtering.Filter('tests/test_files/test_deseq_biotype.csv')]
    qtbot, window = widget_setup(qtbot, MultiKeepWindow, objs, -1)
    yield window
    window.close()
    _pytestqt_graceful_shutdown()


@pytest.fixture
def filtertabpage(qtbot):
    qtbot, window = widget_setup(qtbot, FilterTabPage)
    window.start_from_filter_obj(filtering.DESeqFilter('tests/test_files/test_deseq.csv'), 1)
    yield window
    window.close()
    _pytestqt_graceful_shutdown()


@pytest.fixture
def filtertabpage_with_undo_stack(qtbot):
    stack = QtGui.QUndoStack()
    qtbot, window = widget_setup(qtbot, FilterTabPage, undo_stack=stack)
    window.start_from_filter_obj(filtering.DESeqFilter('tests/test_files/test_deseq_sig.csv'), 1)
    yield window, stack
    _pytestqt_graceful_shutdown()


@pytest.fixture
def countfiltertabpage_with_undo_stack(qtbot):
    stack = QtGui.QUndoStack()
    qtbot, window = widget_setup(qtbot, FilterTabPage, undo_stack=stack)
    window.start_from_filter_obj(filtering.CountFilter('tests/test_files/counted.csv'), 1)
    yield window, stack
    _pytestqt_graceful_shutdown()


@pytest.fixture
def settabpage_with_undo_stack(qtbot):
    stack = QtGui.QUndoStack()
    qtbot, window = widget_setup(qtbot, SetTabPage, 'my set name', {'a', 'b', 'c', 'd'}, undo_stack=stack)
    yield window, stack
    _pytestqt_graceful_shutdown()


@pytest.fixture
def pipeline():
    pipeline = filtering.Pipeline('DESeqFilter')
    pipeline.add_function(filtering.DESeqFilter.describe)
    pipeline.add_function(filtering.DESeqFilter.filter_significant, 0.2)
    pipeline.add_function(filtering.DESeqFilter.filter_top_n, 'padj', n=1)
    return pipeline


@pytest.fixture
def clicom_window(qtbot):
    funcs = {'split_kmeans': 'K-Means', 'split_kmedoids': 'K-Medoids',
             'split_hierarchical': 'Hierarchical (Agglomerative)', 'split_hdbscan': 'HDBSCAN'}
    qtbot, window = widget_setup(qtbot, ClicomWindow, funcs, filtering.CountFilter('tests/test_files/counted.csv'))
    yield window
    window.close()
    _pytestqt_graceful_shutdown()


@pytest.fixture
def simple_deseq_window(qtbot) -> SimpleDESeqWindow:
    qtbot, window = widget_setup(qtbot, SimpleDESeqWindow)
    yield window
    window.close()
    _pytestqt_graceful_shutdown()


@pytest.fixture
def simple_limma_window(qtbot) -> SimpleLimmaWindow:
    qtbot, window = widget_setup(qtbot, SimpleLimmaWindow)
    yield window
    window.close()
    _pytestqt_graceful_shutdown()


@pytest.fixture
def deseq_window(qtbot) -> DESeqWindow:
    qtbot, window = widget_setup(qtbot, DESeqWindow)
    yield window
    window.close()
    _pytestqt_graceful_shutdown()


@pytest.fixture
def limma_window(qtbot) -> LimmaWindow:
    qtbot, window = widget_setup(qtbot, LimmaWindow)
    yield window
    window.close()
    _pytestqt_graceful_shutdown()


@pytest.fixture
def cutadapt_single_window(qtbot) -> CutAdaptSingleWindow:
    qtbot, window = widget_setup(qtbot, CutAdaptSingleWindow)
    yield window
    window.close()
    _pytestqt_graceful_shutdown()


@pytest.fixture
def cutadapt_paired_window(qtbot) -> CutAdaptPairedWindow:
    qtbot, window = widget_setup(qtbot, CutAdaptPairedWindow)
    yield window

    window.close()
    _pytestqt_graceful_shutdown()


@pytest.fixture
def kallisto_index_window(qtbot) -> KallistoIndexWindow:
    qtbot, window = widget_setup(qtbot, KallistoIndexWindow)
    yield window
    window.close()
    _pytestqt_graceful_shutdown()


@pytest.fixture
def kallisto_single_window(qtbot) -> KallistoSingleWindow:
    qtbot, window = widget_setup(qtbot, KallistoSingleWindow)
    yield window
    window.close()
    _pytestqt_graceful_shutdown()


@pytest.fixture
def kallisto_paired_window(qtbot) -> KallistoPairedWindow:
    qtbot, window = widget_setup(qtbot, KallistoPairedWindow)
    yield window
    window.close()
    _pytestqt_graceful_shutdown()


def update_gene_sets_widget(widget: gui_widgets.GeneSetComboBox, objs):
    widget.update_gene_sets(objs)


@pytest.fixture
def enrichment_window(qtbot, available_objects):
    qtbot, window = widget_setup(qtbot, EnrichmentWindow)
    window.geneSetsRequested.connect(functools.partial(update_gene_sets_widget, objs=available_objects))
    window.widgets['parallel_backend'] = 'multiprocessing'

    yield window
    _pytestqt_graceful_shutdown()


@pytest.fixture
def set_op_window(qtbot, four_available_objects_and_empty):
    qtbot, window = widget_setup(qtbot, SetOperationWindow, four_available_objects_and_empty)
    yield window
    _pytestqt_graceful_shutdown()


@pytest.fixture
def set_vis_window(qtbot, four_available_objects_and_empty):
    qtbot, window = widget_setup(qtbot, SetVisualizationWindow, four_available_objects_and_empty)
    yield window
    _pytestqt_graceful_shutdown()


multi_open_window_files = ['tests/counted.csv', 'tests/test_deseq.csv', 'tests/counted.tsv']


@pytest.fixture
def multi_open_window(qtbot):
    qtbot, window = widget_setup(qtbot, MultiOpenWindow, multi_open_window_files)
    yield window
    _pytestqt_graceful_shutdown()


@pytest.fixture
def apply_table_pipeline_window(qtbot, available_objects_no_tabpages):
    qtbot, window = widget_setup(qtbot, gui_windows.ApplyTablePipelineWindow, available_objects_no_tabpages)
    yield window
    _pytestqt_graceful_shutdown()


@pytest.fixture
def monkeypatch_create_canvas(monkeypatch):
    canvas_created = []

    def mock_create_canvas(self):
        canvas_created.append(True)

    monkeypatch.setattr(SetVisualizationWindow, 'create_canvas', mock_create_canvas)
    return canvas_created


def widget_setup(qtbot, widget_class, *args, **kwargs):
    widget = widget_class(*args, **kwargs)
    widget.show()
    qtbot.add_widget(widget)
    return qtbot, widget


def test_ApplyPipelineWindow_init(apply_table_pipeline_window):
    pass


def test_ApplyPipelineWindow_select_all(qtbot, apply_table_pipeline_window, available_objects_no_tabpages):
    qtbot.mouseClick(apply_table_pipeline_window.list.select_all_button, LEFT_CLICK)
    assert apply_table_pipeline_window.result() == list(available_objects_no_tabpages.keys())


def test_ApplyPipelineWindow_clear_all(qtbot, apply_table_pipeline_window):
    qtbot.mouseClick(apply_table_pipeline_window.list.select_all_button, LEFT_CLICK)
    qtbot.mouseClick(apply_table_pipeline_window.list.clear_all_button, LEFT_CLICK)
    assert apply_table_pipeline_window.result() == []


def test_KallistoIndexWindow_init(kallisto_index_window):
    _ = kallisto_index_window


def test_KallistoSingleWindow_init(kallisto_single_window):
    _ = kallisto_single_window


def test_KallistoPairedWindow_init(kallisto_paired_window):
    _ = kallisto_paired_window


def test_KallistoIndexWindow_start_analysis(qtbot, kallisto_index_window):
    truth_args = []
    fa_file = 'path/to/fa/file'
    truth_kwargs = dict(transcriptome_fasta=fa_file,
                        kallisto_installation_folder='auto',
                        kmer_length=31,
                        make_unique=False)

    kallisto_index_window.param_widgets['transcriptome_fasta'].setText(fa_file)

    with qtbot.waitSignal(kallisto_index_window.paramsAccepted) as blocker:
        qtbot.mouseClick(kallisto_index_window.start_button, LEFT_CLICK)
    assert blocker.args[0] == truth_args
    assert blocker.args[1] == truth_kwargs


def test_KallistoSingleWindow_start_analysis(qtbot, kallisto_single_window):
    truth_args = []
    fq_folder = 'path/to/fq/folder'
    out_folder = 'path/to/out/dir'
    index_file = 'path/to/index/file.idx'
    gtf_file = 'path/to/gtf.gtf'
    average_fragment_length = 175
    stdev_fragment_length = 25.5
    truth_kwargs = dict(fastq_folder=fq_folder, output_folder=out_folder,
                        gtf_file=gtf_file,
                        index_file=index_file,
                        average_fragment_length=average_fragment_length,
                        stdev_fragment_length=stdev_fragment_length,
                        kallisto_installation_folder='auto',
                        new_sample_names='auto',
                        stranded='no',
                        bootstrap_samples=None,
                        summation_method='scaled_tpm')

    kallisto_single_window.param_widgets['fastq_folder'].setText(fq_folder)
    kallisto_single_window.param_widgets['output_folder'].setText(out_folder)
    kallisto_single_window.param_widgets['index_file'].setText(index_file)
    kallisto_single_window.param_widgets['gtf_file'].setText(gtf_file)
    kallisto_single_window.param_widgets['average_fragment_length'].setValue(average_fragment_length)
    kallisto_single_window.param_widgets['stdev_fragment_length'].setValue(stdev_fragment_length)

    with qtbot.waitSignal(kallisto_single_window.paramsAccepted) as blocker:
        qtbot.mouseClick(kallisto_single_window.start_button, LEFT_CLICK)
    assert blocker.args[0] == truth_args
    assert blocker.args[1] == truth_kwargs


def test_KallistoPairedWindow_start_analysis(qtbot, kallisto_paired_window):
    r1_files = ['file1.fq', 'path/file2.fq']
    r2_files = ['file3.fq.gz', 'path/to/file4.fastq.gz']
    out_folder = 'path/to/out/dir'
    index_file = 'path/to/index/file.idx'
    gtf_file = 'path/to/gtf.gtf'
    truth_args = []
    truth_kwargs = dict(r1_files=r1_files, r2_files=r2_files,
                        output_folder=out_folder,
                        gtf_file=gtf_file,
                        index_file=index_file,
                        kallisto_installation_folder='auto',
                        new_sample_names='smart',
                        stranded='no',
                        bootstrap_samples=None,
                        summation_method='scaled_tpm')

    kallisto_paired_window.pairs_widgets['r1_files'].add_items(r1_files)
    kallisto_paired_window.pairs_widgets['r2_files'].add_items(r2_files)
    kallisto_paired_window.param_widgets['output_folder'].setText(out_folder)
    kallisto_paired_window.param_widgets['index_file'].setText(index_file)
    kallisto_paired_window.param_widgets['gtf_file'].setText(gtf_file)

    with qtbot.waitSignal(kallisto_paired_window.paramsAccepted) as blocker:
        qtbot.mouseClick(kallisto_paired_window.start_button, LEFT_CLICK)
    assert blocker.args[0] == truth_args
    assert blocker.args[1] == truth_kwargs


def test_CutAdaptSingleWindow_init(cutadapt_single_window):
    _ = cutadapt_single_window


def test_CutAdaptPairedWindow_init(cutadapt_paired_window):
    _ = cutadapt_paired_window


def test_CutAdaptSingleWindow_start_analysis(qtbot, cutadapt_single_window):
    truth_args = []
    fq_folder = 'path/to/fq/folder'
    out_folder = 'path/to/out/dir'
    adapter = 'ATGGA'
    truth_kwargs = dict(fastq_folder=fq_folder, output_folder=out_folder,
                        three_prime_adapters=adapter,
                        five_prime_adapters=None,
                        any_position_adapters=None,
                        quality_trimming=20, trim_n=True,
                        minimum_read_length=10, maximum_read_length=None,
                        discard_untrimmed_reads=True, error_tolerance=0.1,
                        minimum_overlap=3, allow_indels=True, parallel=True, gzip_output=False, new_sample_names='auto')

    cutadapt_single_window.param_widgets['fastq_folder'].setText(fq_folder)
    cutadapt_single_window.param_widgets['output_folder'].setText(out_folder)
    cutadapt_single_window.param_widgets['three_prime_adapters'].setValue(adapter)

    with qtbot.waitSignal(cutadapt_single_window.paramsAccepted) as blocker:
        qtbot.mouseClick(cutadapt_single_window.start_button, LEFT_CLICK)
    assert blocker.args[0] == truth_args
    assert blocker.args[1] == truth_kwargs


def test_CutAdaptPairedWindow_start_analysis(qtbot, cutadapt_paired_window):
    r1_files = ['file1.fq', 'path/file2.fq']
    r2_files = ['file3.fq.gz', 'path/to/file4.fastq.gz']
    out_folder = 'path/to/out/dir'
    adapter1 = 'ATGGA'
    adapter2 = 'CATC'
    truth_args = []
    truth_kwargs = dict(r1_files=r1_files, r2_files=r2_files,
                        output_folder=out_folder,
                        three_prime_adapters_r1=adapter1, three_prime_adapters_r2=adapter2,
                        five_prime_adapters_r1=None, five_prime_adapters_r2=None,
                        any_position_adapters_r1=None, any_position_adapters_r2=None,
                        quality_trimming=20, trim_n=True, minimum_read_length=10, maximum_read_length=None,
                        discard_untrimmed_reads=True, pair_filter_if='both', new_sample_names='auto',
                        error_tolerance=0.1, minimum_overlap=3, allow_indels=True, parallel=True, gzip_output=False)
    cutadapt_paired_window.pairs_widgets['r1_files'].add_items(r1_files)
    cutadapt_paired_window.pairs_widgets['r2_files'].add_items(r2_files)
    cutadapt_paired_window.param_widgets['output_folder'].setText(out_folder)
    cutadapt_paired_window.param_widgets['three_prime_adapters_r1'].setValue(adapter1)
    cutadapt_paired_window.param_widgets['three_prime_adapters_r2'].setValue(adapter2)

    with qtbot.waitSignal(cutadapt_paired_window.paramsAccepted) as blocker:
        qtbot.mouseClick(cutadapt_paired_window.start_button, LEFT_CLICK)
    assert blocker.args[0] == truth_args
    assert blocker.args[1] == truth_kwargs


def test_SimpleDESeqWindow_init(simple_deseq_window):
    _ = simple_deseq_window


def test_SimpleDESeqWindow_load_design_mat(qtbot, simple_deseq_window):
    design_mat_path = 'tests/test_files/test_design_matrix.csv'
    design_mat_truth = io.load_table(design_mat_path, 0)
    simple_deseq_window.param_widgets['design_matrix'].setText(design_mat_path)
    qtbot.mouseClick(simple_deseq_window.param_widgets['load_design'], LEFT_CLICK)
    assert simple_deseq_window.design_mat.equals(design_mat_truth)
    assert simple_deseq_window.comparisons_widgets['picker'].design_mat.equals(design_mat_truth)


def test_SimpleDESeqWindow_get_analysis_params(qtbot, simple_deseq_window):
    design_mat_path = 'tests/test_files/test_design_matrix.csv'
    truth = dict(r_installation_folder='auto', design_matrix=design_mat_path, output_folder=None,
                 comparisons=[('replicate', 'rep3', 'rep2'), ('condition', 'cond1', 'cond2')], return_code=True,
                 return_design_matrix=True, return_log=True)

    simple_deseq_window.param_widgets['design_matrix'].setText(design_mat_path)
    qtbot.mouseClick(simple_deseq_window.param_widgets['load_design'], LEFT_CLICK)

    simple_deseq_window.comparisons_widgets['picker'].add_comparison_widget()

    simple_deseq_window.comparisons_widgets['picker'].inputs[0].factor.setCurrentText('replicate')
    simple_deseq_window.comparisons_widgets['picker'].inputs[0].numerator.setCurrentText('rep3')
    simple_deseq_window.comparisons_widgets['picker'].inputs[0].denominator.setCurrentText('rep2')

    assert simple_deseq_window.get_analysis_kwargs() == truth


def test_SimpleDESeqWindow_start_analysis(qtbot, simple_deseq_window):
    design_mat_path = 'tests/test_files/test_design_matrix.csv'

    truth_args = []
    truth_kwargs = dict(r_installation_folder='auto', design_matrix=design_mat_path, output_folder=None,
                        comparisons=[('replicate', 'rep3', 'rep2'), ('condition', 'cond1', 'cond2')], return_code=True,
                        return_design_matrix=True, return_log=True)

    simple_deseq_window.param_widgets['design_matrix'].setText(design_mat_path)
    qtbot.mouseClick(simple_deseq_window.param_widgets['load_design'], LEFT_CLICK)

    simple_deseq_window.comparisons_widgets['picker'].add_comparison_widget()

    simple_deseq_window.comparisons_widgets['picker'].inputs[0].factor.setCurrentText('replicate')
    simple_deseq_window.comparisons_widgets['picker'].inputs[0].numerator.setCurrentText('rep3')
    simple_deseq_window.comparisons_widgets['picker'].inputs[0].denominator.setCurrentText('rep2')

    with qtbot.waitSignal(simple_deseq_window.paramsAccepted) as blocker:
        qtbot.mouseClick(simple_deseq_window.start_button, LEFT_CLICK)
    assert blocker.args[0] == truth_args
    assert blocker.args[1] == truth_kwargs


def test_SimpleLimmaWindow_init(simple_limma_window):
    _ = simple_limma_window


def test_SimpleLimmaWindow_load_design_mat(qtbot, simple_limma_window):
    design_mat_path = 'tests/test_files/test_design_matrix.csv'
    design_mat_truth = io.load_table(design_mat_path, 0)
    simple_limma_window.param_widgets['design_matrix'].setText(design_mat_path)
    qtbot.mouseClick(simple_limma_window.param_widgets['load_design'], LEFT_CLICK)
    assert simple_limma_window.design_mat.equals(design_mat_truth)
    assert simple_limma_window.comparisons_widgets['picker'].design_mat.equals(design_mat_truth)


def test_SimpleLimmaWindow_get_analysis_params(qtbot, simple_limma_window):
    design_mat_path = 'tests/test_files/test_design_matrix.csv'
    truth = dict(r_installation_folder='auto', design_matrix=design_mat_path, output_folder=None,
                 comparisons=[('replicate', 'rep3', 'rep2'), ('condition', 'cond1', 'cond2')], random_effect=None,
                 quality_weights=False, return_code=True, return_design_matrix=True, return_log=True)

    simple_limma_window.param_widgets['design_matrix'].setText(design_mat_path)
    qtbot.mouseClick(simple_limma_window.param_widgets['load_design'], LEFT_CLICK)

    simple_limma_window.comparisons_widgets['picker'].add_comparison_widget()

    simple_limma_window.comparisons_widgets['picker'].inputs[0].factor.setCurrentText('replicate')
    simple_limma_window.comparisons_widgets['picker'].inputs[0].numerator.setCurrentText('rep3')
    simple_limma_window.comparisons_widgets['picker'].inputs[0].denominator.setCurrentText('rep2')

    assert simple_limma_window.get_analysis_kwargs() == truth


def test_SimpleLimmaWindow_start_analysis(qtbot, simple_limma_window):
    design_mat_path = 'tests/test_files/test_design_matrix.csv'

    truth_args = []
    truth_kwargs = dict(r_installation_folder='auto', design_matrix=design_mat_path, output_folder=None,
                        comparisons=[('replicate', 'rep3', 'rep2'), ('condition', 'cond1', 'cond2')],
                        random_effect=None, quality_weights=False, return_code=True,
                        return_design_matrix=True, return_log=True)

    simple_limma_window.param_widgets['design_matrix'].setText(design_mat_path)
    qtbot.mouseClick(simple_limma_window.param_widgets['load_design'], LEFT_CLICK)

    simple_limma_window.comparisons_widgets['picker'].add_comparison_widget()

    simple_limma_window.comparisons_widgets['picker'].inputs[0].factor.setCurrentText('replicate')
    simple_limma_window.comparisons_widgets['picker'].inputs[0].numerator.setCurrentText('rep3')
    simple_limma_window.comparisons_widgets['picker'].inputs[0].denominator.setCurrentText('rep2')

    with qtbot.waitSignal(simple_limma_window.paramsAccepted) as blocker:
        qtbot.mouseClick(simple_limma_window.start_button, LEFT_CLICK)
    assert blocker.args[0] == truth_args
    assert blocker.args[1] == truth_kwargs


def test_ClicomWindow_init(clicom_window):
    _ = clicom_window


def test_ClicomWindow_add_setup(qtbot, clicom_window):
    truth = dict(method='kmeans', n_clusters=3, n_init=3, max_iter=300, random_seed=None,
                 max_n_clusters_estimate='auto')

    qtbot.keyClicks(clicom_window.stack.func_combo, filtering.CountFilter.split_kmeans.readable_name)
    clicom_window.stack.parameter_widgets['n_clusters'].other.setValue(3)
    qtbot.mouseClick(clicom_window.setups_widgets['add_button'], LEFT_CLICK)
    assert len(clicom_window.parameter_dicts) == 1
    assert clicom_window.parameter_dicts[0] == truth


def test_ClicomWindow_remove_setup(qtbot, monkeypatch, clicom_window):
    monkeypatch.setattr(QtWidgets.QMessageBox, 'question', lambda *args: QtWidgets.QMessageBox.StandardButton.Yes)
    qtbot.keyClicks(clicom_window.stack.func_combo, filtering.CountFilter.split_kmeans.readable_name)
    clicom_window.stack.parameter_widgets['n_clusters'].other.setValue(3)
    qtbot.mouseClick(clicom_window.setups_widgets['add_button'], LEFT_CLICK)
    assert len(clicom_window.parameter_dicts) == 1

    qtbot.mouseClick(clicom_window.setups_widgets['list'].delete_all_button, LEFT_CLICK)

    assert len(clicom_window.parameter_dicts) == 0


def test_ClicomWindow_get_analysis_params(qtbot, clicom_window):
    truth = dict(replicate_grouping='ungrouped', power_transform=[True, False], evidence_threshold=0.35,
                 cluster_unclustered_features=True, parallel_backend='loky',
                 min_cluster_size=15, plot_style='all', split_plots=False)

    qtbot.mouseClick(clicom_window.param_widgets['power_transform'].false_button, LEFT_CLICK)
    qtbot.mouseClick(clicom_window.param_widgets['cluster_unclustered_features'].switch, LEFT_CLICK)
    clicom_window.param_widgets['evidence_threshold'].clear()
    qtbot.keyClicks(clicom_window.param_widgets['evidence_threshold'], '0.35')

    assert clicom_window.get_analysis_kwargs() == truth


def test_ClicomWindow_start_analysis(qtbot, clicom_window):
    truth_setups = [dict(method='kmeans', n_clusters=3, n_init=3, max_iter=300, random_seed=None,
                         max_n_clusters_estimate='auto'),
                    dict(method='hierarchical', n_clusters='silhouette', metric='Euclidean', linkage='Average',
                         distance_threshold=None, max_n_clusters_estimate='auto')]
    truth_params = dict(replicate_grouping='ungrouped', power_transform=[True, False], evidence_threshold=0.35,
                        cluster_unclustered_features=True, min_cluster_size=15, plot_style='all', split_plots=False,
                        parallel_backend='loky')

    clicom_window.stack.func_combo.setCurrentText(filtering.CountFilter.split_kmeans.readable_name)
    clicom_window.stack.parameter_widgets['n_clusters'].other.setValue(3)
    qtbot.mouseClick(clicom_window.setups_widgets['add_button'], LEFT_CLICK)

    clicom_window.stack.func_combo.setCurrentText(filtering.CountFilter.split_hierarchical.readable_name)
    qtbot.keyClicks(clicom_window.stack.parameter_widgets['n_clusters'].combo, 'silhouette')
    qtbot.mouseClick(clicom_window.setups_widgets['add_button'], LEFT_CLICK)

    qtbot.mouseClick(clicom_window.param_widgets['power_transform'].false_button, LEFT_CLICK)
    qtbot.mouseClick(clicom_window.param_widgets['cluster_unclustered_features'].switch, LEFT_CLICK)
    clicom_window.param_widgets['evidence_threshold'].clear()
    qtbot.keyClicks(clicom_window.param_widgets['evidence_threshold'], '0.35')

    with qtbot.waitSignal(clicom_window.paramsAccepted) as blocker:
        clicom_window.start_button.click()
    assert blocker.args[0] == truth_setups
    assert blocker.args[1] == truth_params


def test_EnrichmentWindow_init(enrichment_window):
    _ = enrichment_window


@pytest.mark.parametrize('button_name,truth', [
    ('Gene Ontology (GO)', 'go'),
    ('Kyoto Encyclopedia of Genes and Genomes (KEGG)', 'kegg'),
    ('Categorical attributes', 'user_defined'),
    ('Non-categorical attributes', 'non_categorical')
])
def test_EnrichmentWindow_get_analysis_type(enrichment_window, button_name, truth):
    enrichment_window.widgets['dataset_radiobox'].radio_buttons[button_name].click()
    assert enrichment_window.get_current_analysis_type() == truth


@pytest.mark.parametrize('button_name', [
    'Gene Ontology (GO)',
    'Kyoto Encyclopedia of Genes and Genomes (KEGG)',
    'Categorical attributes',
])
@pytest.mark.parametrize('test_name,truth', [
    ("Fisher's Exact test", False),
    ('Hypergeometric test', False),
    ('Randomization test', False),
    ('Single-set enrichment (XL-mHG test)', True)
])
def test_EnrichmentWindow_is_single_set(enrichment_window, button_name, test_name, truth):
    enrichment_window.widgets['dataset_radiobox'].radio_buttons[button_name].click()
    enrichment_window.stats_widgets['stats_radiobox'].radio_buttons[test_name].click()

    assert enrichment_window.is_single_set() == truth


@pytest.mark.parametrize('test_name,truth', [
    ("One-sample T-test (parametric)", False),
    ('Sign test (non-parametric)', False)])
def test_EnrichmentWindow_is_single_set_non_categorical(enrichment_window, test_name, truth):
    enrichment_window.widgets['dataset_radiobox'].radio_buttons['Non-categorical attributes'].click()
    enrichment_window.stats_widgets['stats_radiobox'].radio_buttons[test_name].click()

    assert enrichment_window.is_single_set() == truth


@pytest.mark.parametrize('button_name,test_name,func_truth', [
    ('Gene Ontology (GO)', "Fisher's Exact test", enrichment.FeatureSet.go_enrichment),
    ('Gene Ontology (GO)', 'Hypergeometric test', enrichment.FeatureSet.go_enrichment),
    ('Gene Ontology (GO)', 'Randomization test', enrichment.FeatureSet.go_enrichment),
    ('Gene Ontology (GO)', 'Single-set enrichment (XL-mHG test)', enrichment.RankedSet.single_set_go_enrichment),
    ('Kyoto Encyclopedia of Genes and Genomes (KEGG)', "Fisher's Exact test", enrichment.FeatureSet.kegg_enrichment),
    ('Kyoto Encyclopedia of Genes and Genomes (KEGG)', 'Hypergeometric test', enrichment.FeatureSet.kegg_enrichment),
    ('Kyoto Encyclopedia of Genes and Genomes (KEGG)', 'Randomization test', enrichment.FeatureSet.kegg_enrichment),
    ('Kyoto Encyclopedia of Genes and Genomes (KEGG)', 'Single-set enrichment (XL-mHG test)',
     enrichment.RankedSet.single_set_kegg_enrichment),
    ('Categorical attributes', "Fisher's Exact test", enrichment.FeatureSet.user_defined_enrichment),
    ('Categorical attributes', 'Hypergeometric test', enrichment.FeatureSet.user_defined_enrichment),
    ('Categorical attributes', 'Randomization test', enrichment.FeatureSet.user_defined_enrichment),
    ('Categorical attributes', 'Single-set enrichment (XL-mHG test)', enrichment.RankedSet.single_set_enrichment),
    ('Non-categorical attributes', "One-sample T-test (parametric)", enrichment.FeatureSet.non_categorical_enrichment),
    ('Non-categorical attributes', "Sign test (non-parametric)", enrichment.FeatureSet.non_categorical_enrichment)
])
def test_EnrichmentWindow_get_func(enrichment_window, button_name, test_name, func_truth):
    enrichment_window.widgets['dataset_radiobox'].radio_buttons[button_name].click()
    enrichment_window.stats_widgets['stats_radiobox'].radio_buttons[test_name].click()

    assert enrichment_window.get_current_func() == func_truth


@pytest.mark.parametrize('button_name,truth', [
    ('Gene Ontology (GO)', True),
    ('Kyoto Encyclopedia of Genes and Genomes (KEGG)', True),
    ('Categorical attributes', True),
    ('Non-categorical attributes', False)
])
def test_EnrichmentWindow_is_categorical(enrichment_window, button_name, truth):
    enrichment_window.widgets['dataset_radiobox'].radio_buttons[button_name].click()
    assert enrichment_window.is_categorical() == truth


@pytest.mark.parametrize('en_set,bg_set,en_set_truth,bg_set_truth,', [
    ('first tab', 'second tab', 'first tab', 'second tab'),
    ('third tab', 'first tab', 'third tab', 'first tab'),
    ('second tab', 'third tab', 'second tab', 'third tab'),
])
@pytest.mark.parametrize('button_name,dataset_kwargs', [
    ('Gene Ontology (GO)',
     dict(plot_horizontal=True, plot_ontology_graph=False, organism='auto', excluded_evidence_types='experimental')),
    ('Kyoto Encyclopedia of Genes and Genomes (KEGG)',
     dict(plot_horizontal=True, gene_id_type='auto')),
    ('Categorical attributes', dict(attributes='all', plot_horizontal=False))
])
@pytest.mark.parametrize('test_name,is_single_set,test_arg_truth,stats_kwargs', [
    ("Fisher's Exact test", False, 'fisher', dict(alpha=0.05)),
    ('Hypergeometric test', False, 'hypergeometric', dict(alpha=0.5)),
    ('Randomization test', False, 'randomization', dict(alpha=0.13, random_seed=42)),
    ('Single-set enrichment (XL-mHG test)', True, 'single_set', dict(alpha=0.01))
])
def test_EnrichmentWindow_get_analysis_params(qtbot, enrichment_window, button_name, test_name, test_arg_truth, en_set,
                                              en_set_truth, bg_set, bg_set_truth, is_single_set, available_objects,
                                              stats_kwargs, dataset_kwargs):
    kwargs_truth = dict()
    kwargs_truth.update(stats_kwargs)
    kwargs_truth.update(dataset_kwargs)

    set_name_truth = available_objects[en_set_truth][0].name
    enrichment_window.widgets['dataset_radiobox'].radio_buttons[button_name].click()
    enrichment_window.stats_widgets['stats_radiobox'].radio_buttons[test_name].click()

    enrichment_window.widgets['enrichment_list'].showPopup()
    qtbot.keyClicks(enrichment_window.widgets['enrichment_list'], en_set)

    enrichment_window.stats_widgets['alpha'].clear()
    qtbot.keyClicks(enrichment_window.stats_widgets['alpha'], str(kwargs_truth['alpha']))

    for key in stats_kwargs:
        if key not in {'alpha'}:
            enrichment_window.stats_widgets[key].setValue(stats_kwargs[key])

    for key in dataset_kwargs:
        if key in enrichment_window.parameter_widgets:
            qtbot.keyClicks(enrichment_window.parameter_widgets[key].combo, dataset_kwargs[key])
        elif key in enrichment_window.plot_widgets:
            if not dataset_kwargs[key]:
                enrichment_window.plot_widgets[key].switch.click()

    if not is_single_set:
        enrichment_window.widgets['bg_list'].showPopup()
        qtbot.keyClicks(enrichment_window.widgets['bg_list'], bg_set)

    gene_set, bg_set, gene_set_name, kwargs, pred_ids = enrichment_window.get_analysis_params()

    assert gene_set == available_objects[en_set_truth][0].obj()
    if is_single_set:
        assert bg_set is None
        assert 'statistical_test' not in kwargs
    else:
        assert bg_set == available_objects[bg_set_truth][0].obj()
        assert kwargs['statistical_test'] == test_arg_truth

    for key in kwargs_truth:
        assert kwargs[key] == kwargs_truth[key]

    assert gene_set_name == set_name_truth


@pytest.mark.parametrize('en_set,bg_set,en_set_truth,bg_set_truth,', [
    ('first tab', 'second tab', 'first tab', 'second tab'),
    ('third tab', 'first tab', 'third tab', 'first tab'),
    ('second tab', 'third tab', 'second tab', 'third tab'),
])
@pytest.mark.parametrize('button_name,dataset_kwargs', [
    ('Non-categorical attributes', dict(plot_log_scale=False, attributes='all')),
])
@pytest.mark.parametrize('test_name,test_arg_truth,stats_kwargs', [
    ("One-sample T-test (parametric)", True, dict(alpha=0.08)),
    ('Sign test (non-parametric)', False, dict(alpha=0.5))
])
def test_EnrichmentWindow_get_analysis_params_single_set(qtbot, enrichment_window, button_name, test_name,
                                                         test_arg_truth, en_set, en_set_truth, bg_set, bg_set_truth,
                                                         available_objects, stats_kwargs, dataset_kwargs):
    kwargs_truth = dict()
    kwargs_truth.update(stats_kwargs)
    kwargs_truth.update(dataset_kwargs)

    set_name_truth = available_objects[en_set_truth][0].name
    enrichment_window.widgets['dataset_radiobox'].radio_buttons[button_name].click()
    enrichment_window.stats_widgets['stats_radiobox'].radio_buttons[test_name].click()

    enrichment_window.widgets['enrichment_list'].showPopup()
    qtbot.keyClicks(enrichment_window.widgets['enrichment_list'], en_set)

    enrichment_window.stats_widgets['alpha'].clear()
    qtbot.keyClicks(enrichment_window.stats_widgets['alpha'], str(kwargs_truth['alpha']))

    for key in stats_kwargs:
        if key not in {'alpha'}:
            enrichment_window.stats_widgets[key].setValue(stats_kwargs[key])

    for key in dataset_kwargs:
        if key in enrichment_window.parameter_widgets:
            qtbot.keyClicks(enrichment_window.parameter_widgets[key].combo, dataset_kwargs[key])
        elif key in enrichment_window.plot_widgets:
            if not dataset_kwargs[key]:
                enrichment_window.plot_widgets[key].switch.click()

    enrichment_window.widgets['bg_list'].showPopup()
    qtbot.keyClicks(enrichment_window.widgets['bg_list'], bg_set)

    gene_set, bg_set, gene_set_name, kwargs, predecessor_ids = enrichment_window.get_analysis_params()

    assert gene_set == available_objects[en_set_truth][0].obj()

    assert bg_set == available_objects[bg_set_truth][0].obj()
    assert kwargs['parametric_test'] == test_arg_truth

    assert gene_set_name == set_name_truth


@pytest.mark.parametrize('en_set,bg_set,en_set_truth,bg_set_truth,', [
    ('third tab', 'first tab', 'third tab', 'first tab'),
    ('second tab', 'third tab', 'second tab', 'third tab'),
])
@pytest.mark.parametrize('button_name,dataset_name_truth,dataset_kwargs', [
    ('Gene Ontology (GO)', 'go',
     dict(plot_horizontal=True, plot_ontology_graph=False, organism='auto', excluded_evidence_types='experimental')),
    ('Kyoto Encyclopedia of Genes and Genomes (KEGG)', 'kegg',
     dict(plot_horizontal=True, gene_id_type='auto')),
    ('Categorical attributes', 'user_defined', dict(attributes='all', plot_horizontal=False))
])
@pytest.mark.parametrize('test_name,is_single_set,test_arg_truth,stats_kwargs', [
    ("Fisher's Exact test", False, 'fisher', dict(alpha=0.05)),
    ('Hypergeometric test', False, 'hypergeometric', dict(alpha=0.5)),
    ('Randomization test', False, 'randomization', dict(alpha=0.13, random_seed=42)),
    ('Single-set enrichment (XL-mHG test)', True, 'single_set', dict(alpha=0.01))
])
def test_EnrichmentWindow_run_analysis(qtbot, enrichment_window, button_name, test_name,
                                       test_arg_truth, en_set, en_set_truth, bg_set, bg_set_truth, dataset_name_truth,
                                       available_objects, stats_kwargs, dataset_kwargs, is_single_set):
    func_truth = {
        ('go', False): enrichment.FeatureSet.go_enrichment,
        ('go', True): enrichment.RankedSet.single_set_go_enrichment,
        ('kegg', False): enrichment.FeatureSet.kegg_enrichment,
        ('kegg', True): enrichment.RankedSet.single_set_kegg_enrichment,
        ('user_defined', False): enrichment.FeatureSet.user_defined_enrichment,
        ('user_defined', True): enrichment.RankedSet.single_set_enrichment}

    set_name_truth = available_objects[en_set_truth][0].name

    if is_single_set:
        gene_set_truth = enrichment.RankedSet(available_objects[en_set_truth][0].obj(), set_name_truth)
    else:
        gene_set_truth = enrichment.FeatureSet(available_objects[en_set_truth][0].obj() if isinstance(
            available_objects[en_set_truth][0].obj(), set) else available_objects[en_set_truth][0].obj().index_set,
                                               set_name_truth)

    kwargs_truth = dict()
    kwargs_truth.update(stats_kwargs)
    kwargs_truth.update(dataset_kwargs)

    enrichment_window.widgets['dataset_radiobox'].radio_buttons[button_name].click()
    enrichment_window.stats_widgets['stats_radiobox'].radio_buttons[test_name].click()

    enrichment_window.widgets['enrichment_list'].showPopup()
    qtbot.keyClicks(enrichment_window.widgets['enrichment_list'], en_set)

    enrichment_window.stats_widgets['alpha'].clear()
    qtbot.keyClicks(enrichment_window.stats_widgets['alpha'], str(kwargs_truth['alpha']))

    for key in stats_kwargs:
        if key not in {'alpha'}:
            enrichment_window.stats_widgets[key].setValue(stats_kwargs[key])

    for key in dataset_kwargs:
        if key in enrichment_window.parameter_widgets:
            qtbot.keyClicks(enrichment_window.parameter_widgets[key].combo, dataset_kwargs[key])
        elif key in enrichment_window.plot_widgets:
            if not dataset_kwargs[key]:
                enrichment_window.plot_widgets[key].switch.click()

    if not is_single_set:
        enrichment_window.widgets['bg_list'].showPopup()
        qtbot.keyClicks(enrichment_window.widgets['bg_list'], bg_set)

    with qtbot.waitSignal(enrichment_window.enrichmentStarted) as blocker:
        enrichment_window.widgets['run_button'].click()

    assert isinstance(blocker.args[0], gui_widgets.Worker)
    worker = blocker.args[0]
    assert worker.emit_args[0] == set_name_truth

    if is_single_set:
        pass
    else:
        assert worker.partial.keywords['statistical_test'] == test_arg_truth
        assert worker.partial.keywords['background_genes'].gene_set == available_objects[bg_set_truth][
            0].obj() if isinstance(available_objects[bg_set_truth][0].obj(), set) else available_objects[bg_set_truth][
            0].obj().index_set

    for kw in kwargs_truth:
        assert worker.partial.keywords[kw] == kwargs_truth[kw]

    assert worker.partial.func == func_truth[(dataset_name_truth, is_single_set)]
    assert worker.partial.args[0] == gene_set_truth


@pytest.mark.parametrize('en_set,bg_set,en_set_truth,bg_set_truth,', [
    ('first tab', 'second tab', 'first tab', 'second tab'),
    ('third tab', 'first tab', 'third tab', 'first tab'),
    ('second tab', 'third tab', 'second tab', 'third tab'),
])
@pytest.mark.parametrize('button_name,dataset_kwargs', [
    ('Non-categorical attributes', dict(plot_log_scale=False, attributes='all')),
])
@pytest.mark.parametrize('test_name,test_arg_truth,stats_kwargs', [
    ("One-sample T-test (parametric)", True, dict(alpha=0.08)),
    ('Sign test (non-parametric)', False, dict(alpha=0.5))
])
def test_EnrichmentWindow_run_analysis_non_categorical(qtbot, enrichment_window, button_name, test_name,
                                                       test_arg_truth, en_set, en_set_truth, bg_set, bg_set_truth,
                                                       available_objects, stats_kwargs, dataset_kwargs):
    set_name_truth = available_objects[en_set_truth][0].name
    gene_set_truth = enrichment.FeatureSet(available_objects[en_set_truth][0].obj() if isinstance(
        available_objects[en_set_truth][0].obj(), set) else available_objects[en_set_truth][0].obj().index_set,
                                           set_name_truth)

    kwargs_truth = dict()
    kwargs_truth.update(stats_kwargs)
    kwargs_truth.update(dataset_kwargs)

    enrichment_window.widgets['dataset_radiobox'].radio_buttons[button_name].click()
    enrichment_window.stats_widgets['stats_radiobox'].radio_buttons[test_name].click()

    enrichment_window.widgets['enrichment_list'].showPopup()
    qtbot.keyClicks(enrichment_window.widgets['enrichment_list'], en_set)

    enrichment_window.stats_widgets['alpha'].clear()
    qtbot.keyClicks(enrichment_window.stats_widgets['alpha'], str(kwargs_truth['alpha']))

    for key in stats_kwargs:
        if key not in {'alpha'}:
            enrichment_window.stats_widgets[key].setValue(stats_kwargs[key])

    for key in dataset_kwargs:
        if key in enrichment_window.parameter_widgets:
            qtbot.keyClicks(enrichment_window.parameter_widgets[key].combo, dataset_kwargs[key])
        elif key in enrichment_window.plot_widgets:
            if not dataset_kwargs[key]:
                enrichment_window.plot_widgets[key].switch.click()

    enrichment_window.widgets['bg_list'].showPopup()
    qtbot.keyClicks(enrichment_window.widgets['bg_list'], bg_set)

    with qtbot.waitSignal(enrichment_window.enrichmentStarted) as blocker:
        enrichment_window.widgets['run_button'].click()

    assert isinstance(blocker.args[0], gui_widgets.Worker)
    worker = blocker.args[0]
    assert worker.emit_args[0] == set_name_truth

    assert worker.partial.keywords['parametric_test'] == test_arg_truth
    for kw in kwargs_truth:
        assert worker.partial.keywords[kw] == kwargs_truth[kw]

    assert worker.partial.func == enrichment.FeatureSet.non_categorical_enrichment
    assert worker.partial.args[0] == gene_set_truth

    assert worker.partial.keywords['background_genes'].gene_set == available_objects[bg_set_truth][
        0].obj() if isinstance(available_objects[bg_set_truth][0].obj(), set) else available_objects[bg_set_truth][
        0].obj().index_set


def test_SetOperationWindow_init(set_op_window):
    _ = set_op_window


@pytest.mark.parametrize('op_name,truth', [
    ('Intersection', 'intersection'),
    ('Union', 'union'),
    ('Symmetric Difference', 'symmetric_difference'),
    ('Majority-Vote Intersection', 'majority_vote_intersection'),
    ('Other', 'other')
])
@pytest.mark.parametrize('second_op_name,second_truth', [
    ('Intersection', 'intersection'),
    ('Union', 'union'),
    ('Symmetric Difference', 'symmetric_difference'),
    ('Majority-Vote Intersection', 'majority_vote_intersection'),
    ('Other', 'other')
])
def test_SetOperationWindow_get_current_func_name(set_op_window, op_name, truth, second_op_name, second_truth):
    assert set_op_window.get_current_func_name() is None
    set_op_window.widgets['radio_button_box'].radio_buttons[op_name].click()
    assert set_op_window.get_current_func_name() == truth
    set_op_window.widgets['radio_button_box'].radio_buttons[second_op_name].click()
    assert set_op_window.get_current_func_name() == second_truth


def test_SetOperationWindow_canvas_types(set_op_window):
    assert isinstance(set_op_window.widgets['canvas'], gui_graphics.EmptyCanvas)

    set_op_window.widgets['set_list'].list_items[0].setSelected(True)
    assert isinstance(set_op_window.widgets['canvas'], gui_graphics.EmptyCanvas)

    set_op_window.widgets['set_list'].list_items[1].setSelected(True)
    assert isinstance(set_op_window.widgets['canvas'], gui_graphics.VennInteractiveCanvas)

    set_op_window.widgets['set_list'].list_items[2].setSelected(True)
    assert isinstance(set_op_window.widgets['canvas'], gui_graphics.VennInteractiveCanvas)

    set_op_window.widgets['set_list'].select_all_button.click()
    assert isinstance(set_op_window.widgets['canvas'], gui_graphics.UpSetInteractiveCanvas)

    set_op_window.widgets['set_list'].list_items[0].setSelected(False)
    assert isinstance(set_op_window.widgets['canvas'], gui_graphics.VennInteractiveCanvas)

    set_op_window.widgets['set_list'].clear_all_button.click()
    assert isinstance(set_op_window.widgets['canvas'], gui_graphics.EmptyCanvas)


@pytest.mark.parametrize('n_selected', [3, 4])
def test_SetOperationWindow_primary_set_change(qtbot, set_op_window, n_selected):
    for i in range(n_selected):
        set_op_window.widgets['set_list'].list_items[i].setSelected(True)

    with qtbot.waitSignal(set_op_window.primarySetChangedDifference):
        set_op_window.widgets['radio_button_box'].radio_buttons['Difference'].click()

    for tab in ['first tab', 'second tab', 'third tab']:
        with qtbot.waitSignal(set_op_window.primarySetChangedDifference) as blocker:
            set_op_window.widgets['choose_primary_set'].setCurrentText(tab)
            print(qtbot.screenshot(set_op_window))
        assert blocker.args[0] == tab

    with qtbot.waitSignal(set_op_window.primarySetChangedIntersection):
        set_op_window.widgets['radio_button_box'].radio_buttons['Intersection'].click()

    for tab in ['first tab', 'second tab', 'third tab']:
        with qtbot.waitSignal(set_op_window.primarySetChangedIntersection):
            set_op_window.widgets['choose_primary_set'].setCurrentText(tab)


apply_set_ops_parametrize = [
    ('Union', [0, 2],
     {'WBGene00018199', 'WBGene00020407', 'WBGene00045366', 'WBGene00044258', 'WBGene00010100', 'WBGene00018193',
      'WBGene00219307', 'WBGene00021019', 'WBGene00045410', 'WBGene00194708', 'WBGene00021589', 'WBGene00219304',
      'WBGene00023036', 'WBGene00021375', 'WBGene00008447', 'WBGene00044799', 'WBGene00001118', 'WBGene00077437',
      'WBGene00010755', 'WBGene00012919', 'WBGene00021654', 'WBGene00013816', 'WBGene00022486', 'WBGene00019174',
      'WBGene00007674', 'WBGene00012648', 'WBGene00021605'}
     ),
    ('Union', [1, 2, 3],
     {'WBGene00018199', 'WBGene00007064', 'WBGene00020407', 'WBGene00007079', 'WBGene00044478', 'WBGene00045366',
      'WBGene00043989', 'WBGene00007075', 'WBGene00044258', 'WBGene00010100', 'WBGene00043987', 'WBGene00007066',
      'WBGene00018193', 'WBGene00022730', 'WBGene00044022', 'WBGene00077504', 'WBGene00219307', 'WBGene00014997',
      'WBGene00021019', 'WBGene00043990', 'WBGene00045410', 'WBGene00021018', 'WBGene00194708', 'WBGene00007078',
      'WBGene00021589', 'WBGene00219304', 'WBGene00023036', 'WBGene00007069', 'WBGene00021375', 'WBGene00007076',
      'WBGene00008447', 'WBGene00044799', 'WBGene00001118', 'WBGene00077502', 'WBGene00007067', 'WBGene00077503',
      'WBGene00007071', 'WBGene00012961', 'WBGene00077437', 'WBGene00022438', 'WBGene00010755', 'WBGene00007063',
      'WBGene00012919', 'WBGene00021654', 'WBGene00013816', 'WBGene00007074', 'WBGene00010507', 'WBGene00016635',
      'WBGene00022486', 'WBGene00043988', 'WBGene00007077', 'WBGene00019174', 'WBGene00012452', 'WBGene00007674',
      'WBGene00012648', 'WBGene00044951', 'WBGene00021605'}
     ),
    ('Intersection', [0, 2], {'WBGene00044258', 'WBGene00045410', 'WBGene00010100'}),
    ('Intersection', [1, 2, 3], set()),
    ('Difference', [0, 2], {'WBGene00008447'}),
    ('Difference', [1, 2, 3],
     {'WBGene00044478', 'WBGene00008447', 'WBGene00021018', 'WBGene00010507', 'WBGene00016635', 'WBGene00012452',
      'WBGene00022730', 'WBGene00012961', 'WBGene00022438'}
     ),
    ('Symmetric Difference', [0, 1],
     {'WBGene00018199', 'WBGene00044478', 'WBGene00045366', 'WBGene00022730', 'WBGene00219307', 'WBGene00021019',
      'WBGene00021018', 'WBGene00194708', 'WBGene00219304', 'WBGene00023036', 'WBGene00021375', 'WBGene00012961',
      'WBGene00077437', 'WBGene00022438', 'WBGene00013816', 'WBGene00010507', 'WBGene00016635', 'WBGene00022486',
      'WBGene00019174', 'WBGene00012452', 'WBGene00007674', 'WBGene00012648'}
     ),
    ('Symmetric Difference', [2, 3],
     {'WBGene00018199', 'WBGene00045366', 'WBGene00043989', 'WBGene00043987', 'WBGene00007066', 'WBGene00219307',
      'WBGene00021019', 'WBGene00043990', 'WBGene00007078', 'WBGene00219304', 'WBGene00023036', 'WBGene00044799',
      'WBGene00077502', 'WBGene00001118', 'WBGene00007067', 'WBGene00077437', 'WBGene00010755', 'WBGene00007063',
      'WBGene00021654', 'WBGene00013816', 'WBGene00007674', 'WBGene00012648', 'WBGene00007064', 'WBGene00020407',
      'WBGene00007079', 'WBGene00007075', 'WBGene00044258', 'WBGene00010100', 'WBGene00021605', 'WBGene00018193',
      'WBGene00044022', 'WBGene00077504', 'WBGene00045410', 'WBGene00194708', 'WBGene00021589', 'WBGene00007069',
      'WBGene00021375', 'WBGene00007076', 'WBGene00077503', 'WBGene00007071', 'WBGene00012919', 'WBGene00007074',
      'WBGene00043988', 'WBGene00007077', 'WBGene00022486', 'WBGene00019174', 'WBGene00044951', 'WBGene00014997'}
     )
]


@pytest.mark.parametrize('operation,set_indices,truth', apply_set_ops_parametrize)
def test_SetOperationWindow_apply_set_op(qtbot, set_op_window, operation, set_indices, truth):
    for ind in set_indices:
        set_op_window.widgets['set_list'].list_items[ind].setSelected(True)
    set_op_window.widgets['radio_button_box'].radio_buttons[operation].click()
    if operation in ['Difference', 'Intersection']:
        set_op_window.widgets['choose_primary_set'].setCurrentText(
            set_op_window.widgets['set_list'].items[set_indices[0]])
    with qtbot.waitSignal(set_op_window.geneSetReturned) as blocker:
        set_op_window.widgets['apply_button'].click()
    assert blocker.args[0] == truth


@pytest.mark.parametrize('operation,set_indices,truth', apply_set_ops_parametrize)
def test_SetOperationWindow_apply_set_op_other(qtbot, set_op_window, operation, set_indices, truth):
    for ind in set_indices:
        set_op_window.widgets['set_list'].list_items[ind].setSelected(True)
    set_op_window.widgets['radio_button_box'].radio_buttons[operation].click()
    if operation in ['Difference', 'Intersection']:
        set_op_window.widgets['choose_primary_set'].setCurrentText(
            set_op_window.widgets['set_list'].items[set_indices[0]])

    set_op_window.widgets['radio_button_box'].radio_buttons['Other'].click()
    with qtbot.waitSignal(set_op_window.geneSetReturned) as blocker:
        set_op_window.widgets['apply_button'].click()
    assert blocker.args[0] == truth


@pytest.mark.parametrize('operation,set_indices,primary_set,truth',
                         [('Intersection', [0, 2], 2, {'WBGene00044258', 'WBGene00045410', 'WBGene00010100'}),
                          ('Intersection', [1, 2, 3], 1, set()),
                          ('Difference', [0, 2], 2,
                           {'WBGene00001118', 'WBGene00007674', 'WBGene00010755', 'WBGene00012648', 'WBGene00012919',
                            'WBGene00013816', 'WBGene00018193', 'WBGene00018199', 'WBGene00019174', 'WBGene00020407',
                            'WBGene00021019', 'WBGene00021375', 'WBGene00021589', 'WBGene00021605', 'WBGene00021654',
                            'WBGene00022486', 'WBGene00023036', 'WBGene00044799', 'WBGene00045366', 'WBGene00077437',
                            'WBGene00194708', 'WBGene00219304', 'WBGene00219307'}),
                          ('Difference', [1, 2, 3], 1,
                           {'WBGene00044478', 'WBGene00008447', 'WBGene00021018', 'WBGene00010507', 'WBGene00016635',
                            'WBGene00012452',
                            'WBGene00022730', 'WBGene00012961', 'WBGene00022438'})])
def test_SetOperationWindow_apply_set_op_inplace(qtbot, four_available_objects_and_empty, set_op_window, operation,
                                                 set_indices, primary_set, truth):
    primary_set_name = set_op_window.widgets['set_list'].items[primary_set]

    for ind in set_indices:
        set_op_window.widgets['set_list'].list_items[ind].setSelected(True)
    set_op_window.widgets['radio_button_box'].radio_buttons[operation].click()
    set_op_window.widgets['choose_primary_set'].setCurrentText(
        primary_set_name)

    with qtbot.waitSignal(set_op_window.geneSetReturned) as blocker:
        set_op_window.widgets['apply_button'].click()
    assert blocker.args[0] == truth

    inplace_truth = four_available_objects_and_empty[primary_set_name][0].obj().__copy__()
    obj_names = [set_op_window.widgets['set_list'].items[ind] for ind in set_indices if ind != primary_set]
    objs_for_operation = [four_available_objects_and_empty[name][0].obj() for name in obj_names]
    if operation == 'Difference':
        inplace_truth.difference(
            *objs_for_operation, inplace=True)
    else:
        inplace_truth.intersection(*objs_for_operation, inplace=True)
    set_op_window.parameter_widgets['inplace'].switch.click()
    with qtbot.assertNotEmitted(set_op_window.geneSetReturned) as blocker:
        set_op_window.widgets['apply_button'].click()
    assert four_available_objects_and_empty[primary_set_name][0].obj() == inplace_truth


@pytest.mark.parametrize('threshold,truth', [
    (0, {'WBGene00194708', 'WBGene00044951', 'WBGene00018193', 'WBGene00022730', 'WBGene00012919', 'WBGene00044022',
         'WBGene00044799', 'WBGene00001118', 'WBGene00007069', 'WBGene00021375', 'WBGene00021654', 'WBGene00077437',
         'WBGene00010507', 'WBGene00043987', 'WBGene00010755', 'WBGene00012648', 'WBGene00077503', 'WBGene00007079',
         'WBGene00010100', 'WBGene00012452', 'WBGene00013816', 'WBGene00022438', 'WBGene00012961', 'WBGene00016635',
         'WBGene00007064', 'WBGene00219307', 'WBGene00043989', 'WBGene00007063', 'WBGene00023036', 'WBGene00007078',
         'WBGene00043988', 'WBGene00077504', 'WBGene00007066', 'WBGene00007674', 'WBGene00044258', 'WBGene00021589',
         'WBGene00021605', 'WBGene00021019', 'WBGene00007071', 'WBGene00219304', 'WBGene00043990', 'WBGene00014997',
         'WBGene00045410', 'WBGene00077502', 'WBGene00020407', 'WBGene00007075', 'WBGene00018199', 'WBGene00045366',
         'WBGene00007067', 'WBGene00044478', 'WBGene00022486', 'WBGene00007074', 'WBGene00007076', 'WBGene00007077',
         'WBGene00008447', 'WBGene00019174', 'WBGene00021018'}),
    (0.25, {'WBGene00194708', 'WBGene00044951', 'WBGene00018193', 'WBGene00022730', 'WBGene00012919', 'WBGene00044022',
            'WBGene00044799', 'WBGene00001118', 'WBGene00007069', 'WBGene00021375', 'WBGene00021654', 'WBGene00077437',
            'WBGene00010507', 'WBGene00043987', 'WBGene00010755', 'WBGene00012648', 'WBGene00077503', 'WBGene00007079',
            'WBGene00010100', 'WBGene00012452', 'WBGene00013816', 'WBGene00022438', 'WBGene00012961', 'WBGene00016635',
            'WBGene00007064', 'WBGene00219307', 'WBGene00043989', 'WBGene00007063', 'WBGene00023036', 'WBGene00007078',
            'WBGene00043988', 'WBGene00077504', 'WBGene00007066', 'WBGene00007674', 'WBGene00044258', 'WBGene00021589',
            'WBGene00021605', 'WBGene00021019', 'WBGene00007071', 'WBGene00219304', 'WBGene00043990', 'WBGene00014997',
            'WBGene00045410', 'WBGene00077502', 'WBGene00020407', 'WBGene00007075', 'WBGene00018199', 'WBGene00045366',
            'WBGene00007067', 'WBGene00044478', 'WBGene00022486', 'WBGene00007074', 'WBGene00007076', 'WBGene00007077',
            'WBGene00008447', 'WBGene00019174', 'WBGene00021018'}),
    (0.57, {'WBGene00044258', 'WBGene00010100', 'WBGene00045410'}),
    (0.99, set()),
    (1, set())
])
def test_SetOperationWindow_apply_set_op_majority_vote(qtbot, set_op_window, threshold, truth):
    for ind in range(4):
        set_op_window.widgets['set_list'].list_items[ind].setSelected(True)
    set_op_window.widgets['radio_button_box'].radio_buttons['Majority-Vote Intersection'].click()
    set_op_window.parameter_widgets['majority_threshold'].setValue(threshold)
    with qtbot.waitSignal(set_op_window.geneSetReturned) as blocker:
        set_op_window.widgets['apply_button'].click()
    assert blocker.args[0] == truth


def test_SetVisualizationWindow_init(set_vis_window):
    _ = set_vis_window


@pytest.mark.parametrize('op_name,truth', [
    ('Venn Diagram', 'venn_diagram'),
    ('UpSet Plot', 'upset_plot')
])
@pytest.mark.parametrize('second_op_name,second_truth', [
    ('Venn Diagram', 'venn_diagram'),
    ('UpSet Plot', 'upset_plot')
])
def test_SetVisualizationWindow_get_current_func_name(set_vis_window, op_name, truth, second_op_name,
                                                      second_truth):
    assert set_vis_window.get_current_func_name() is None
    set_vis_window.widgets['radio_button_box'].radio_buttons[op_name].click()
    assert set_vis_window.get_current_func_name() == truth
    set_vis_window.widgets['radio_button_box'].radio_buttons[second_op_name].click()
    assert set_vis_window.get_current_func_name() == second_truth


@pytest.mark.parametrize('is_func_selected', ['Venn Diagram', 'UpSet Plot', False])
def test_SetVisualizationWindow_canvas_types(qtbot, set_vis_window, is_func_selected):
    expected_canvas = gui_graphics.BasePreviewCanvas if is_func_selected else gui_graphics.EmptyCanvas
    if is_func_selected:
        qtbot.mouseClick(set_vis_window.widgets['radio_button_box'].radio_buttons[is_func_selected], LEFT_CLICK)
    assert isinstance(set_vis_window.widgets['canvas'], gui_graphics.EmptyCanvas)

    set_vis_window.widgets['set_list'].list_items[0].setSelected(True)
    assert isinstance(set_vis_window.widgets['canvas'], gui_graphics.EmptyCanvas)

    set_vis_window.widgets['set_list'].list_items[1].setSelected(True)
    assert isinstance(set_vis_window.widgets['canvas'], expected_canvas)

    set_vis_window.widgets['set_list'].list_items[2].setSelected(True)
    assert isinstance(set_vis_window.widgets['canvas'], expected_canvas)

    set_vis_window.widgets['set_list'].select_all_button.click()
    assert isinstance(set_vis_window.widgets['canvas'], expected_canvas)

    set_vis_window.widgets['set_list'].list_items[0].setSelected(False)
    assert isinstance(set_vis_window.widgets['canvas'], expected_canvas)

    set_vis_window.widgets['set_list'].clear_all_button.click()
    assert isinstance(set_vis_window.widgets['canvas'], gui_graphics.EmptyCanvas)


@pytest.mark.parametrize('op_name', [
    'Venn Diagram',
    'UpSet Plot'
])
@pytest.mark.parametrize('second_op_name', [
    'Venn Diagram',
    'UpSet Plot'
])
def test_SetVisualizationWindow_function_change_canvas(monkeypatch_create_canvas, set_vis_window, op_name,
                                                       second_op_name):
    n_sets = 3
    for i in range(n_sets):
        set_vis_window.widgets['set_list'].list_items[i].setSelected(True)

    while len(monkeypatch_create_canvas) > 0:
        monkeypatch_create_canvas.pop(-1)

    set_vis_window.widgets['radio_button_box'].radio_buttons[op_name].click()
    assert monkeypatch_create_canvas == [True]
    set_vis_window.widgets['radio_button_box'].radio_buttons[second_op_name].click()
    assert monkeypatch_create_canvas == [True, True]


@pytest.mark.parametrize('op_name,n_sets,sample_bool_param', [
    ('Venn Diagram', 2, 'weighted'),
    ('UpSet Plot', 4, 'show_percentages')
])
def test_SetVisualizationWindow_parameter_change_canvas(monkeypatch, qtbot, set_vis_window, op_name, n_sets,
                                                        sample_bool_param):
    canvas_created = []

    def mock_create_canvas(self):
        canvas_created.append(True)

    monkeypatch.setattr(SetVisualizationWindow, 'create_canvas', mock_create_canvas)

    set_vis_window.widgets['radio_button_box'].radio_buttons[op_name].click()
    for i in range(n_sets):
        set_vis_window.widgets['set_list'].list_items[i].setSelected(True)

    set_vis_window.parameter_widgets['title_fontsize'].setValue(27)

    assert canvas_created == [True]

    qtbot.mouseClick(set_vis_window.parameter_widgets[sample_bool_param].switch, LEFT_CLICK)

    assert canvas_created == [True, True]


@pytest.mark.parametrize('func_name,op_name,n_sets,kwargs_truth', [
    ('venn_diagram', 'Venn Diagram', 2, {'title': 'default', 'weighted': True, 'transparency': 0.4}),
    ('venn_diagram', 'Venn Diagram', 3, {'title': 'default', 'weighted': True, 'linestyle': 'solid'}),
    ('upset_plot', 'UpSet Plot', 2, {'title': 'UpSet Plot', 'title_fontsize': 20}),
    ('upset_plot', 'UpSet Plot', 4, {'title': 'UpSet Plot', 'show_percentages': True}),

])
def test_SetVisualizationWindow_generate_graph(qtbot, set_vis_window, monkeypatch, func_name, op_name, n_sets,
                                               kwargs_truth, four_available_objects_and_empty):
    called = []

    def mock_func(*args, **kwargs):
        for key in kwargs_truth:
            assert kwargs[key] == kwargs_truth[key]
        assert 'fig' not in kwargs
        assert len(args) == 1
        objs_truth = {
            list(four_available_objects_and_empty.keys())[i]:
                four_available_objects_and_empty[list(four_available_objects_and_empty.keys())[i]][
                    0].obj() for i in range(n_sets)}
        assert args[0] == objs_truth

        called.append(True)
        return plt.Figure()

    set_vis_window.widgets['radio_button_box'].radio_buttons[op_name].click()
    for i in range(n_sets):
        set_vis_window.widgets['set_list'].list_items[i].setSelected(True)

    monkeypatch.setattr(enrichment, func_name, mock_func)

    qtbot.mouseClick(set_vis_window.widgets['generate_button'], LEFT_CLICK)
    assert called == [True]


def test_FilterTabPage_init(qtbot):
    _, _ = widget_setup(qtbot, FilterTabPage)


@pytest.mark.parametrize('outputs,exp_signals', [
    ([], []),
    (tuple(), []),
    (filtering.CountFilter('tests/test_files/counted.csv'), ['itemSpawned', 'filterObjectCreated']),
    (enrichment.FeatureSet({'a', 'b', 'c'}, 'set name'), ['itemSpawned', 'featureSetCreated']),
    (pl.DataFrame([1, 2, 3]), ['itemSpawned']),
    (plt.Figure(), ['itemSpawned']),
    ('filterlist', []),
    ('dict', []),
    ('mix', []),

])
def test_FilterTabPage_process_outputs_signals(qtbot, outputs, exp_signals):
    qtbot, tabpage = widget_setup(qtbot, FilterTabPage)
    job_id = -1
    source_name = 'source name'
    all_signals = [tabpage.filterObjectCreated, tabpage.featureSetCreated, tabpage.itemSpawned]

    if len(exp_signals) == 0:
        for signal in all_signals:
            with qtbot.assertNotEmitted(signal):
                tabpage.process_outputs(outputs, job_id, source_name)
    else:
        signals = [getattr(tabpage, sig) for sig in exp_signals]
        with qtbot.waitSignals(signals):
            tabpage.process_outputs(outputs, job_id, source_name)


@pytest.mark.parametrize('outputs,exp_filts,exp_sets,exp_items', [
    (filtering.CountFilter('tests/test_files/counted.csv'),
     [(filtering.CountFilter('tests/test_files/counted.csv'), 42)],
     [], [("'source name'\noutput", 42, -1, filtering.CountFilter('tests/test_files/counted.csv'))]),

    (enrichment.FeatureSet({'a', 'b', 'c'}, 'set name'), [], [(enrichment.FeatureSet({'a', 'b', 'c'}, 'set name'), 42)],
     [("'source name'\noutput", 42, -1, enrichment.FeatureSet({'a', 'b', 'c'}, 'set name'))]),

    (pl.DataFrame([1, 2, 3]), [], [], [("'source name'\noutput", 42, -1, pl.DataFrame([1, 2, 3]))]),

    (plt.Figure(), [], [], [("'source name'\ngraph", 42, -1, plt.gcf())]),

    ([filtering.Filter('tests/test_files/counted.csv'), filtering.DESeqFilter('tests/test_files/test_deseq.csv')],
     [(filtering.Filter('tests/test_files/counted.csv'), 42),
      (filtering.DESeqFilter('tests/test_files/test_deseq.csv'), 42)], [],
     [("'source name'\noutput", 42, -1, filtering.Filter('tests/test_files/counted.csv')),
      ("'source name'\noutput", 42, -1, filtering.DESeqFilter('tests/test_files/test_deseq.csv'))]),

    ({'out1': plt.Figure(), 'out2': pl.DataFrame(), 'other': 'some str'}, [], [],
     [("'source name'\ngraph", 42, -1, plt.gcf()), ("'source name'\noutput", 42, -1, pl.DataFrame())]),

    ([], [], [], []),

])
def test_FilterTabPage_process_outputs_signal_contents(monkeypatch, qtbot, outputs, exp_filts, exp_sets, exp_items):
    monkeypatch.setattr(JOB_COUNTER, 'get_id', lambda *args: 42)

    def mock_exec(self):
        self.select_all.click()
        self.accepted.emit()

    monkeypatch.setattr(MultiKeepWindow, 'exec', mock_exec)

    qtbot, tabpage = widget_setup(qtbot, FilterTabPage)
    tabpage.name = 'tab_name*'
    job_id = -1
    source_name = 'source name'
    filter_objs = []
    gene_sets = []
    items = []
    tabpage.filterObjectCreated.connect(lambda *args: filter_objs.append(args))
    tabpage.featureSetCreated.connect(lambda *args: gene_sets.append(args))
    tabpage.itemSpawned.connect(lambda *args: items.append(args))

    tabpage.process_outputs(outputs, job_id, source_name)

    assert filter_objs == exp_filts
    assert gene_sets == exp_sets
    assert len(items) == len(exp_items)
    for item, item_truth in zip(items, exp_items):
        assert type(item[-1]) == type(item_truth[-1])


def test_FilterTabPage_load_file(qtbot):
    obj_truth = filtering.CountFilter('tests/test_files/counted.csv')
    qtbot, window = widget_setup(qtbot, FilterTabPage)
    assert window.is_empty()
    assert not window.basic_widgets['start_button'].isEnabled()

    window.basic_widgets['file_path'].clear()
    qtbot.keyClicks(window.basic_widgets['file_path'].file_path, str(Path('tests/test_files/counted.csv').absolute()))
    window.basic_widgets['table_type_combo'].setCurrentText('Count matrix')
    qtbot.mouseClick(window.basic_widgets['start_button'], LEFT_CLICK)

    assert not window.is_empty()
    assert window.obj() == obj_truth
    assert window.obj_type() == filtering.CountFilter
    assert window.name == 'counted'
    assert window.get_table_type() == 'Count matrix'


def test_FilterTabPage_from_obj(qtbot):
    table_name = 'table name'
    qtbot, window = widget_setup(qtbot, FilterTabPage)
    obj = filtering.DESeqFilter('tests/test_files/test_deseq.csv')
    assert window.is_empty()
    window.start_from_filter_obj(obj, 1, table_name)

    assert not window.is_empty()
    assert window.obj() == obj
    assert window.obj_type() == filtering.DESeqFilter
    assert window.name == table_name
    assert window.get_table_type() == 'Differential expression'


def test_FilterTabPage_cache(qtbot, monkeypatch):
    qtbot, window = widget_setup(qtbot, FilterTabPage)
    filt = filtering.DESeqFilter('tests/test_files/test_deseq.csv')
    window.start_from_filter_obj(filt, 1, 'table name')
    cached = []

    def mock_cache(obj, filename):
        assert isinstance(obj, pl.DataFrame)
        assert obj.equals(filt.df)
        cached.append(True)

    monkeypatch.setattr(io, 'cache_gui_file', mock_cache)

    fname = window.cache()
    assert fname.endswith('.parquet')
    assert len(fname) == 48

    time.sleep(0.01)
    fname2 = window.cache()
    assert cached == [True, True]
    assert fname != fname2


@pytest.mark.parametrize('filter_obj,truth', [
    (filtering.DESeqFilter('tests/test_files/test_deseq.csv', log2fc_col='my log2fc col', padj_col='my padj col'),
     {'log2fc_col': 'my log2fc col', 'padj_col': 'my padj col', 'pval_col': 'pvalue'}),
    (filtering.CountFilter('tests/test_files/counted.tsv'), {'is_normalized': False}),
    (filtering.FoldChangeFilter('tests/test_files/fc_1.csv', 'num_name', 'denom_name'),
     {'numerator_name': 'num_name', 'denominator_name': 'denom_name'}),
    (filtering.Filter('tests/test_files/test_deseq.csv'), {})

])
def test_FilterTabPage_obj_properties(qtbot, filter_obj, truth):
    qtbot, window = widget_setup(qtbot, FilterTabPage)
    window.start_from_filter_obj(filter_obj, 1, 'table name')

    assert window.obj_properties() == truth


def test_FilterTabPage_rename(qtbot, filtertabpage_with_undo_stack):
    new_name = 'my new table name'
    window, stack = filtertabpage_with_undo_stack
    window.overview_widgets['table_name'].setText(new_name)
    with qtbot.waitSignal(window.tabNameChange) as blocker:
        window.overview_widgets['rename_button'].click()
    assert blocker.args[0] == new_name
    assert str(window.obj().fname.stem) == new_name
    assert new_name in window.overview_widgets['table_name_label'].text()
    assert 'test_deseq' not in window.overview_widgets['table_name_label'].text()
    assert window.name == new_name


def test_FilterTabPage_undo_rename(qtbot, filtertabpage_with_undo_stack):
    new_name = 'my new table name'
    window, stack = filtertabpage_with_undo_stack
    prev_name = window.name
    qtbot.keyClicks(window.overview_widgets['table_name'], new_name)
    with qtbot.waitSignal(window.tabNameChange) as blocker:
        window.overview_widgets['rename_button'].click()
    assert blocker.args[0] == new_name

    with qtbot.waitSignal(window.tabNameChange) as blocker:
        stack.undo()
    assert blocker.args[0] == prev_name
    assert str(window.obj().fname.stem) == prev_name
    assert prev_name in window.overview_widgets['table_name_label'].text()
    assert new_name not in window.overview_widgets['table_name_label'].text()
    assert window.name == prev_name

    with qtbot.waitSignal(window.tabNameChange) as blocker:
        stack.redo()
    assert blocker.args[0] == new_name
    assert str(window.obj().fname.stem) == new_name
    assert new_name in window.overview_widgets['table_name_label'].text()
    assert prev_name not in window.overview_widgets['table_name_label'].text()
    assert window.name == new_name


@pytest.mark.parametrize('tab_type,args', [(FilterTabPage, [])])
def test_save_table_empty_tab(qtbot, tab_type, args):
    qtbot, window = widget_setup(qtbot, tab_type, *args)
    with qtbot.assertNotEmitted(window.tabSaved):
        window.save_file()


def test_FilterTabPage_save_table(qtbot, monkeypatch):
    fname = 'my filename.tsv'
    saved = []

    def mock_get_save_name(*args, **kwargs):
        saved.append('got name')
        return fname, '.tsv'

    def mock_save_table(self, suffix, filename):
        saved.append(filename)

    monkeypatch.setattr(QtWidgets.QFileDialog, 'getSaveFileName', mock_get_save_name)
    monkeypatch.setattr(filtering.Filter, 'save_table', mock_save_table)

    qtbot, window = widget_setup(qtbot, FilterTabPage)
    filt = filtering.DESeqFilter('tests/test_files/test_deseq.csv')
    window.start_from_filter_obj(filt, 1, 'table name')
    qtbot.mouseClick(window.overview_widgets['save_button'], LEFT_CLICK)

    assert saved == ['got name', fname]


def test_FilterTabPage_view_full_table(filtertabpage):
    filtertabpage.overview_widgets['view_button'].click()
    assert isinstance(filtertabpage.overview_widgets['full_table_view'], gui_windows.DataFrameView)
    assert filtertabpage.overview_widgets['full_table_view'].data_view.model()._dataframe.equals(filtertabpage.obj().df)


def test_FilterTabPage_apply_function(qtbot, filtertabpage_with_undo_stack):
    window, stack = filtertabpage_with_undo_stack
    orig = window.obj().__copy__()
    truth = window.obj().filter_significant(0.01, opposite=True, inplace=False)
    window.stack_buttons[0].click()
    window.stack.currentWidget().func_combo.setCurrentText(filtering.DESeqFilter.filter_significant.readable_name)
    window.stack.currentWidget().parameter_widgets['alpha'].clear()
    qtbot.keyClicks(window.stack.currentWidget().parameter_widgets['alpha'], '0.01')
    qtbot.mouseClick(window.stack.currentWidget().parameter_widgets['opposite'].switch, LEFT_CLICK)
    qtbot.mouseClick(window.stack.currentWidget().parameter_widgets['inplace'].switch, LEFT_CLICK)
    with qtbot.waitSignal(window.filterObjectCreated, timeout=10000) as blocker:
        qtbot.mouseClick(window.apply_button, LEFT_CLICK)
    assert blocker.args[0] == truth
    assert window.obj() == orig


def test_FilterTabPage_apply_split_clustering_function(qtbot, monkeypatch, countfiltertabpage_with_undo_stack):
    def mock_show_multikeep(self):
        self.select_all.setChecked(True)
        self.change_all()
        self.accept()
        self.button_box.button(QtWidgets.QDialogButtonBox.StandardButton.Ok).click()

    monkeypatch.setattr(MultiKeepWindow, 'exec', mock_show_multikeep)

    window, stack = countfiltertabpage_with_undo_stack

    def my_slot(tab, worker, func_name):
        window.process_outputs(worker.run()[0], func_name)

    window.startedClustering.connect(my_slot)

    orig = window.obj().__copy__()
    truth = orig.split_kmeans(n_clusters=3, random_seed=42)

    window.stack_buttons[4].click()
    qtbot.keyClicks(window.stack.currentWidget().func_combo, filtering.CountFilter.split_kmeans.readable_name)
    window.stack.currentWidget().parameter_widgets['n_clusters'].other.setValue(3)
    window.stack.currentWidget().parameter_widgets['random_seed'].setValue(42)
    with qtbot.waitSignals([window.filterObjectCreated, window.filterObjectCreated, window.filterObjectCreated],
                           timeout=15000) as blocker:
        qtbot.mouseClick(window.apply_button, LEFT_CLICK)

    res = [sig.args[0] for sig in blocker.all_signals_and_args]
    for i in range(3):
        assert np.allclose(res[i].df.drop(cs.first()), truth[i].df.drop(cs.first()), equal_nan=True)

    assert window.obj() == orig


def test_FilterTabPage_apply_function_inplace(qtbot, filtertabpage_with_undo_stack):
    window, stack = filtertabpage_with_undo_stack
    truth = window.obj().filter_significant(0.01, opposite=True, inplace=False)
    window.stack_buttons[0].click()
    window.stack.currentWidget().func_combo.setCurrentText(filtering.DESeqFilter.filter_significant.readable_name)
    window.stack.currentWidget().parameter_widgets['alpha'].clear()
    qtbot.keyClicks(window.stack.currentWidget().parameter_widgets['alpha'], '0.01')
    qtbot.mouseClick(window.stack.currentWidget().parameter_widgets['opposite'].switch, LEFT_CLICK)
    qtbot.mouseClick(window.apply_button, LEFT_CLICK)
    assert window.obj() == truth


def test_FilterTabPage_undo_function(qtbot, filtertabpage_with_undo_stack):
    window, stack = filtertabpage_with_undo_stack
    truth = window.obj().filter_significant(0.01, opposite=True, inplace=False)
    orig = window.obj().__copy__()
    window.stack_buttons[0].click()
    window.stack.currentWidget().func_combo.setCurrentText(filtering.DESeqFilter.filter_significant.readable_name)
    window.stack.currentWidget().parameter_widgets['alpha'].clear()
    qtbot.keyClicks(window.stack.currentWidget().parameter_widgets['alpha'], '0.01')
    qtbot.mouseClick(window.stack.currentWidget().parameter_widgets['opposite'].switch, LEFT_CLICK)
    qtbot.mouseClick(window.apply_button, LEFT_CLICK)
    assert window.obj() == truth

    stack.undo()

    assert window.obj() == orig

    stack.redo()

    assert window.obj() == truth


def test_FilterTabPage_apply_pipeline(qtbot, filtertabpage_with_undo_stack, pipeline):
    window, stack = filtertabpage_with_undo_stack
    filter_obj_orig = window.obj().__copy__()

    filter_obj_truth = pipeline.apply_to(window.obj(), inplace=False)[0]

    with qtbot.waitSignal(window.filterObjectCreated) as blocker:
        window.apply_pipeline(pipeline, pipeline_name='my pipeline', pipeline_id=1, inplace=False)
    assert blocker.args[0] == filter_obj_truth
    assert window.obj() == filter_obj_orig

    window.apply_pipeline(pipeline, pipeline_name='my pipeline', pipeline_id=1, inplace=True)
    assert window.obj() == filter_obj_truth


def test_FilterTabPage_undo_pipeline(filtertabpage_with_undo_stack, pipeline):
    window, stack = filtertabpage_with_undo_stack
    orig_name = window.name
    filter_obj_orig = window.obj().__copy__()
    filter_obj_truth = pipeline.apply_to(window.obj(), inplace=False)[0]
    window.apply_pipeline(pipeline, 'my pipeline', 1, True)
    assert window.obj() == filter_obj_truth

    stack.undo()
    assert window.obj() == filter_obj_orig
    assert window.name == orig_name

    stack.redo()
    assert window.obj() == filter_obj_truth
    assert window.name != orig_name


def test_FilterTabPage_open_clicom(countfiltertabpage_with_undo_stack, monkeypatch):
    tabpage = countfiltertabpage_with_undo_stack[0]
    opened = []

    def mock_show(*args, **kwargs):
        opened.append(True)

    monkeypatch.setattr(ClicomWindow, 'show', mock_show)

    tabpage.stack_buttons[4].click()
    tabpage.stack_widgets['Cluster'].func_combo.setCurrentText(filtering.CountFilter.split_clicom.readable_name)

    assert opened == [True]


def test_FilterTabPage_open_deseq(countfiltertabpage_with_undo_stack, monkeypatch):
    tabpage = countfiltertabpage_with_undo_stack[0]
    opened = []

    def mock_show(*args, **kwargs):
        opened.append(True)

    monkeypatch.setattr(DESeqWindow, 'show', mock_show)

    tabpage.stack_buttons[5].click()
    tabpage.stack_widgets['General'].func_combo.setCurrentText(
        filtering.CountFilter.differential_expression_deseq2.readable_name)

    assert opened == [True]


def test_FilterTabPage_open_limma(countfiltertabpage_with_undo_stack, monkeypatch):
    tabpage = countfiltertabpage_with_undo_stack[0]
    opened = []

    def mock_show(*args, **kwargs):
        opened.append(True)

    monkeypatch.setattr(LimmaWindow, 'show', mock_show)

    tabpage.stack_buttons[5].click()
    tabpage.stack_widgets['General'].func_combo.setCurrentText(
        filtering.CountFilter.differential_expression_limma_voom.readable_name)

    assert opened == [True]


def test_FilterTabPage_get_all_actions(countfiltertabpage_with_undo_stack, filtertabpage_with_undo_stack):
    countfilter = countfiltertabpage_with_undo_stack[0]
    deseqfilter = filtertabpage_with_undo_stack[0]
    truth_counts = {'Filter': [], 'Summarize': [], 'Visualize': [], 'Normalize': [], 'Cluster': [], 'General': []}
    truth_deseq = {'Filter': [], 'Summarize': [], 'Visualize': [], 'Normalize': [], 'Cluster': [], 'General': []}

    counts_res = countfilter.get_all_actions()
    deseq_res = deseqfilter.get_all_actions()

    assert sorted(counts_res.keys()) == sorted(truth_counts.keys())
    assert sorted(deseq_res.keys()) == sorted(truth_deseq.keys())

    assert len(counts_res['Cluster']) >= 5
    assert len(deseq_res['Cluster']) == 0

    for res in (counts_res, deseq_res):
        for action in res['Filter']:
            assert 'filter' in action or action.startswith('split')
        for action in res['Normalize']:
            assert action.startswith('normalize')
        for action in ['sort', 'transform']:
            assert action in res['General']
        for action in itertools.chain(res['General'], res['Visualize'], res['Summarize']):
            for keyword in ['split', 'filter', 'normalize']:
                assert keyword not in action


def test_SetTabPage_init(qtbot):
    _, _ = widget_setup(qtbot, SetTabPage, 'set name')
    _, _ = widget_setup(qtbot, SetTabPage, 'set name', {'aa', 'bb', 'cc', 'dd'})


def test_SetTabPage_from_set(qtbot):
    set_name = 'table name'
    qtbot, window = widget_setup(qtbot, SetTabPage, set_name)
    assert window.is_empty()

    obj = {'abc', 'def', 'ghi', 'jkl'}
    window.update_gene_set(obj)

    assert not window.is_empty()
    assert window.obj().gene_set == obj
    assert window.obj_type() == enrichment.FeatureSet
    assert window.name == set_name


def test_SetTabPage_cache(qtbot, monkeypatch):
    s = {'abc', 'def', 'ghi', '123'}
    qtbot, window = widget_setup(qtbot, SetTabPage, 'set name', s)
    cached = []

    def mock_cache(obj, filename):
        assert isinstance(obj, set)
        assert obj == s
        cached.append(True)

    monkeypatch.setattr(io, 'cache_gui_file', mock_cache)

    fname = window.cache()
    assert fname.endswith('.txt')
    assert len(fname) == 44

    time.sleep(0.01)
    fname2 = window.cache()
    assert cached == [True, True]
    assert fname != fname2


def test_SetTabPage_obj_properties(qtbot):
    s = {'abc', 'def', 'ghi', '123'}
    qtbot, window = widget_setup(qtbot, SetTabPage, 'set name', s)
    assert window.obj_properties() == {}


def test_SetTabPage_rename(qtbot, settabpage_with_undo_stack):
    window, stack = settabpage_with_undo_stack
    new_name = 'my new set name'
    prev_name = window.name
    qtbot.keyClicks(window.overview_widgets['table_name'], new_name)
    with qtbot.waitSignal(window.tabNameChange) as blocker:
        qtbot.mouseClick(window.overview_widgets['rename_button'], LEFT_CLICK)
    assert blocker.args[0] == new_name
    assert str(window.gene_set.set_name) == new_name
    assert new_name in window.overview_widgets['table_name_label'].text()
    assert prev_name not in window.overview_widgets['table_name_label'].text()
    assert window.name == new_name


def test_SetTabPage_undo_rename(qtbot, settabpage_with_undo_stack):
    window, stack = settabpage_with_undo_stack
    new_name = 'my new set name'
    prev_name = window.name
    qtbot.keyClicks(window.overview_widgets['table_name'], new_name)
    with qtbot.waitSignal(window.tabNameChange) as blocker:
        qtbot.mouseClick(window.overview_widgets['rename_button'], LEFT_CLICK)
    assert window.name == new_name

    with qtbot.waitSignal(window.tabNameChange) as blocker:
        stack.undo()
    assert blocker.args[0] == prev_name
    assert str(window.gene_set.set_name) == prev_name
    assert prev_name in window.overview_widgets['table_name_label'].text()
    assert new_name not in window.overview_widgets['table_name_label'].text()
    assert window.name == prev_name

    with qtbot.waitSignal(window.tabNameChange) as blocker:
        stack.redo()
    assert blocker.args[0] == new_name
    assert str(window.gene_set.set_name) == new_name
    assert new_name in window.overview_widgets['table_name_label'].text()
    assert prev_name not in window.overview_widgets['table_name_label'].text()
    assert window.name == new_name


def test_SetTabPage_save_gene_set(qtbot, monkeypatch):
    fname = 'my filename.txt'
    saved = []

    def mock_get_save_name(*args, **kwargs):
        saved.append('got name')
        return fname, '.txt'

    def mock_save_txt(self, filename):
        saved.append(filename)

    monkeypatch.setattr(QtWidgets.QFileDialog, 'getSaveFileName', mock_get_save_name)
    monkeypatch.setattr(enrichment.FeatureSet, 'save_txt', mock_save_txt)

    qtbot, window = widget_setup(qtbot, SetTabPage, 'set name', {'1', '2', '3'})
    qtbot.mouseClick(window.overview_widgets['save_button'], LEFT_CLICK)

    assert saved == ['got name', fname]


def test_SetTabPage_view_full_set(qtbot):
    qtbot, window = widget_setup(qtbot, SetTabPage, 'set name', {'a', 'b', 'c', 'd'})
    qtbot.mouseClick(window.overview_widgets['view_button'], LEFT_CLICK)
    assert isinstance(window.overview_widgets['full_table_view'], gui_windows.GeneSetView)

    view = window.overview_widgets['full_table_view'].data_view
    genes_in_view = {view.item(i).text() for i in range(view.count())}
    assert genes_in_view == window.obj().gene_set


@pytest.mark.parametrize('exc_params', [None, ['self', 'other']])
@pytest.mark.parametrize('pipeline_mode', [True, False])
def test_FuncTypeStack_init(qtbot, pipeline_mode, exc_params):
    _ = widget_setup(qtbot, FuncTypeStack, ['filter_biotype_from_ref_table', 'number_filters', 'describe'],
                     filtering.Filter('tests/test_files/test_deseq.csv'),
                     additional_excluded_params=exc_params, pipeline_mode=pipeline_mode)


def test_CreatePipelineWindow_init(qtbot):
    _, _ = widget_setup(qtbot, CreatePipelineWindow)


def test_CreatePipelineWindow_from_pipeline(qtbot):
    name = 'my pipeline name'
    pipeline = filtering.Pipeline.import_pipeline('tests/test_files/test_pipeline.yaml')
    qtbot, window = widget_setup(qtbot, CreatePipelineWindow.start_from_pipeline, pipeline, name)
    assert window.pipeline == pipeline
    assert window._get_pipeline_name() == name


@pytest.mark.parametrize('pipeline_type,exp_pipeline,exp_filter_type', [
    ('Differential expression', filtering.Pipeline, filtering.DESeqFilter),
    ('Other table', filtering.Pipeline, filtering.Filter),
    ('Sequence files (single-end)', fastq.SingleEndPipeline, False),
    ('Sequence files (paired-end)', fastq.PairedEndPipeline, False)
])
def test_CreatePipelineWindow_create_pipeline(qtbot, monkeypatch, pipeline_type, exp_pipeline, exp_filter_type):
    monkeypatch.setattr(QtWidgets.QMessageBox, "question", lambda *args: QtWidgets.QMessageBox.StandardButton.Yes)
    pipeline_name = 'my pipeline name'
    qtbot, window = widget_setup(qtbot, CreatePipelineWindow)
    window.basic_widgets['pipeline_name'].clear()
    qtbot.keyClicks(window.basic_widgets['pipeline_name'], pipeline_name)
    window.basic_widgets['table_type_combo'].setCurrentText(pipeline_type)
    qtbot.mouseClick(window.basic_widgets['start_button'], LEFT_CLICK)

    assert not window.basic_group.isVisible()
    assert isinstance(window.pipeline, exp_pipeline)
    assert window._get_pipeline_name() == pipeline_name
    if exp_filter_type:
        assert window.pipeline.filter_type == exp_filter_type


def test_CreatePipelineWindow_add_function(qtbot, monkeypatch):
    pipeline_truth = filtering.Pipeline('DESeqFilter')
    pipeline_truth.add_function('split_fold_change_direction')

    monkeypatch.setattr(QtWidgets.QMessageBox, "question", lambda *args: QtWidgets.QMessageBox.StandardButton.Yes)

    qtbot, window = widget_setup(qtbot, CreatePipelineWindow)
    window.basic_widgets['pipeline_name'].clear()
    qtbot.keyClicks(window.basic_widgets['pipeline_name'], 'pipeline_name')
    qtbot.keyClicks(window.basic_widgets['table_type_combo'], 'Differential expression')
    qtbot.mouseClick(window.basic_widgets['start_button'], LEFT_CLICK)

    qtbot.mouseClick(window.stack_buttons[0], LEFT_CLICK)
    qtbot.keyClicks(window.stack.currentWidget().func_combo,
                    filtering.DESeqFilter.split_fold_change_direction.readable_name)
    qtbot.mouseClick(window.apply_button, LEFT_CLICK)

    assert window.pipeline == pipeline_truth


def test_CreatePipelineWindow_remove_function(qtbot, monkeypatch):
    warned = []
    monkeypatch.setattr(QtWidgets.QMessageBox, "question", lambda *args: QtWidgets.QMessageBox.StandardButton.Yes)
    monkeypatch.setattr(QtWidgets.QMessageBox, 'exec', lambda *args, **kwargs: warned.append(True))

    qtbot, window = widget_setup(qtbot, CreatePipelineWindow)
    window.basic_widgets['pipeline_name'].clear()
    qtbot.keyClicks(window.basic_widgets['pipeline_name'], 'pipeline_name')
    qtbot.keyClicks(window.basic_widgets['table_type_combo'], 'Differential expression')
    qtbot.mouseClick(window.basic_widgets['start_button'], LEFT_CLICK)

    qtbot.mouseClick(window.stack_buttons[0], LEFT_CLICK)
    qtbot.keyClicks(window.stack.currentWidget().func_combo,
                    filtering.DESeqFilter.split_fold_change_direction.readable_name)
    qtbot.mouseClick(window.apply_button, LEFT_CLICK)

    assert len(window.pipeline) == 1

    qtbot.mouseClick(window.overview_widgets['remove_button'], LEFT_CLICK)
    assert len(window.pipeline) == 0
    assert warned == []

    qtbot.mouseClick(window.overview_widgets['remove_button'], LEFT_CLICK)
    assert len(window.pipeline) == 0
    assert warned == [True]


def test_CreatePipelineWindow_add_function_with_args(qtbot, monkeypatch):
    pipeline_truth = filtering.Pipeline('DESeqFilter')
    pipeline_truth.add_function('filter_significant', alpha=0.01, opposite=True)

    monkeypatch.setattr(QtWidgets.QMessageBox, "question", lambda *args: QtWidgets.QMessageBox.StandardButton.Yes)

    qtbot, window = widget_setup(qtbot, CreatePipelineWindow)
    window.basic_widgets['pipeline_name'].clear()
    qtbot.keyClicks(window.basic_widgets['pipeline_name'], 'pipeline_name')
    qtbot.keyClicks(window.basic_widgets['table_type_combo'], 'Differential expression')
    qtbot.mouseClick(window.basic_widgets['start_button'], LEFT_CLICK)

    qtbot.mouseClick(window.stack_buttons[0], LEFT_CLICK)
    window.stack.currentWidget().func_combo.setCurrentText(filtering.DESeqFilter.filter_significant.readable_name)
    window.stack.currentWidget().parameter_widgets['alpha'].clear()
    qtbot.keyClicks(window.stack.currentWidget().parameter_widgets['alpha'], '0.01')
    qtbot.mouseClick(window.stack.currentWidget().parameter_widgets['opposite'].switch, LEFT_CLICK)
    qtbot.mouseClick(window.apply_button, LEFT_CLICK)
    assert window.pipeline == pipeline_truth

    # add a second function
    pipeline_truth.add_function('split_fold_change_direction')

    window.stack.currentWidget().func_combo.setCurrentText(
        filtering.DESeqFilter.split_fold_change_direction.readable_name)
    qtbot.mouseClick(window.apply_button, LEFT_CLICK)
    assert window.pipeline == pipeline_truth


def test_CreatePipelineWindow_save_pipeline(qtbot, monkeypatch):
    pipeline_truth = filtering.Pipeline('DESeqFilter')
    pipeline_truth.add_function('describe', percentiles=[0.01, 0.25, 0.5, 0.75, 0.99])
    pipeline_name = 'my pipeline name'

    monkeypatch.setattr(QtWidgets.QMessageBox, "question", lambda *args: QtWidgets.QMessageBox.StandardButton.Yes)

    qtbot, window = widget_setup(qtbot, CreatePipelineWindow)
    window.basic_widgets['pipeline_name'].clear()
    qtbot.keyClicks(window.basic_widgets['pipeline_name'], pipeline_name)
    qtbot.keyClicks(window.basic_widgets['table_type_combo'], 'Differential expression')
    qtbot.mouseClick(window.basic_widgets['start_button'], LEFT_CLICK)

    qtbot.mouseClick(window.stack_buttons[2], LEFT_CLICK)
    qtbot.keyClicks(window.stack.currentWidget().func_combo, filtering.Filter.describe.readable_name)
    qtbot.mouseClick(window.apply_button, LEFT_CLICK)

    with qtbot.waitSignal(window.pipelineSaved) as blocker:
        qtbot.mouseClick(window.overview_widgets['save_button'], LEFT_CLICK)
    assert blocker.args[0] == pipeline_name
    assert blocker.args[1] == pipeline_truth


def test_CreatePipelineWindow_export_pipeline(qtbot, monkeypatch):
    pipeline_truth = filtering.Pipeline('DESeqFilter')
    pipeline_truth.add_function('describe', percentiles=[0.01, 0.25, 0.5, 0.75, 0.99])
    pipeline_name = 'my pipeline name'

    monkeypatch.setattr(QtWidgets.QMessageBox, "question", lambda *args: QtWidgets.QMessageBox.StandardButton.Yes)

    qtbot, window = widget_setup(qtbot, CreatePipelineWindow)
    window.basic_widgets['pipeline_name'].clear()
    qtbot.keyClicks(window.basic_widgets['pipeline_name'], pipeline_name)
    qtbot.keyClicks(window.basic_widgets['table_type_combo'], 'Differential expression')
    qtbot.mouseClick(window.basic_widgets['start_button'], LEFT_CLICK)

    qtbot.mouseClick(window.stack_buttons[2], LEFT_CLICK)
    qtbot.keyClicks(window.stack.currentWidget().func_combo, filtering.Filter.describe.readable_name)
    qtbot.mouseClick(window.apply_button, LEFT_CLICK)

    with qtbot.waitSignal(window.pipelineExported) as blocker:
        qtbot.mouseClick(window.overview_widgets['export_button'], LEFT_CLICK)
    assert blocker.args[0] == pipeline_name
    assert blocker.args[1] == pipeline_truth


def test_MultiKeepWindow_init(multi_keep_window):
    _ = multi_keep_window


@pytest.mark.parametrize('keep_ops,name_ops,truth', [
    ({}, {}, []),
    ({'all': True}, {}, [filtering.DESeqFilter('tests/test_files/test_deseq.csv'),
                         filtering.CountFilter('tests/test_files/counted.tsv'),
                         filtering.Filter('tests/test_files/test_deseq_biotype.csv')]),
    ({'test_deseq': True, 'test_deseq_biotype': True}, {},
     [filtering.DESeqFilter('tests/test_files/test_deseq.csv'),
      filtering.Filter('tests/test_files/test_deseq_biotype.csv')]),
    ({'test_deseq': True, 'test_deseq_biotype': True},
     {'test_deseq': 'new name1', 'test_deseq_biotype': 'new name 2', 'counted': 'new name 3'},
     [filtering.DESeqFilter('tests/test_files/test_deseq.csv'),
      filtering.Filter('tests/test_files/test_deseq_biotype.csv')])
])
def test_MultiKeepWindow_result(qtbot, multi_keep_window, keep_ops, name_ops, truth):
    for ind, op in keep_ops.items():
        if ind == 'all':
            qtbot.mouseClick(multi_keep_window.select_all, LEFT_CLICK)
        else:
            qtbot.mouseClick(multi_keep_window.keep_marks[ind], LEFT_CLICK)
    for ind, op in name_ops.items():
        qtbot.keyClicks(multi_keep_window.names[ind], op)

        for item in truth:
            if item.fname.stem == ind:
                item.fname = Path(op)

    assert multi_keep_window.result() == truth


def test_MultiOpenWindow_init(multi_open_window):
    _ = multi_open_window


@pytest.mark.parametrize('path_ops,type_ops,name_ops,truth', [
    ({}, {}, {}, ({'tests/counted.csv': 'tests/counted.csv', 'tests/test_deseq.csv': 'tests/test_deseq.csv',
                   'tests/counted.tsv': 'tests/counted.tsv'},
                  {'tests/counted.csv': 'Other table', 'tests/test_deseq.csv': 'Other table',
                   'tests/counted.tsv': 'Other table'},
                  {'tests/counted.csv': '', 'tests/test_deseq.csv': '', 'tests/counted.tsv': ''},
                  {'tests/counted.csv': {'drop_columns': []},
                   'tests/counted.tsv': {'drop_columns': []},
                   'tests/test_deseq.csv': {'drop_columns': []}})),
    (
        {}, {}, {1: 'new name', 2: 'second new name'},
        ({'tests/counted.csv': 'tests/counted.csv', 'tests/test_deseq.csv': 'tests/test_deseq.csv',
          'tests/counted.tsv': 'tests/counted.tsv'},
         {'tests/counted.csv': 'Other table', 'tests/test_deseq.csv': 'Other table',
          'tests/counted.tsv': 'Other table'},
         {'tests/counted.csv': '', 'tests/test_deseq.csv': 'new name', 'tests/counted.tsv': 'second new name'},
         {'tests/counted.csv': {'drop_columns': []},
          'tests/counted.tsv': {'drop_columns': []},
          'tests/test_deseq.csv': {'drop_columns': []}})),

    ({}, {0: 'Count matrix', 1: 'Differential expression'}, {},
     ({'tests/counted.csv': 'tests/counted.csv', 'tests/test_deseq.csv': 'tests/test_deseq.csv',
       'tests/counted.tsv': 'tests/counted.tsv'},
      {'tests/counted.csv': 'Count matrix', 'tests/test_deseq.csv': 'Differential expression',
       'tests/counted.tsv': 'Other table'},
      {'tests/counted.csv': '', 'tests/test_deseq.csv': '', 'tests/counted.tsv': ''},
      {'tests/counted.csv': {'drop_columns': [], 'is_normalized': False},
       'tests/counted.tsv': {'drop_columns': []},
       'tests/test_deseq.csv': {'drop_columns': [],
                                'log2fc_col': 'log2FoldChange',
                                'padj_col': 'padj',
                                'pval_col': 'pvalue'}})),

    ({1: 'tests/big_counted.csv'}, {}, {},
     ({'tests/counted.csv': 'tests/counted.csv', 'tests/test_deseq.csv': 'tests/big_counted.csv',
       'tests/counted.tsv': 'tests/counted.tsv'},
      {'tests/counted.csv': 'Other table', 'tests/test_deseq.csv': 'Other table', 'tests/counted.tsv': 'Other table'},
      {'tests/counted.csv': '', 'tests/test_deseq.csv': '', 'tests/counted.tsv': ''},
      {'tests/counted.csv': {'drop_columns': []},
       'tests/counted.tsv': {'drop_columns': []},
       'tests/test_deseq.csv': {'drop_columns': []}})),

    ({}, {0: 'Count matrix', 1: 'Differential expression'}, {1: 'new name', 2: 'second new name'},
     ({'tests/counted.csv': 'tests/counted.csv', 'tests/test_deseq.csv': 'tests/test_deseq.csv',
       'tests/counted.tsv': 'tests/counted.tsv'},
      {'tests/counted.csv': 'Count matrix', 'tests/test_deseq.csv': 'Differential expression',
       'tests/counted.tsv': 'Other table'},
      {'tests/counted.csv': '', 'tests/test_deseq.csv': 'new name', 'tests/counted.tsv': 'second new name'},
      {'tests/counted.csv': {'drop_columns': [], 'is_normalized': False},
       'tests/counted.tsv': {'drop_columns': []},
       'tests/test_deseq.csv': {'drop_columns': [],
                                'log2fc_col': 'log2FoldChange',
                                'padj_col': 'padj',
                                'pval_col': 'pvalue'}})),
])
def test_MultiOpenWindow_result(qtbot, multi_open_window, path_ops, type_ops, name_ops, truth):
    files = multi_open_window_files
    for ind, op in path_ops.items():
        multi_open_window.paths[files[ind]].clear()
        qtbot.keyClicks(multi_open_window.paths[files[ind]].file_path, op)
    for ind, op in type_ops.items():
        qtbot.keyClicks(multi_open_window.table_types[files[ind]], op)
    for ind, op in name_ops.items():
        qtbot.keyClicks(multi_open_window.names[files[ind]], op)

    assert multi_open_window.result() == truth


def test_ReactiveTabWidget_init(tab_widget):
    _ = tab_widget


def test_ReactiveTabWidget_new_tab_from_item(qtbot, tab_widget):
    with qtbot.waitSignal(tab_widget.newTabFromSet) as blocker:
        tab_widget.new_tab_from_item({'a', 'b', 'c', 'd'}, 'my name', 1)
    assert blocker.args == [{'a', 'b', 'c', 'd'}, 1, 'my name']

    with qtbot.waitSignal(tab_widget.newTabFromFilter) as blocker:
        tab_widget.new_tab_from_item(filtering.CountFilter('tests/test_files/counted.tsv'), 'my name', -1)
    assert blocker.args == [filtering.CountFilter('tests/test_files/counted.tsv'), -1, 'my name']

    with pytest.raises(TypeError):
        with qtbot.assertNotEmitted(tab_widget.newTabFromSet):
            with qtbot.assertNotEmitted(tab_widget.newTabFromFilter):
                tab_widget.new_tab_from_item(['invalid item type'], 'my name', 1)


class MockTab(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.tab_id = -1


def test_ReactiveTabWidget_remove_tab(qtbot, tab_widget):
    qtbot, widget = widget_setup(qtbot, MockTab)
    tab_widget.setCornerWidget(widget, QtCore.Qt.Corner.TopRightCorner)
    for i in range(3):
        qtbot, widget = widget_setup(qtbot, MockTab)
        tab_widget.addTab(widget, 'name')

    for i in range(3):
        tab_widget.removeTab(0)

    assert tab_widget.count() == 0


def test_ReactiveTabWidget_left_click(qtbot, tab_widget, monkeypatch):
    super_triggered = []

    def mock_mouse_press_event(self, event):
        super_triggered.append(True)

    monkeypatch.setattr(QtWidgets.QTabWidget, 'mousePressEvent', mock_mouse_press_event)

    for i in range(3):
        qtbot.mouseClick(tab_widget, LEFT_CLICK)
        assert super_triggered == [True] * (i + 1)


def test_ReactiveTabWidget_right_click(qtbot, tab_widget, monkeypatch):
    super_triggered = []

    def mock_mouse_press_event(self, event):
        super_triggered.append(True)

    monkeypatch.setattr(QtWidgets.QTabWidget, 'mousePressEvent', mock_mouse_press_event)

    for i in range(3):
        # with qtbot.waitSignal(tab_widget.tabRightClicked) as blocker:
        qtbot.mouseClick(tab_widget, RIGHT_CLICK)
        assert super_triggered == []

    for i in range(3):
        qtbot, widget = widget_setup(qtbot, QtWidgets.QWidget)
        tab_widget.addTab(widget, 'name')

        for j in range(i + 1):
            with qtbot.waitSignal(tab_widget.tabRightClicked) as blocker:
                qtbot.mouseClick(tab_widget, RIGHT_CLICK, pos=tab_widget.tabBar().tabRect(j).center())
            assert super_triggered == []
            assert blocker.args[0] == j


def test_MainWindow_init(main_window):
    _ = main_window


def test_MainWindow_add_new_tab(main_window):
    main_window.new_table_action.trigger()
    assert main_window.tabs.count() == 2


@pytest.mark.parametrize('ind', range(6))
def test_MainWindow_add_new_tab_at(main_window_with_tabs, ind):
    main_window_with_tabs.add_new_tab_at(ind)
    assert main_window_with_tabs.tabs.count() == 6
    assert main_window_with_tabs.tabs.currentIndex() == ind
    assert main_window_with_tabs.tabs.currentWidget().is_empty()


def test_MainWindow_close_current_tab(main_window_with_tabs):
    current_tab_name = main_window_with_tabs.tabs.currentWidget().get_tab_name()
    main_window_with_tabs.close_current_action.trigger()
    assert main_window_with_tabs.tabs.count() == 4
    assert current_tab_name not in main_window_with_tabs.get_available_objects()
    assert main_window_with_tabs.tabs.currentWidget().get_tab_name() != current_tab_name


@pytest.mark.parametrize('ind', range(5))
def test_MainWindow_close_tabs_to_the_right(main_window_with_tabs, ind):
    tab_name = main_window_with_tabs.tabs.widget(ind).get_tab_name()
    all_names = [main_window_with_tabs.tabs.widget(i).get_tab_name() for i in range(5)]
    main_window_with_tabs.close_tabs_to_the_right(ind)
    assert main_window_with_tabs.tabs.count() == ind + 1
    assert tab_name in main_window_with_tabs.get_available_objects()
    for i in range(ind, 5):
        if i <= ind:
            assert all_names[i] in main_window_with_tabs.get_available_objects()
        else:
            assert all_names[i] not in main_window_with_tabs.get_available_objects()


@pytest.mark.parametrize('ind', range(5))
def test_MainWindow_close_tabs_to_the_left(main_window_with_tabs, ind):
    tab_name = main_window_with_tabs.tabs.widget(ind).get_tab_name()
    all_names = [main_window_with_tabs.tabs.widget(i).get_tab_name() for i in range(5)]
    main_window_with_tabs.close_tabs_to_the_left(ind)
    assert main_window_with_tabs.tabs.count() == 5 - ind
    assert tab_name in main_window_with_tabs.get_available_objects()
    for i in range(ind, 5):
        if i >= ind:
            assert all_names[i] in main_window_with_tabs.get_available_objects()
        else:
            assert all_names[i] not in main_window_with_tabs.get_available_objects()


@pytest.mark.parametrize('ind', range(5))
def test_MainWindow_close_other_tabs(main_window_with_tabs, ind):
    tab_name = main_window_with_tabs.tabs.widget(ind).get_tab_name()
    all_names = [main_window_with_tabs.tabs.widget(i).get_tab_name() for i in range(5)]
    main_window_with_tabs.close_other_tabs(ind)
    assert main_window_with_tabs.tabs.count() == 1
    assert tab_name in main_window_with_tabs.get_available_objects()
    for i in range(ind, 5):
        if i != ind:
            assert all_names[i] not in main_window_with_tabs.get_available_objects()


@pytest.mark.parametrize('ind', range(5))
def test_MainWindow_close_tab(main_window_with_tabs, ind):
    tab_name = main_window_with_tabs.tabs.widget(ind).get_tab_name()
    main_window_with_tabs.close_tab(ind)
    assert main_window_with_tabs.tabs.count() == 4
    assert tab_name not in main_window_with_tabs.get_available_objects()
    assert main_window_with_tabs.tabs.currentWidget().get_tab_name() != tab_name


def test_MainWindow_close_tab_undo(main_window_with_tabs):
    current_tab_name = main_window_with_tabs.tabs.currentWidget().get_tab_name()
    current_obj = copy.copy(main_window_with_tabs.tabs.currentWidget().obj())
    main_window_with_tabs.close_current_action.trigger()
    assert main_window_with_tabs.tabs.count() == 4

    main_window_with_tabs.restore_tab_action.trigger()

    assert main_window_with_tabs.tabs.count() == 5
    assert current_tab_name in main_window_with_tabs.get_available_objects()
    assert main_window_with_tabs.tabs.currentWidget().get_tab_name() == current_tab_name
    assert main_window_with_tabs.tabs.currentWidget().obj() == current_obj


def test_MainWindow_sort_tabs_by_type(main_window_with_tabs):
    truth = ['counted', 'test_deseq', 'my table', 'counted_6cols', 'majority_vote_intersection output']
    main_window_with_tabs.sort_tabs_by_type()
    for i, name in enumerate(truth):
        assert main_window_with_tabs.tabs.widget(i).get_tab_name() == name


def test_MainWindow_sort_tabs_by_n_features(main_window_with_tabs):
    truth = ['test_deseq', 'my table', 'majority_vote_intersection output', 'counted_6cols', 'counted']
    main_window_with_tabs.sort_tabs_by_name()
    main_window_with_tabs.sort_tabs_by_n_features()
    for i, name in enumerate(truth):
        assert main_window_with_tabs.tabs.widget(i).get_tab_name() == name


def test_MainWindow_sort_tabs_by_creation_time(main_window_with_tabs):
    truth = [main_window_with_tabs.tabs.widget(i).get_tab_name() for i in range(5)]
    main_window_with_tabs.sort_tabs_by_name()
    main_window_with_tabs.sort_tabs_by_creation_time()
    for i, name in enumerate(truth):
        assert main_window_with_tabs.tabs.widget(i).get_tab_name() == name


def test_MainWindow_sort_tabs_by_name(main_window_with_tabs):
    truth = ['counted', 'counted_6cols', 'majority_vote_intersection output', 'my table', 'test_deseq']
    main_window_with_tabs.sort_tabs_by_name()
    for i, name in enumerate(truth):
        assert main_window_with_tabs.tabs.widget(i).get_tab_name() == name


def test_MainWindow_reverse_order(main_window_with_tabs):
    truth = reversed(['counted', 'counted_6cols', 'majority_vote_intersection output', 'my table', 'test_deseq'])
    main_window_with_tabs.sort_tabs_by_name()
    main_window_with_tabs.sort_reverse()
    for i, name in enumerate(truth):
        assert main_window_with_tabs.tabs.widget(i).get_tab_name() == name


def test_MainWindow_rename_tab(qtbot, main_window_with_tabs):
    new_name = 'my new tab name'

    qtbot.keyClicks(main_window_with_tabs.tabs.currentWidget().overview_widgets['table_name'], new_name)
    qtbot.mouseClick(main_window_with_tabs.tabs.currentWidget().overview_widgets['rename_button'], LEFT_CLICK)

    assert main_window_with_tabs.tabs.currentWidget().get_tab_name() == new_name
    assert main_window_with_tabs.tabs.tabText(main_window_with_tabs.tabs.currentIndex()).rstrip('*') == new_name


@pytest.mark.parametrize('normalize', [False, True])
def test_MainWindow_new_table_from_folder_htseqcount(main_window_with_tabs, normalize, monkeypatch):
    dir_path = 'tests/test_files/test_count_from_folder'

    def mock_get_dir(*args, **kwargs):
        return dir_path

    def mock_question(*args, **kwargs):
        if args[1] == 'Close program':
            return QtWidgets.QMessageBox.StandardButton.Yes
        return QtWidgets.QMessageBox.StandardButton.Yes if normalize else QtWidgets.QMessageBox.StandardButton.No

    monkeypatch.setattr(QtWidgets.QFileDialog, 'getExistingDirectory', mock_get_dir)
    monkeypatch.setattr(QtWidgets.QMessageBox, 'question', mock_question)

    main_window_with_tabs.new_table_from_folder_htseq_action.trigger()
    assert main_window_with_tabs.tabs.count() == 6
    assert main_window_with_tabs.tabs.currentWidget().obj() == filtering.CountFilter.from_folder_htseqcount(dir_path,
                                                                                                            normalize)


def test_MainWindow_new_table_from_folder(main_window_with_tabs, monkeypatch):
    dir_path = 'tests/test_files/test_count_from_folder'

    def mock_get_dir(*args, **kwargs):
        return dir_path

    monkeypatch.setattr(QtWidgets.QFileDialog, 'getExistingDirectory', mock_get_dir)

    main_window_with_tabs.new_table_from_folder_action.trigger()
    assert main_window_with_tabs.tabs.count() == 6
    assert main_window_with_tabs.tabs.currentWidget().obj() == filtering.CountFilter.from_folder(dir_path)


def test_MainWindow_multiple_new_tables(main_window, monkeypatch):
    filenames = ['tests/test_files/test_deseq.csv', 'tests/test_files/counted.tsv', 'tests/test_files/fc_1.csv']
    objs_truth = [filtering.DESeqFilter(filenames[0]), filtering.CountFilter(filenames[1], drop_columns='cond2'),
                  filtering.FoldChangeFilter(filenames[2], 'num', 'denom')]
    objs_truth[1].fname = Path('new name')

    def mock_exec(self):
        return True

    def mock_multi_selection_result(self, _):
        return filenames, ''

    def mock_multi_open_result(self):
        filename_dict = {fname: fname for fname in filenames}
        types_dict = {filenames[0]: 'Differential expression', filenames[1]: 'Count matrix',
                      filenames[2]: 'Fold change'}
        names_dict = {filenames[0]: '', filenames[1]: 'new name', filenames[2]: ''}
        kwargs_dict = {filenames[0]: {}, filenames[1]: {'drop_columns': ['cond2']},
                       filenames[2]: {'numerator_name': 'num', 'denominator_name': 'denom'}}
        return filename_dict, types_dict, names_dict, kwargs_dict

    monkeypatch.setattr(MultiOpenWindow, 'exec', mock_exec)
    monkeypatch.setattr(QtWidgets.QFileDialog, 'getOpenFileNames', mock_multi_selection_result)
    monkeypatch.setattr(MultiOpenWindow, 'result', mock_multi_open_result)
    main_window.new_multiple_action.trigger()

    assert main_window.tabs.count() == 3
    for i in range(3):
        assert main_window.tabs.widget(i).obj() == objs_truth[i]


def test_MainWindow_export_pipeline(use_temp_settings_file, main_window, monkeypatch):
    fname = 'path/to/pipeline.yaml'
    pipeline_exported = []
    pipeline_truth = filtering.Pipeline.import_pipeline('tests/test_files/test_pipeline.yaml')

    def mock_export(pipeline, filename):
        assert filename == fname
        assert pipeline == pipeline_truth
        pipeline_exported.append(True)

    monkeypatch.setattr(QtWidgets.QInputDialog, 'getItem', lambda *args, **kwargs: ('test_pipeline', True))
    monkeypatch.setattr(QtWidgets.QFileDialog, 'getSaveFileName', lambda *args, **kwargs: (fname, '.yaml'))
    monkeypatch.setattr(filtering.Pipeline, 'export_pipeline', mock_export)
    main_window.pipelines['test_pipeline'] = (pipeline_truth, 1)

    main_window.export_pipeline_action.trigger()
    assert pipeline_exported == [True]


@pytest.mark.parametrize('name,exp_class', [('test_pipeline', filtering.Pipeline),
                                            ('test_single_end_pipeline', fastq.SingleEndPipeline),
                                            ('test_paired_end_pipeline', fastq.PairedEndPipeline)
                                            ])
def test_MainWindow_import_pipeline(use_temp_settings_file, main_window, monkeypatch, name, exp_class):
    fname = f'tests/test_files/{name}.yaml'
    monkeypatch.setattr(QtWidgets.QFileDialog, 'getOpenFileName', lambda *args, **kwargs: (fname, '.yaml'))
    main_window.import_pipeline_action.trigger()
    main_window.pipelines[name] = (main_window.pipelines[name][0], -1)
    assert main_window.pipelines == OrderedDict({name: (exp_class.import_pipeline(fname), -1)})


def test_MainWindow_import_multiple_gene_sets(main_window_with_tabs, monkeypatch):
    filenames = ['tests/test_files/counted.tsv', 'tests/test_files/test_deseq.csv',
                 'tests/test_files/test_gene_set.txt']
    truth = []
    for filename in filenames:
        if filename.endswith('.txt'):
            with open(filename) as f:
                truth_set = set(f.read().split())
        else:
            df = io.load_table(filename)
            truth_set = parsing.data_to_set(df.select(pl.first()))
        truth_featureset = enrichment.FeatureSet(truth_set, Path(filename).stem)
        truth.append(truth_featureset)

    def mock_multi_selection_result(self, _):
        return filenames, ''

    monkeypatch.setattr(QtWidgets.QFileDialog, 'getOpenFileNames', mock_multi_selection_result)
    main_window_with_tabs.import_multiple_sets_action.trigger()
    assert main_window_with_tabs.tabs.count() == 5 + len(filenames)
    assert isinstance(main_window_with_tabs.tabs.currentWidget(), SetTabPage)
    for i in range(3):
        assert main_window_with_tabs.tabs.widget(i + 5).obj() == truth[i]


@pytest.mark.parametrize('filename', ['tests/test_files/counted.tsv', 'tests/test_files/test_deseq.csv',
                                      'tests/test_files/test_gene_set.txt'])
def test_MainWindow_import_gene_set(main_window_with_tabs, monkeypatch, filename):
    if filename.endswith('.txt'):
        with open(filename) as f:
            truth_set = enrichment.FeatureSet(set(f.read().split()), Path(filename).stem)
    else:
        df = io.load_table(filename)
        truth_set = enrichment.FeatureSet(parsing.data_to_set(df.select(pl.first())), Path(filename).stem)

    def mock_get_file(*args, **kwargs):
        return filename, '.csv'

    monkeypatch.setattr(QtWidgets.QFileDialog, 'getOpenFileName', mock_get_file)
    main_window_with_tabs.import_set_action.trigger()
    assert main_window_with_tabs.tabs.count() == 6
    assert isinstance(main_window_with_tabs.tabs.currentWidget(), SetTabPage)
    assert main_window_with_tabs.tabs.currentWidget().obj() == truth_set


@pytest.mark.parametrize('ind', range(5))
def test_MainWindow_export_gene_set(use_temp_settings_file, main_window_with_tabs, monkeypatch, ind):
    save_path = 'test/save/path.csv'
    save_called = []

    def mock_save(gene_set, filename):
        assert gene_set == gene_set_truth
        assert filename == save_path
        save_called.append(True)

    def mock_get_file(*args, **kwargs):
        return save_path, '.csv'

    monkeypatch.setattr(io, 'save_gene_set', mock_save)
    monkeypatch.setattr(QtWidgets.QFileDialog, 'getSaveFileName', mock_get_file)
    main_window_with_tabs.tabs.setCurrentIndex(ind)
    obj = main_window_with_tabs.tabs.currentWidget().obj()
    if isinstance(obj, set):
        gene_set_truth = obj
    else:
        gene_set_truth = obj.index_set
    main_window_with_tabs.export_set_action.trigger()
    assert save_called == [True]


@pytest.mark.parametrize('ind,gene_set', [
    (4, {'WBGene00007069', 'WBGene00007064', 'WBGene00007063', 'WBGene00007074', 'WBGene00077502',
         'WBGene00007076', 'WBGene00044951', 'WBGene00007067', 'WBGene00044022', 'WBGene00043990',
         'WBGene00077504', 'WBGene00007066', 'WBGene00043987', 'WBGene00014997', 'WBGene00043989',
         'WBGene00007071', 'WBGene00007075', 'WBGene00007078', 'WBGene00007079', 'WBGene00007077',
         'WBGene00077503', 'WBGene00043988'}),
    (1, {'WBGene00007066', 'WBGene00007076', 'WBGene00044022', 'WBGene00007067', 'WBGene00043987',
         'WBGene00007077', 'WBGene00044951', 'WBGene00007075', 'WBGene00077502', 'WBGene00077504',
         'WBGene00007069', 'WBGene00007079', 'WBGene00043990', 'WBGene00043989', 'WBGene00014997',
         'WBGene00007074', 'WBGene00007071', 'WBGene00077503', 'WBGene00007063', 'WBGene00043988',
         'WBGene00007064', 'WBGene00007078'})
])
def test_MainWindow_copy_gene_set(main_window_with_tabs, ind, gene_set):
    main_window_with_tabs.tabs.setCurrentIndex(1)
    main_window_with_tabs.copy_action.trigger()
    gene_ids = QtWidgets.QApplication.clipboard().text().split()
    assert len(gene_ids) == len(gene_set)
    assert sorted(gene_set) == sorted(gene_ids)


def test_MainWindow_add_pipeline(main_window, monkeypatch):
    window_opened = []
    monkeypatch.setattr(CreatePipelineWindow, 'exec', functools.partial(window_opened.append, True))

    main_window.new_pipeline_action.trigger()
    assert window_opened == [True]


def test_MainWindow_apply_function(qtbot, main_window_with_tabs):
    main_window_with_tabs.choose_tab_by_name('test_deseq')
    tab = main_window_with_tabs.tabs.currentWidget()
    orig = filtering.DESeqFilter('tests/test_files/test_deseq.csv')

    truth = tab.obj().filter_significant(0.01, opposite=True, inplace=False)
    tab.stack_buttons[0].click()
    tab.stack.currentWidget().func_combo.setCurrentText(filtering.DESeqFilter.filter_significant.readable_name)
    tab.stack.currentWidget().parameter_widgets['alpha'].clear()
    qtbot.keyClicks(tab.stack.currentWidget().parameter_widgets['alpha'], '0.01')
    qtbot.mouseClick(tab.stack.currentWidget().parameter_widgets['opposite'].switch, LEFT_CLICK)
    qtbot.mouseClick(tab.stack.currentWidget().parameter_widgets['inplace'].switch, LEFT_CLICK)
    with qtbot.waitSignal(tab.filterObjectCreated, timeout=10000) as blocker:
        qtbot.mouseClick(tab.apply_button, LEFT_CLICK)
    assert blocker.args[0] == truth
    assert np.allclose(tab.obj().df.drop(cs.first()), orig.df.drop(cs.first()))

    assert main_window_with_tabs.tabs.count() == 6


def test_MainWindow_get_available_objects(use_temp_settings_file, main_window_with_tabs):
    objs_truth = {'my table': filtering.FoldChangeFilter('tests/test_files/fc_1.csv', 'a', 'b'),
                  'counted': filtering.CountFilter('tests/test_files/counted.tsv'),
                  'counted_6cols': filtering.Filter('tests/test_files/counted_6cols.csv'),
                  'test_deseq': filtering.DESeqFilter('tests/test_files/test_deseq.csv'),
                  'majority_vote_intersection output': enrichment.FeatureSet(
                      {'WBGene00007069', 'WBGene00007064', 'WBGene00007063',
                       'WBGene00007074', 'WBGene00077502',
                       'WBGene00007076', 'WBGene00044951', 'WBGene00007067',
                       'WBGene00044022', 'WBGene00043990',
                       'WBGene00077504', 'WBGene00007066', 'WBGene00043987',
                       'WBGene00014997', 'WBGene00043989',
                       'WBGene00007071', 'WBGene00007075', 'WBGene00007078',
                       'WBGene00007079', 'WBGene00007077',
                       'WBGene00077503', 'WBGene00043988'}, 'majority_vote_intersection output')}
    objs_truth['my table'].fname = Path('my table')
    objs_truth['counted'].fname = Path('counted')
    objs_truth['counted_6cols'].fname = Path('counted_6cols')
    objs_truth['test_deseq'].fname = Path('test_deseq')

    res = main_window_with_tabs.get_available_objects()
    assert len(res) == len(objs_truth)
    for name in res.keys():
        assert isinstance(res[name][0], TabPage)
        assert (res[name][0].obj() == objs_truth[name]) or (
            np.allclose(np.squeeze(res[name][0].obj().df.drop(cs.first())),
                        np.squeeze(objs_truth[name].df.drop(cs.first()))) and (
                    res[name][0].obj().fname == objs_truth[name].fname))

        assert isinstance(res[name][1], QtGui.QIcon)


def test_MainWindow_choose_set_op(use_temp_settings_file, main_window, monkeypatch):
    def mock_init(self, available_objs, parent=None):
        assert available_objs == 'my available objects'
        QtWidgets.QWidget.__init__(self)

    monkeypatch.setattr(main_window, 'get_available_objects', lambda *args, **kwargs: 'my available objects')
    window_opened = []
    monkeypatch.setattr(SetOperationWindow, '__init__', mock_init)
    monkeypatch.setattr(SetOperationWindow, 'show', functools.partial(window_opened.append, True))

    main_window.set_op_action.trigger()
    assert window_opened == [True]


def test_MainWindow_visualize_gene_sets(use_temp_settings_file, main_window, monkeypatch):
    def mock_init(self, available_objs, parent=None):
        assert available_objs == 'my available objects'
        QtWidgets.QWidget.__init__(self)

    monkeypatch.setattr(main_window, 'get_available_objects', lambda *args, **kwargs: 'my available objects')
    window_opened = []
    monkeypatch.setattr(SetVisualizationWindow, '__init__', mock_init)
    monkeypatch.setattr(SetVisualizationWindow, 'show', functools.partial(window_opened.append, True))

    main_window.set_vis_action.trigger()
    assert window_opened == [True]


def test_MainWindow_open_enrichment_analysis(main_window, monkeypatch):
    window_opened = []
    monkeypatch.setattr(EnrichmentWindow, 'show', functools.partial(window_opened.append, True))

    main_window.enrichment_action.trigger()
    assert window_opened == [True]


def test_MainWindow_choose_tab_by_name(use_temp_settings_file, main_window_with_tabs, monkeypatch):
    truth = sorted(['my table', 'counted', 'counted_6cols', 'test_deseq', 'majority_vote_intersection output'])
    keys = truth.copy()
    np.random.shuffle(keys)
    main_window_with_tabs.sort_tabs_by_name()

    for key in keys:
        main_window_with_tabs.choose_tab_by_name(key)
        assert main_window_with_tabs.tabs.currentIndex() == truth.index(key)


def test_MainWindow_delete_pipeline(use_temp_settings_file, main_window, monkeypatch):
    main_window.pipelines = {'p1': (1, 1), 'p2': (2, 2), 'p3': (3, 3)}
    monkeypatch.setattr(QtWidgets.QInputDialog, 'getItem', lambda *args, **kwargs: ('p2', True))
    main_window.delete_pipeline()
    assert main_window.pipelines == {'p1': (1, 1), 'p3': (3, 3)}


def test_MainWindow_delete_pipeline_no_pipelines(use_temp_settings_file, main_window):
    main_window.delete_pipeline()


def test_MainWindow_export_pipeline_no_pipelines(use_temp_settings_file, main_window):
    main_window.export_pipeline()


def test_MainWindow_edit_pipeline(monkeypatch, use_temp_settings_file, main_window):
    monkeypatch.setattr(CreatePipelineWindow, 'exec', lambda *args, **kwargs: None)
    main_window.pipelines = {'p1': (filtering.Pipeline(), 1)}
    main_window.edit_pipeline('p1')


def test_MainWindow_clear_cache(monkeypatch, use_temp_settings_file, main_window):
    called = []
    monkeypatch.setattr(io, 'clear_cache', lambda *args, **kwargs: called.append(True))
    main_window.clear_cache()
    assert called == [True]


@pytest.mark.parametrize('state', [True, False])
def test_MainWindow_toggle_history(state, use_temp_settings_file, main_window):
    main_window.toggle_history_window(state)


def test_MainWindow_save_session(use_temp_settings_file, main_window, monkeypatch):
    monkeypatch.setattr(QtWidgets.QFileDialog, 'getOpenFileName',
                        lambda *args, **kwargs: ('tests/test_files/test_session.rnal', '.rnal'))
    monkeypatch.setattr(QtWidgets.QApplication, 'processEvents', lambda *args, **kwargs: None)

    main_window.load_session()

    session_fname = 'session filename.rnal'
    n_files = main_window.tabs.count()
    n_pipelines = len(main_window.pipelines)
    item_types_truth = ['FoldChangeFilter', 'CountFilter', 'Filter', 'DESeqFilter', 'set']
    item_properties_truth = [{'numerator_name': 'a', 'denominator_name': 'b'}, {'is_normalized': False}, {},
                             {'log2fc_col': 'log2FoldChange', 'padj_col': 'padj', 'pval_col': 'pvalue'}, {}]
    pipeline_names_truth = ['New Pipeline', 'Other Pipeline']
    pipeline_files_truth = [re.sub('\d\d:\d\d:\d\d', '$EXPORTTIME', pipeline.export_pipeline(filename=None)) for
                            pipeline, p_id in main_window.pipelines.values()]
    func_called = []

    def mock_save_session(self, file_data: List[io.FileData], pipeline_data: List[io.PipelineData], report: dict,
                          report_file_paths: dict):
        assert len(file_data) == n_files
        assert [file.item_type for file in file_data] == item_types_truth
        assert [file.item_property for file in file_data] == item_properties_truth
        assert len(pipeline_data) == n_pipelines
        assert [pipeline.name for pipeline in pipeline_data] == pipeline_names_truth
        assert [re.sub('\d\d:\d\d:\d\d', '$EXPORTTIME', pipeline.content) for pipeline in
                pipeline_data] == pipeline_files_truth

        func_called.append(True)

    monkeypatch.setattr(io.GUISessionManager, 'save_session', mock_save_session)
    monkeypatch.setattr(QtWidgets.QFileDialog, 'getSaveFileName', lambda *args, **kwargs: (session_fname, '.rnal'))

    main_window.save_session_action.trigger()
    assert func_called == [True]


@pytest.mark.parametrize('legacy_session', [True, False])
def test_MainWindow_load_session(use_temp_settings_file, main_window, monkeypatch, legacy_session):
    if legacy_session:
        session_file = 'tests/test_files/test_legacy_session.rnal'
    else:
        session_file = 'tests/test_files/test_session.rnal'
    pipelines_truth = {'New Pipeline': filtering.Pipeline('Filter'),
                       'Other Pipeline': filtering.Pipeline('DESeqFilter')}
    pipelines_truth['New Pipeline'].add_function('filter_top_n', by='log2FoldChange', n=99, ascending=True,
                                                 na_position='last', opposite=False)
    pipelines_truth['New Pipeline'].add_function('describe', percentiles=[0.01, 0.25, 0.5, 0.75, 0.99])
    pipelines_truth['Other Pipeline'].add_function('split_fold_change_direction')
    pipelines_truth['Other Pipeline'].add_function('volcano_plot', alpha=0.1)

    objs_truth = [filtering.FoldChangeFilter('tests/test_files/fc_1.csv', 'a', 'b'),
                  filtering.CountFilter('tests/test_files/counted.tsv'),
                  filtering.Filter('tests/test_files/counted_6cols.csv'),
                  filtering.DESeqFilter('tests/test_files/test_deseq.csv'),
                  enrichment.FeatureSet(
                      {'WBGene00007069', 'WBGene00007064', 'WBGene00007063', 'WBGene00007074', 'WBGene00077502',
                       'WBGene00007076', 'WBGene00044951', 'WBGene00007067', 'WBGene00044022', 'WBGene00043990',
                       'WBGene00077504', 'WBGene00007066', 'WBGene00043987', 'WBGene00014997', 'WBGene00043989',
                       'WBGene00007071', 'WBGene00007075', 'WBGene00007078', 'WBGene00007079', 'WBGene00007077',
                       'WBGene00077503', 'WBGene00043988'}, 'majority_vote_intersection output')]
    objs_truth[0].fname = Path('my table')
    objs_truth[1].fname = Path('counted')
    objs_truth[2].fname = Path('counted_6cols')
    objs_truth[3].fname = Path('test_deseq')

    monkeypatch.setattr(QtWidgets.QFileDialog, 'getOpenFileName',
                        lambda *args, **kwargs: (session_file, '.rnal'))
    main_window.load_session_action.trigger()
    assert main_window.tabs.count() == 5
    assert len(main_window.pipelines) == 2
    assert {key: val[0] for key, val in main_window.pipelines.items()} == pipelines_truth

    for i in range(1, main_window.tabs.count()):
        obj = main_window.tabs.widget(i).obj()

        assert (obj == objs_truth[i]) or (np.allclose(obj.df.drop(cs.first()), objs_truth[i].df.drop(cs.first())) and (
            obj.fname == objs_truth[i].fname))


def test_MainWindow_about(main_window, monkeypatch):
    window_opened = []
    monkeypatch.setattr(gui_windows.AboutWindow, 'exec', functools.partial(window_opened.append, True))

    main_window.about_action.trigger()
    assert window_opened == [True]


def test_MainWindow_cite(main_window, monkeypatch):
    window_opened = []
    monkeypatch.setattr(gui_windows.HowToCiteWindow, 'exec', functools.partial(window_opened.append, True))

    main_window.cite_action.trigger()
    assert window_opened == [True]


def test_MainWindow_settings(main_window, monkeypatch):
    window_opened = []
    monkeypatch.setattr(gui_windows.SettingsWindow, 'exec', lambda *args: window_opened.append(True))

    main_window.settings_action.trigger()
    assert window_opened == [True]


def test_MainWindow_user_guide(main_window, monkeypatch):
    window_opened = []

    def mock_open_url(url):
        window_opened.append(True)
        return True

    monkeypatch.setattr(QtGui.QDesktopServices, 'openUrl', mock_open_url)

    main_window.user_guide_action.trigger()
    assert window_opened == [True]


def test_MainWindow_context_menu(qtbot, main_window_with_tabs, monkeypatch):
    opened = []

    def mock_exec(*args, **kwargs):
        opened.append(True)

    monkeypatch.setattr(QtWidgets.QMenu, 'exec', mock_exec)
    qtbot.mouseClick(main_window_with_tabs.tabs.tabBar(), RIGHT_CLICK,
                     pos=main_window_with_tabs.tabs.tabBar().tabRect(1).center())
    assert opened == [True]


def test_MainWindow_clear_history(main_window_with_tabs, monkeypatch):
    cleared = [False for i in range(main_window_with_tabs.tabs.count())]
    truth = [True for i in cleared]

    def mock_clear(*args, ind):
        cleared[ind] = True

    for i in range(len(truth)):
        monkeypatch.setattr(main_window_with_tabs.undo_group.stacks()[i], 'clear', functools.partial(mock_clear, ind=i))

    main_window_with_tabs.clear_history()
    assert cleared == truth


def test_MainWindow_clear_session(main_window_with_tabs):
    main_window_with_tabs.clear_session(confirm_action=False)
    assert main_window_with_tabs.tabs.count() == 1
    assert main_window_with_tabs.tabs.widget(0).is_empty()


NO_WINOS_ACTIONS = ['shortstack_action']


@pytest.mark.parametrize('action_name', ['ontology_graph_action', 'pathway_graph_action', 'featurecounts_single_action',
                                         'featurecounts_paired_action', 'bowtie2_index_action', 'shortstack_action',
                                         'bowtie2_single_action', 'bowtie2_paired_action', 'kallisto_index_action',
                                         'kallisto_single_action', 'kallisto_paired_action', 'cutadapt_single_action',
                                         'cutadapt_paired_action', 'set_op_action', 'enrichment_action',
                                         'set_vis_action', 'bar_plot_action', 'validate_sam_action',
                                         'convert_sam_action', 'sam2fastq_single_action', 'sam2fastq_paired_action',
                                         'fastq2sam_single_action', 'fastq2sam_paired_action', 'sort_sam_action',
                                         'find_duplicates_action', 'bam_index_action'])
def test_MainWindow_open_windows(main_window_with_tabs, action_name):
    action = getattr(main_window_with_tabs, action_name)
    if platform.system() == 'Windows' and action_name in NO_WINOS_ACTIONS:
        assert not action.isEnabled()
    else:
        assert action.isEnabled()
        action.trigger()


@pytest.mark.parametrize('action_name, window_attr_name',
                         [('new_pipeline_action', 'pipeline_window'),
                          ('cite_action', 'cite_window'),
                          ('about_action', 'about_window'),
                          ('settings_action', 'settings_window')])
def test_MainWindow_open_dialogs(main_window_with_tabs, action_name, window_attr_name, monkeypatch):
    action = getattr(main_window_with_tabs, action_name)

    def win():
        return getattr(main_window_with_tabs, window_attr_name)

    def handle_dialog():
        while win() is None or not win().isVisible():
            QtWidgets.QApplication.processEvents()
        win().close()

    QtCore.QTimer.singleShot(100, handle_dialog)
    action.trigger()


class TestMainWindowToggleReporting:
    # Mock the dependencies and set up the test scenario
    @pytest.fixture
    def mock_dependencies(self):
        with patch('rnalysis.gui.gui.MainWindow.clear_session', autospec=True) as mock_clear_session:
            yield mock_clear_session

    def test_toggle_reporting_on(self, main_window, mock_dependencies, caplog, monkeypatch):
        session_cleared = []

        def mock_clear_session(self, confirm_action=True):
            assert confirm_action
            session_cleared.append(True)
            return True

        monkeypatch.setattr(main_window, 'clear_session', mock_clear_session)
        # Arrange
        mock_clear_session = mock_dependencies
        mock_clear_session.return_value = True
        state = True  # Turning on report generation

        # Act
        with caplog.at_level(logging.WARNING):
            main_window._toggle_reporting(state)

        # Assert
        assert main_window._generate_report
        assert main_window.report is not None
        assert main_window.tabs.count() == 1 and main_window.tabs.currentWidget().is_empty()
        assert main_window.toggle_report_action.isChecked()
        assert session_cleared == [True]

    def test_toggle_reporting_on_missing_module(self, main_window, monkeypatch):
        # Arrange
        session_cleared = []

        def mock_clear_session(self, confirm_action=True):
            assert confirm_action
            session_cleared.append(True)
            return True

        monkeypatch.setattr(main_window, 'clear_session', mock_clear_session)

        def mock_report_init(*args):
            raise ImportError

        monkeypatch.setattr(rnalysis.gui.gui_report.ReportGenerator, '__init__', mock_report_init)

        state = True  # Turning on report generation

        # Act
        main_window._toggle_reporting(state)

        # Assert
        assert not main_window._generate_report
        assert main_window.report is None
        assert session_cleared == []

    def test_toggle_reporting_on_clear_session_failed(self, main_window, mock_dependencies, monkeypatch):
        # Arrange
        session_cleared = []

        def mock_clear_session(confirm_action=True):
            session_cleared.append(True)
            return False

        monkeypatch.setattr(main_window, 'clear_session', mock_clear_session)
        state = True  # Turning on report generation

        # Act
        main_window._toggle_reporting(state)

        # Assert
        assert not main_window._generate_report
        assert main_window.report is None
        assert session_cleared == [True]

    def test_toggle_reporting_off(self, main_window):
        # Arrange
        state = False
        main_window._generate_report = True  # Simulate report generation turned on
        main_window.toggle_report_action.setChecked(True)

        # Act
        main_window._toggle_reporting(state)

        # Assert
        assert not main_window._generate_report
        assert main_window.report is None
        assert not main_window.toggle_report_action.isChecked()


class TestPromptAutoReportGen:
    @pytest.mark.parametrize("choice_truth, dont_ask_again_truth", [
        (True, True), (True, False), (False, True), (False, False)])
    def test_no_preset(self, use_temp_settings_file, main_window, caplog, monkeypatch, choice_truth,
                       dont_ask_again_truth):
        # Simulate no preset settings
        def mock_get_settings():
            return None

        monkeypatch.setattr(settings, 'get_report_gen_settings', mock_get_settings)

        def mock_set_settings(given_choice):
            if dont_ask_again_truth:
                assert given_choice == choice_truth
            else:
                assert given_choice is None

        monkeypatch.setattr(settings, 'set_report_gen_settings', mock_set_settings)

        # Simulate user input from ReportGenerationMessageBox
        message_box = Mock()
        message_box.exec.return_value = (choice_truth, dont_ask_again_truth)

        # Mock the ReportGenerationMessageBox and settings
        with patch('rnalysis.gui.gui_windows.ReportGenerationMessageBox', return_value=message_box):
            main_window.prompt_auto_report_gen()

        # Check if the toggle_report_action is checked
        assert main_window.toggle_report_action.isChecked() == choice_truth

    @pytest.mark.parametrize('preset_choice', [True, False])
    def test_with_preset(self, main_window, monkeypatch, preset_choice, use_temp_settings_file):
        # Simulate having a preset choice
        def mock_get_settings():
            return preset_choice

        monkeypatch.setattr(settings, 'get_report_gen_settings', mock_get_settings)

        # Run the method
        main_window.prompt_auto_report_gen()

        # Check if the toggle_report_action is checked and no log message was generated
        assert main_window.toggle_report_action.isChecked() == preset_choice


def test_monkeypatch_setup(main_window):
    try:
        main_window._monkeypatch_setup('alt_tqdm', 'alt_parallel')
        assert enrichment.enrichment_runner.generic.ProgressParallel == 'alt_parallel'
        assert generic.ProgressParallel == 'alt_parallel'
        assert filtering.clustering.generic.ProgressParallel == 'alt_parallel'
        assert enrichment.enrichment_runner.parsing.tqdm == 'alt_tqdm'
        assert enrichment.enrichment_runner.io.tqdm == 'alt_tqdm'
        assert enrichment.enrichment_runner.tqdm == 'alt_tqdm'
        assert filtering.clustering.tqdm == 'alt_tqdm'
        assert filtering.tqdm == 'alt_tqdm'
        assert fastq.tqdm == 'alt_tqdm'
    finally:
        main_window._monkeypatch_cleanup()


def test_monkeypatch_cleanup(main_window):
    main_window._monkeypatch_setup('alt_tqdm', 'alt_parallel')
    main_window._monkeypatch_cleanup()
    assert enrichment.enrichment_runner.generic.ProgressParallel == ORIG_PARALLEL
    assert generic.ProgressParallel == ORIG_PARALLEL
    assert filtering.clustering.generic.ProgressParallel == ORIG_PARALLEL
    assert enrichment.enrichment_runner.parsing.tqdm == ORIG_TQDM
    assert enrichment.enrichment_runner.io.tqdm == ORIG_TQDM
    assert enrichment.enrichment_runner.tqdm == ORIG_TQDM
    assert filtering.clustering.tqdm == ORIG_TQDM
    assert filtering.tqdm == ORIG_TQDM
    assert fastq.tqdm == ORIG_TQDM


class TestLimmaWindow:
    design_mat_path = 'tests/test_files/test_design_matrix_advanced.csv'

    @pytest.fixture(autouse=True)
    def test_init(self, qtbot, monkeypatch, limma_window):
        assert limma_window.windowTitle() == 'Limma-Voom differential expression setup'
        monkeypatch.setattr(QtWidgets.QFileDialog, 'getOpenFileName',
                            lambda *args, **kwargs: (self.design_mat_path, ''))
        qtbot.mouseClick(limma_window.param_widgets['design_matrix'].open_button, LEFT_CLICK)
        qtbot.mouseClick(limma_window.param_widgets['load_design'], LEFT_CLICK)

    def test_load_design_mat(self, limma_window):
        design_mat_truth = io.load_table(self.design_mat_path, 0)
        assert limma_window.design_mat.equals(design_mat_truth)
        assert limma_window.comparisons_widgets['picker'].design_mat.equals(design_mat_truth)

    def test_get_analysis_params(self, limma_window):
        truth = dict(r_installation_folder='auto', design_matrix=self.design_mat_path, output_folder=None,
                     comparisons=[('replicate', 'rep3', 'rep2'), ('condition', 'cond1', 'cond2')],
                     covariates=['covariate1'], lrt_factors=['factor1'], random_effect=None, quality_weights=False,
                     return_code=True, return_design_matrix=True, return_log=True)

        limma_window.comparisons_widgets['picker'].add_comparison_widget()
        limma_window.comparisons_widgets['picker'].inputs[0].factor.setCurrentText('replicate')
        limma_window.comparisons_widgets['picker'].inputs[0].numerator.setCurrentText('rep3')
        limma_window.comparisons_widgets['picker'].inputs[0].denominator.setCurrentText('rep2')

        limma_window.covariates_widgets['picker'].add_comparison_widget()
        limma_window.covariates_widgets['picker'].inputs[0].factor.setCurrentText('covariate1')

        limma_window.lrt_widgets['picker'].add_comparison_widget()
        limma_window.lrt_widgets['picker'].inputs[0].factor.setCurrentText('factor1')

        assert limma_window.get_analysis_kwargs() == truth

    def test_start_analysis(self, qtbot, monkeypatch, limma_window):
        truth_args = []
        truth_kwargs = dict(r_installation_folder='auto', design_matrix=self.design_mat_path, output_folder=None,
                            comparisons=[('replicate', 'rep3', 'rep2'), ('condition', 'cond1', 'cond2')],
                            covariates=['covariate1'], lrt_factors=['factor1'], random_effect=None,
                            quality_weights=False, return_code=True, return_design_matrix=True, return_log=True)

        limma_window.comparisons_widgets['picker'].add_comparison_widget()
        limma_window.comparisons_widgets['picker'].inputs[0].factor.setCurrentText('replicate')
        limma_window.comparisons_widgets['picker'].inputs[0].numerator.setCurrentText('rep3')
        limma_window.comparisons_widgets['picker'].inputs[0].denominator.setCurrentText('rep2')

        limma_window.covariates_widgets['picker'].add_comparison_widget()
        limma_window.covariates_widgets['picker'].inputs[0].factor.setCurrentText('covariate1')

        limma_window.lrt_widgets['picker'].add_comparison_widget()
        limma_window.lrt_widgets['picker'].inputs[0].factor.setCurrentText('factor1')

        with qtbot.waitSignal(limma_window.paramsAccepted) as blocker:
            qtbot.mouseClick(limma_window.start_button, LEFT_CLICK)
        assert blocker.args[0] == truth_args
        assert blocker.args[1] == truth_kwargs


class TestDESeqWindow:
    design_mat_path = 'tests/test_files/test_design_matrix_advanced.csv'

    @pytest.fixture(autouse=True)
    def test_init(self, deseq_window, qtbot, monkeypatch):
        assert deseq_window.windowTitle() == 'DESeq2 differential expression setup'
        monkeypatch.setattr(QtWidgets.QFileDialog, 'getOpenFileName',
                            lambda *args, **kwargs: (self.design_mat_path, ''))
        qtbot.mouseClick(deseq_window.param_widgets['design_matrix'].open_button, LEFT_CLICK)
        qtbot.mouseClick(deseq_window.param_widgets['load_design'], LEFT_CLICK)

    def test_load_design_mat(self, deseq_window):
        design_mat_truth = io.load_table(self.design_mat_path, 0)
        assert deseq_window.design_mat.equals(design_mat_truth)
        assert deseq_window.comparisons_widgets['picker'].design_mat.equals(design_mat_truth)

    def test_get_analysis_params(self, deseq_window):
        truth = dict(r_installation_folder='auto', design_matrix=self.design_mat_path, output_folder=None,
                     comparisons=[('replicate', 'rep3', 'rep2'), ('condition', 'cond1', 'cond2')],
                     covariates=['covariate1'], lrt_factors=['factor1'], return_code=True, return_design_matrix=True,
                     cooks_cutoff=True, scaling_factors=None, return_log=True)

        deseq_window.comparisons_widgets['picker'].add_comparison_widget()
        deseq_window.comparisons_widgets['picker'].inputs[0].factor.setCurrentText('replicate')
        deseq_window.comparisons_widgets['picker'].inputs[0].numerator.setCurrentText('rep3')
        deseq_window.comparisons_widgets['picker'].inputs[0].denominator.setCurrentText('rep2')

        deseq_window.covariates_widgets['picker'].add_comparison_widget()
        deseq_window.covariates_widgets['picker'].inputs[0].factor.setCurrentText('covariate1')

        deseq_window.lrt_widgets['picker'].add_comparison_widget()
        deseq_window.lrt_widgets['picker'].inputs[0].factor.setCurrentText('factor1')

        assert deseq_window.get_analysis_kwargs() == truth

    def test_start_analysis(self, qtbot, monkeypatch, deseq_window):
        truth_args = []
        truth_kwargs = dict(r_installation_folder='auto', design_matrix=self.design_mat_path, output_folder=None,
                            comparisons=[('replicate', 'rep3', 'rep2'), ('condition', 'cond1', 'cond2')],
                            covariates=['covariate1'], lrt_factors=['factor1'], return_code=True, return_log=True,
                            return_design_matrix=True, cooks_cutoff=True, scaling_factors=None)

        deseq_window.comparisons_widgets['picker'].add_comparison_widget()
        deseq_window.comparisons_widgets['picker'].inputs[0].factor.setCurrentText('replicate')
        deseq_window.comparisons_widgets['picker'].inputs[0].numerator.setCurrentText('rep3')
        deseq_window.comparisons_widgets['picker'].inputs[0].denominator.setCurrentText('rep2')

        deseq_window.covariates_widgets['picker'].add_comparison_widget()
        deseq_window.covariates_widgets['picker'].inputs[0].factor.setCurrentText('covariate1')

        deseq_window.lrt_widgets['picker'].add_comparison_widget()
        deseq_window.lrt_widgets['picker'].inputs[0].factor.setCurrentText('factor1')

        with qtbot.waitSignal(deseq_window.paramsAccepted) as blocker:
            qtbot.mouseClick(deseq_window.start_button, LEFT_CLICK)
        assert blocker.args[0] == truth_args
        assert blocker.args[1] == truth_kwargs


class TestMainWindowJobRunning:
    def test_start_generic_job(self, main_window, mocker, monkeypatch):
        parent_tab = mocker.Mock(spec=FilterTabPage)
        worker = mocker.Mock(spec=gui_widgets.Worker)
        finish_slots = mocker.Mock()

        monkeypatch.setattr(main_window, 'queue_worker', mocker.Mock())
        main_window.start_generic_job(parent_tab, worker, finish_slots)

        main_window.queue_worker.assert_called_once_with(worker, [mocker.ANY, finish_slots])

    def test_finish_generic_job(self, main_window, mocker, monkeypatch):
        worker_output = mocker.Mock(spec=gui_widgets.WorkerOutput)
        worker_output.raised_exception = None
        worker_output.result = ["result"]
        worker_output.emit_args = ["func_name"]
        worker_output.job_id = 1

        parent_tab = mocker.Mock(spec=TabPage)

        monkeypatch.setattr(main_window, 'update_report_from_worker', mocker.Mock())
        monkeypatch.setattr(main_window, 'update_report_spawn', mocker.Mock())
        monkeypatch.setattr(main_window, 'new_tab_from_filter_obj', mocker.Mock())

        main_window.finish_generic_job(worker_output, parent_tab)

        parent_tab.update_tab.assert_called_once()
        parent_tab.process_outputs.assert_called_once_with(worker_output.result, worker_output.job_id, "func_name")

    def test_start_generic_job_from_params(self, main_window, mocker, monkeypatch):
        func_name = "func_name"
        func = mocker.Mock()
        args = ["arg1", "arg2"]
        kwargs = {"kwarg1": "value1"}
        finish_slots = mocker.Mock()
        predecessor = 1

        monkeypatch.setattr(main_window, 'start_generic_job', mocker.Mock())
        main_window.start_generic_job_from_params(func_name, func, args, kwargs, finish_slots, predecessor)
        main_window.start_generic_job.assert_called_once_with(None, mocker.ANY, finish_slots)

    def test_start_clustering(self, main_window, mocker, monkeypatch):
        parent_tab = mocker.Mock(spec=FilterTabPage)
        worker = mocker.Mock(spec=gui_widgets.Worker)
        finish_slot = mocker.Mock()

        monkeypatch.setattr(main_window, 'queue_worker', mocker.Mock())
        main_window.start_clustering(parent_tab, worker, finish_slot)

        main_window.queue_worker.assert_called_once_with(worker, (mocker.ANY, finish_slot))

    def test_start_enrichment(self, main_window, mocker, monkeypatch):
        worker = mocker.Mock(spec=gui_widgets.Worker)
        finish_slot = mocker.Mock()

        monkeypatch.setattr(main_window, 'queue_worker', mocker.Mock())
        main_window.start_enrichment(worker, finish_slot)

        main_window.queue_worker.assert_called_once_with(worker, (main_window.finish_enrichment, finish_slot))

    def test_finish_enrichment(self, main_window, mocker, monkeypatch):
        worker_output = mocker.Mock(spec=gui_widgets.WorkerOutput)
        worker_output.raised_exception = None
        worker_output.result = [mocker.Mock(spec=pl.DataFrame),
                                mocker.Mock(spec=enrichment.enrichment_runner.EnrichmentPlotter)]
        worker_output.emit_args = ["set_name"]
        worker_output.job_id = 1

        monkeypatch.setattr(main_window, 'update_report_spawn', mocker.Mock())
        monkeypatch.setattr(main_window, 'display_enrichment_results', mocker.Mock())
        monkeypatch.setattr(main_window, 'show', mocker.Mock())

        main_window.finish_enrichment(worker_output)

        main_window.show.assert_called_once()
        main_window.display_enrichment_results.assert_called_once_with(worker_output.result[0], "set_name")
        main_window.update_report_spawn.assert_any_call(mocker.ANY, mocker.ANY, worker_output.job_id,
                                                        worker_output.result[0])

    def test_queue_worker(self, main_window, mocker, monkeypatch):
        worker = mocker.Mock(spec=gui_widgets.Worker)
        output_slots = mocker.Mock()

        monkeypatch.setattr(main_window, 'run_threaded_workers', lambda *args, **kwargs: None)
        monkeypatch.setattr(main_window, 'job_queue', mocker.Mock(spec=Queue))
        monkeypatch.setattr(main_window, 'jobQueued', mocker.Mock())

        main_window.queue_worker(worker, output_slots)

        main_window.job_queue.put.assert_called_once_with((worker, output_slots))
        main_window.jobQueued.emit.assert_called_once()

    def test_finish_generic_job_with_exception(self, main_window, mocker, monkeypatch):
        worker_output = mocker.Mock(spec=gui_widgets.WorkerOutput)
        worker_output.raised_exception = Exception("Test Exception")
        worker_output.result = []
        worker_output.emit_args = ["func_name"]
        worker_output.job_id = 1

        parent_tab = mocker.Mock(spec=TabPage)

        monkeypatch.setattr(main_window, 'update_report_from_worker', mocker.Mock())
        monkeypatch.setattr(main_window, 'update_report_spawn', mocker.Mock())
        monkeypatch.setattr(main_window, 'new_tab_from_filter_obj', mocker.Mock())
        monkeypatch.setattr(main_window, 'run_threaded_workers', lambda *args, **kwargs: None)

        with pytest.raises(Exception, match="Test Exception"):
            main_window.finish_generic_job(worker_output, parent_tab)

        parent_tab.update_tab.assert_not_called()
        parent_tab.process_outputs.assert_not_called()

    def test_cancel_job_running(self, main_window, mocker, monkeypatch):
        index = 0
        func_name = "func_name"
        worker = mocker.Mock(spec=gui_widgets.Worker)
        monkeypatch.setattr(main_window, 'run_threaded_workers', mocker.Mock())
        monkeypatch.setattr(main_window, 'job_queue', mocker.Mock(spec=Queue, queue=[worker]))

        warning_message_box = mocker.patch.object(QtWidgets.QMessageBox, 'warning', create=True)

        main_window.cancel_job(index, func_name)

        worker.deleteLater.assert_not_called()
        main_window.job_queue.empty.assert_not_called()
        main_window.job_queue.get.assert_not_called()
        main_window.job_queue.put.assert_not_called()
        main_window.run_threaded_workers.assert_not_called()

        warning_message_box.assert_called_once_with(main_window, "Can't stop a running job!", mocker.ANY)

    def test_cancel_job_queued(self, main_window, mocker, monkeypatch):
        index = 2
        func_name = "func_name"

        worker1 = mocker.Mock(spec=gui_widgets.Worker)
        worker2 = mocker.Mock(spec=gui_widgets.Worker)
        monkeypatch.setattr(main_window, 'run_threaded_workers', mocker.Mock())
        monkeypatch.setattr(main_window, 'job_queue', mocker.Mock(spec=Queue, queue=(worker1, worker2)))

        main_window.cancel_job(index, func_name)

        worker1.deleteLater.assert_not_called()
        worker2.deleteLater.assert_called_once()
        main_window.job_queue.empty.assert_called_once()
        main_window.job_queue.put.assert_called_once_with(worker1)
        main_window.run_threaded_workers.assert_called_once()

    def test_finish_clustering(self, main_window, mocker):
        worker_output = mocker.Mock(spec=gui_widgets.WorkerOutput)
        worker_output.raised_exception = None
        clustering_runner = mocker.Mock(spec=clustering.ClusteringRunner)
        worker_output.result = [mocker.Mock(spec=clustering.ClusteringRunner), clustering_runner]
        worker_output.job_id = 1
        parent_tab = mocker.Mock(spec=FilterTabPage)
        func_name = worker_output.partial.func.readable_name
        figs = worker_output.result[1].plot_clustering()

        main_window.finish_clustering(worker_output, parent_tab)

        parent_tab.update_tab.assert_called_once()
        parent_tab.process_outputs.assert_any_call(worker_output.result[0], 1, func_name)
        parent_tab.process_outputs.assert_any_call(figs, 1, func_name)

    def test_finish_enrichment_report_enabled(self, main_window, mocker, monkeypatch):
        worker_output = mocker.Mock(spec=gui_widgets.WorkerOutput)
        worker_output.raised_exception = None
        worker_output.result = [mocker.Mock(spec=pl.DataFrame),
                                mocker.Mock(spec=enrichment.enrichment_runner.EnrichmentPlotter)]
        worker_output.emit_args = ["set_name"]
        worker_output.job_id = 1

        monkeypatch.setattr(main_window, 'update_report_spawn', mocker.Mock())
        monkeypatch.setattr(main_window, 'display_enrichment_results', mocker.Mock())
        monkeypatch.setattr(main_window, 'show', mocker.Mock())
        monkeypatch.setattr(main_window, '_generate_report', True)

        main_window.finish_enrichment(worker_output)

        main_window.show.assert_called_once()
        main_window.display_enrichment_results.assert_called_once_with(worker_output.result[0], "set_name")
        main_window.update_report_spawn.assert_called()

    def test_finish_enrichment_report_disabled(self, main_window, mocker, monkeypatch):
        worker_output = mocker.Mock(spec=gui_widgets.WorkerOutput)
        worker_output.raised_exception = None
        worker_output.result = [mocker.Mock(spec=pl.DataFrame),
                                mocker.Mock(spec=enrichment.enrichment_runner.EnrichmentPlotter)]
        worker_output.emit_args = ["set_name"]
        worker_output.job_id = 1

        monkeypatch.setattr(main_window, 'update_report_spawn', mocker.Mock())
        monkeypatch.setattr(main_window, 'display_enrichment_results', mocker.Mock())
        monkeypatch.setattr(main_window, 'show', mocker.Mock())
        monkeypatch.setattr(main_window, '_generate_report', False)

        main_window.finish_enrichment(worker_output)

        main_window.show.assert_called_once()
        main_window.display_enrichment_results.assert_called_once_with(worker_output.result[0], "set_name")
        main_window.update_report_spawn.assert_not_called()

    def test_finish_generic_job_empty_result(self, main_window, mocker, monkeypatch):
        worker_output = mocker.Mock(spec=gui_widgets.WorkerOutput)
        worker_output.raised_exception = None
        worker_output.result = None
        worker_output.emit_args = ["func_name"]
        worker_output.job_id = 1

        parent_tab = mocker.Mock(spec=TabPage)

        monkeypatch.setattr(main_window, 'update_report_from_worker', mocker.Mock())
        monkeypatch.setattr(main_window, 'update_report_spawn', mocker.Mock())
        monkeypatch.setattr(main_window, 'new_tab_from_filter_obj', mocker.Mock())

        main_window.finish_generic_job(worker_output, parent_tab)

        parent_tab.update_tab.assert_not_called()
        parent_tab.process_outputs.assert_not_called()

    def test_finish_generic_job_no_parent_tab(self, main_window, mocker, monkeypatch):
        worker_output = mocker.Mock(spec=gui_widgets.WorkerOutput)
        worker_output.raised_exception = None
        worker_output.result = ["result"]
        worker_output.emit_args = ["func_name"]
        worker_output.job_id = 1

        monkeypatch.setattr(main_window, 'update_report_from_worker', mocker.Mock())
        monkeypatch.setattr(main_window, 'update_report_spawn', mocker.Mock())
        monkeypatch.setattr(main_window, 'new_tab_from_filter_obj', mocker.Mock())
        monkeypatch.setattr(main_window, 'is_valid_spawn', lambda *args: True)

        main_window.finish_generic_job(worker_output, None)

        main_window.update_report_from_worker.assert_called_once_with(worker_output)
        main_window.update_report_spawn.assert_called_once()

    def test_finish_clustering_empty_result(self, main_window, mocker):
        worker_output = mocker.Mock(spec=gui_widgets.WorkerOutput)
        worker_output.raised_exception = None
        worker_output.result = []
        worker_output.partial.func.__name__ = "func_name"
        worker_output.job_id = 1

        parent_tab = mocker.Mock(spec=FilterTabPage)

        main_window.finish_clustering(worker_output, parent_tab)

        parent_tab.update_tab.assert_not_called()
        parent_tab.process_outputs.assert_not_called()

    def test_finish_clustering_exception_raised(self, main_window, mocker, monkeypatch):
        worker_output = mocker.Mock(spec=gui_widgets.WorkerOutput)
        worker_output.raised_exception = Exception("Test Exception")
        worker_output.result = []
        worker_output.partial.func.__name__ = "func_name"
        worker_output.job_id = 1

        parent_tab = mocker.Mock(spec=FilterTabPage)

        with pytest.raises(Exception, match="Test Exception"):
            main_window.finish_clustering(worker_output, parent_tab)

        parent_tab.update_tab.assert_not_called()
        parent_tab.process_outputs.assert_not_called()

    def test_finish_enrichment_empty_result(self, main_window, mocker, monkeypatch):
        worker_output = mocker.Mock(spec=gui_widgets.WorkerOutput)
        worker_output.raised_exception = None
        worker_output.result = []
        worker_output.emit_args = ["set_name"]
        worker_output.job_id = 1

        monkeypatch.setattr(main_window, 'update_report_spawn', mocker.Mock())
        monkeypatch.setattr(main_window, 'display_enrichment_results', mocker.Mock())
        monkeypatch.setattr(main_window, 'show', mocker.Mock())
        monkeypatch.setattr(main_window, '_generate_report', True)

        main_window.finish_enrichment(worker_output)

        main_window.display_enrichment_results.assert_not_called()
        main_window.update_report_spawn.assert_not_called()

    def test_finish_enrichment_exception_raised(self, main_window, mocker, monkeypatch):
        worker_output = mocker.Mock(spec=gui_widgets.WorkerOutput)
        worker_output.raised_exception = Exception("Test Exception")
        worker_output.result = []
        worker_output.emit_args = ["set_name"]
        worker_output.job_id = 1

        monkeypatch.setattr(main_window, 'update_report_spawn', mocker.Mock())
        monkeypatch.setattr(main_window, 'display_enrichment_results', mocker.Mock())
        monkeypatch.setattr(main_window, 'show', mocker.Mock())
        monkeypatch.setattr(main_window, '_generate_report', True)

        with pytest.raises(Exception, match="Test Exception"):
            main_window.finish_enrichment(worker_output)

        main_window.show.assert_not_called()
        main_window.display_enrichment_results.assert_not_called()
        main_window.update_report_spawn.assert_not_called()
