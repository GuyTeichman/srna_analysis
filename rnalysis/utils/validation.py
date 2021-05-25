from pathlib import Path
from typing import Union, Iterable, Tuple
import types
import pandas as pd
import warnings


def check_is_df_like(inp):
    """
    checks whether an input file is a pandas DataFrame, a string that represent a path of a .csv file, a Path object \
    of a .csv file, or an invalid input.

    :param inp: the input we wish to test
    :return: True if pandas DataFrame, False if a string/Path object that leads to a .csv file.\
    Raises ValueError otherwise.
    """
    if isinstance(inp, pd.DataFrame):
        return True
    elif isinstance(inp, str):
        if inp[-4::] == '.csv':
            return False
    elif isinstance(inp, Path):
        if inp.suffix == '.csv':
            return False
    raise ValueError("The input is neither a pandas DataFrame or a csv file")


def is_method_of_class(mthd, cls):
    """
    Returns True if function 'mthd' is a method of class 'cls'

    :type mthd: function
    :type cls: class
    :return: True if 'mthd' is a method of class 'cls', and False otherwise.
    :rtype: bool
    """
    try:
        class_method = getattr(cls, mthd.__name__)
    except AttributeError:
        return False
    if isinstance(mthd, types.MethodType):
        return class_method == mthd.__func__
    return class_method == mthd


def isinstanceinh(obj, parent_class):
    """
    Returns True if 'obj' is is an instance of class 'parent_class', or of a subclass of 'parent_class'.

    :param obj: object to be tested
    :type obj: Any
    :param parent_class: class to be checked against
    :type parent_class: type (e.g. list, tuple, int, bool)
    :return: True if 'obj' is an instance of 'parent_class' or one of its subclasses, and False otherwise.
    :rtype: bool
    """
    return True if issubclass(obj.__class__, parent_class) else False


def isinstanceiter(iterable: Iterable, object_class: Union[type, Tuple[type, ...]]):
    """
    Returns True if all members of an Iterable object are instances of a class or of a subclass thereof. \
    This function consumes iterators/generators.

    :param iterable: the Iterable object whose members' types should be checked.
    :type iterable: Iterable (list, tuple, str, dict, set, etc')
    :param object_class: the class/classes to check 'isinstance' against
    :type object_class: type (e.g. list, tuple, int, bool) or tuple of types
    :return: True if all members of 'iterable' are of type 'object_class', and False otherwise.
    :rtype: bool
    """
    assert isiterable(iterable), f"Object of type {type(iterable)} is not iterable."
    return all([isinstance(i, object_class) for i in iterable])


def isiterable(obj):
    """
    Returns True if obj is Iterable (list, str, tuple, set, dict, etc'), and False otherwise. \
    This function does not consume iterators/generators.

    :param obj: the object to be tested for iterability
    :type obj: Any
    :return: True if obj is Iterable, False otherwise.
    :rtype: bool
    """
    try:
        _ = iter(obj)
    except TypeError:
        return False
    else:
        return True


def validate_biotype_table(biotype_df: pd.DataFrame):
    """
    Assert legality of Biotype Reference Table, and rename column names to standard names ('gene' and 'biotype').
    :param biotype_df: the loaded Biotype Reference Table
    :type biotype_df: pandas DataFrame

    """
    assert biotype_df.shape[
               1] == 2, f"Invalid number of columns in Biotype Reference Table: found {biotype_df.shape[1]} columns instead of 2!"
    assert biotype_df.shape[
               0] >= 2, f"Biotype Reference Table must have at least two rows, found only  {biotype_df.shape[0]}!"
    biotype_df.rename(columns={biotype_df.columns[0]: 'gene', biotype_df.columns[1]: 'biotype'}, inplace=True)


def validate_attr_table(attr_df: pd.DataFrame):
    """
    Assert legality of Attribute Reference Table, and renames the first column to standard name ('gene').
    :param attr_df:
    :type attr_df: pandas DataFrame

    """
    assert attr_df.shape[
               1] >= 2, f"Attribute Reference Table must have at least two columns, found only  {attr_df.shape[1]}!"
    assert attr_df.shape[
               0] >= 2, f"Attribute Reference Table must have at least two rows, found only  {attr_df.shape[0]}!"
    attr_df.rename(columns={attr_df.columns[0]: 'gene'}, inplace=True)


def validate_uniprot_dataset_name(dataset_dict: dict, *names: str):
    for name in names:
        assert name in dataset_dict, f"Dataset '{name}' is not a valid Uniprot Dataset for mapping gene names/IDs. " \
                                     f"Valid Uniprot Datasets are: {', '.join(dataset_dict.keys())}."


def validate_threshold(threshold: float = 1):
    """
    Assertions for functions that filter normalized values by some threshold, \
    or are meant to be used on normalized values.

    :param threshold: optional. A threshold value for filter_low_rpm to be asserted.

    """
    assert isinstance(threshold, (float, int)), "Threshold must be a number!"
    assert threshold >= 0, "Threshold must be zero or larger!"


def validate_is_normalized(filter_obj_fname: Union[str, Path]):
    if '_norm' not in str(filter_obj_fname):
        warnings.warn("This function is meant for normalized values, and your values may not be normalized. ")


def validate_clustering_parameters(metric: str, linkage: str = None):
    legal_metrics = {'euclidean', 'spearman', 'pearson', 'manhattan', 'cosine', 'ys1', 'yr1', 'jackknife'}
    legal_linkages = {'single', 'average', 'complete', 'ward'}
    assert isinstance(metric, str), f"'metric' must be a string. Instead got '{type(metric)}'."
    metric = metric.lower()
    assert metric in legal_metrics, f"'metric' must be one of {legal_metrics}. Instead got '{metric}'."

    if linkage is not None:
        assert isinstance(linkage, str), f"'linkage' must be a string. Instead got '{type(linkage)}'."
        linkage = linkage.lower()
        assert linkage in legal_linkages, f"'linkage' must be in {legal_linkages}. Instead got '{linkage}'."
        return metric, linkage
    return metric


def validate_hdbscan_parameters(min_cluster_size: int, metric: str, cluster_selection_method: str, n_features: int):
    assert isinstance(min_cluster_size, int) and min_cluster_size >= 2, \
        f"'min_cluster_size' must be an integer >=2. Instead got {min_cluster_size}, type={type(min_cluster_size)}."
    assert min_cluster_size <= n_features, \
        "'min_cluster_size' cannot be larger than the number of features in the CountFilter object. "
    assert isinstance(cluster_selection_method, str), \
        f"'cluster_selection_method' must be a string. Instead got {type(cluster_selection_method)}."
    assert isinstance(metric, str), f"'metric' must be a string. Instead got {type(metric)}."
