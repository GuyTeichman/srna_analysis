import pytest

from rnalysis.utils.generic import *


def test_intersection_nonempty():
    assert intersection_nonempty({1, 2, 3}, {2, 5, 7, 1}) == {1, 2}
    assert intersection_nonempty({1, 3, 7}, set()) == {1, 3, 7}
    assert intersection_nonempty({1, 2, 4, 5}, set(), {1, 3, 4, 7}) == {1, 4}


def test_standardize():
    np.random.seed(42)
    data = np.random.randint(-200, 100000, (100, 5))
    res = standardize(data)
    assert res.shape == data.shape
    assert np.isclose(res.mean(axis=0), 0).all()
    assert np.isclose(res.std(axis=0), 1).all()


def test_standard_box_cox():
    np.random.seed(42)
    data = np.random.randint(-200, 100000, (100, 5))
    res = standard_box_cox(data)
    assert res.shape == data.shape
    assert np.isclose(res.mean(axis=0), 0).all()
    assert np.isclose(res.std(axis=0), 1).all()
    assert not np.isclose(res, standardize(data)).all()

    data_df = pd.DataFrame(data, index=[f'ind{i}' for i in range(100)], columns=[f'col{j}' for j in range(5)])
    res_df = standard_box_cox(data_df)
    assert isinstance(res_df, pd.DataFrame)
    assert res_df.shape == data_df.shape
    assert np.all(res_df.index == data_df.index)
    assert np.all(res_df.columns == data_df.columns)


def test_color_generator():
    gen = color_generator()
    preset_colors = ['tab:blue', 'tab:red', 'tab:green', 'tab:orange', 'tab:purple', 'tab:brown', 'tab:pink',
                     'tab:gray', 'tab:olive', 'tab:cyan', 'gold', 'maroon', 'mediumslateblue', 'fuchsia',
                     'lawngreen', 'moccasin', 'thistle']
    for i in range(150):
        color = next(gen)
        assert (isinstance(color, str) and color in preset_colors) or (
                isinstance(color, np.ndarray) and len(color) == 3 and
                                          np.max(color) <= 1 and np.min(color) >= 0)


@pytest.mark.parametrize("this_set,other_sets,majority_threshold,truth",
                         [({1, 2, 3, 4}, [{1, 2, 3, 6}, {4, 5, 6}], 2 / 3, {1, 2, 3, 4, 6}),
                          ({'a', 'ab', 'aab'}, [{'ba', 'b'}], 0.501, set()),
                          ({'a', 'ab', 'aab'}, [{'ba', 'b'}], 0.5, {'a', 'ab', 'aab', 'ba', 'b'}),
                          ({1, 2, 3}, [{2, 3, 4}, {3, 4, 5}], 0.5, {2, 3, 4}),
                          ({1, 2, 3}, [{2, 3, 4}, {3, 4, 5}], 1, {3})])
def test_majority_vote_intersection(this_set, other_sets, majority_threshold, truth):
    result = SetWithMajorityVote.majority_vote_intersection(this_set, *other_sets,
                                                            majority_threshold=majority_threshold)
    assert result == truth


@pytest.mark.parametrize("is_df", [True, False])
@pytest.mark.parametrize("data,baseline,truth", [
    (np.array([1, 2, 3, 4, 5]), 0, np.array([0, 1, 2, 3, 4])),
    (np.array([[1, 2, 3], [-2, 4, 5], [0, 0, -1], [3, -2, 1]]), 1,
     np.array([[4, 5, 6], [1, 7, 8], [3, 3, 2], [6, 1, 4]])),
    (np.array([[[1, 2], [3, 4]], [[5, 6], [7, 8]]]), -1, np.array([[[-1, 0], [1, 2]], [[3, 4], [5, 6]]]))
])
def test_shift_to_baseline(data, baseline, is_df, truth):
    if is_df and len(data.shape) <= 2:
        assert shift_to_baseline(pd.DataFrame(data), baseline).equals(pd.DataFrame(truth))
    else:
        assert np.all(shift_to_baseline(data, baseline) == truth)


def first_test_func():
    pass


def second_test_func(a: str, b: bool, c):
    pass


def third_test_func(a: typing.List[str], b: typing.Callable, c: int = 3, d=None):
    pass


class TestObj:
    def __init__(self):
        pass

    def fourth_test_func(self, a, b: None, c: float = 5.2):
        pass


@pytest.mark.parametrize("func,obj,truth", [
    (first_test_func, None, {}),
    (second_test_func, None, {'a': {'annotation': str, 'default': inspect._empty},
                              'b': {'annotation': bool, 'default': inspect._empty},
                              'c': {'annotation': inspect._empty, 'default': inspect._empty}}),
    (third_test_func, None, {'a': {'annotation': typing.List[str], 'default': inspect._empty},
                             'b': {'annotation': typing.Callable, 'default': inspect._empty},
                             'c': {'annotation': int, 'default': 3},
                             'd': {'annotation': inspect._empty, 'default': None}}),
    ('fourth_test_func', TestObj(), {'a': {'annotation': inspect._empty, 'default': inspect._empty},
                                     'b': {'annotation': None, 'default': inspect._empty},
                                     'c': {'annotation': float, 'default': 5.2}})])
def test_get_signature(func, obj, truth):
    this_signature = get_method_signature(func, obj)
    assert len(this_signature) == len(truth)
    for key, val in truth.items():
        assert key in this_signature
        param = this_signature[key]
        assert param.name == key
        assert param.annotation == val['annotation']
        assert param.default == val['default']


@pytest.mark.parametrize('intervals,expected', [
    ([], 0),
    ([(1, 3)], 3),
    ([(1, 3), (4, 6), (7, 10)], 10),
    ([(4, 6), (1, 3), (7, 10)], 10),
    ([(1, 4), (3, 6), (3, 5), (3, 6), (4, 9)], 9),
    ([(7, 10), (2, 5), (1, 4), (2, 5)], 9),

])
def test_sum_intervals_inclusive(intervals, expected):
    res = sum_intervals_inclusive(intervals)
    assert res == expected


@pytest.mark.parametrize('seconds,expected', [
    (13, '00:13'),
    (0, '00:00'),
    (59.34, '00:59'),
    (60.0, '01:00'),
    (60.2, '01:00'),
    (192.17, '03:12'),
    (13 * 60 + 1.5, '13:01'),
    (100 * 60, '100:00')])
def test_format_time(seconds, expected):
    res = format_time(seconds)
    assert res == expected


@pytest.mark.parametrize('name,expected', [
    ('aname', 'aname'),
    ('name123n', 'name123n'),
    ('camelCase', 'camelCase'),
    ('snake_case', 'snake_case'),
    ('name with spaces ', 'name_with_spaces'),
    ('1name of var', 'var_1name_of_var'),
    ('12345', 'var_12345'),
    ('%asdf&sign', '_asdf_sign'),
    (' ^^more things123 ', '___more_things123')
])
def test_sanitize_variable_name(name, expected):
    res = sanitize_variable_name(name)
    assert res == expected


def test_get_method_readable_name():
    func = lambda x: x + 1
    func.readable_name = "readable name"
    assert get_method_readable_name(func) == "readable name"

    def func2(a, b):
        return a + b

    assert get_method_readable_name(func2) == 'func2'

    func2.readable_name = "readable name"
    assert get_method_readable_name(func2) == "readable name"
