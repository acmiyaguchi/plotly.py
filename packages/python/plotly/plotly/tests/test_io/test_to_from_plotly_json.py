import pytest
import plotly.io.json as pio
import plotly.graph_objects as go
import numpy as np
import pandas as pd
import json
import datetime
import sys
from pytz import timezone
from _plotly_utils.optional_imports import get_module

orjson = get_module("orjson")

eastern = timezone("US/Eastern")


# Testing helper
def build_json_opts(pretty=False):
    opts = {"sort_keys": True}
    if pretty:
        opts["indent"] = 2
    else:
        opts["separators"] = (",", ":")
    return opts


def to_json_test(value, pretty=False):
    return json.dumps(value, **build_json_opts(pretty=pretty))


def isoformat_test(dt_value):
    if isinstance(dt_value, np.datetime64):
        return str(dt_value)
    elif isinstance(dt_value, datetime.datetime):
        return dt_value.replace(tzinfo=None).isoformat()
    else:
        raise ValueError("Unsupported date type: {}".format(type(dt_value)))


def build_test_dict(value):
    return dict(a=value, b=[3, value], c=dict(Z=value))


def build_test_dict_string(value_string, pretty=False):
    if pretty:
        non_pretty_str = build_test_dict_string(value_string, pretty=False)
        return to_json_test(json.loads(non_pretty_str), pretty=True)
    else:
        value_string = str(value_string).replace(" ", "")
        return """{"a":%s,"b":[3,%s],"c":{"Z":%s}}""" % tuple([value_string] * 3)


def check_roundtrip(value, engine, pretty):
    encoded = pio.to_json_plotly(value, engine=engine, pretty=pretty)
    decoded = pio.from_json_plotly(encoded, engine=engine)
    reencoded = pio.to_json_plotly(decoded, engine=engine, pretty=pretty)
    assert encoded == reencoded

    # Check from_plotly_json with bytes on Python 3
    if sys.version_info.major == 3:
        encoded_bytes = encoded.encode("utf8")
        decoded_from_bytes = pio.from_json_plotly(encoded_bytes, engine=engine)
        assert decoded == decoded_from_bytes


# Fixtures
if orjson is not None:
    engines = ["json", "orjson", "legacy", "auto"]
else:
    engines = ["json", "legacy", "auto"]


@pytest.fixture(scope="module", params=engines)
def engine(request):
    return request.param


@pytest.fixture(scope="module", params=[False])
def pretty(request):
    return request.param


@pytest.fixture(scope="module", params=["float64", "int32", "uint32"])
def graph_object(request):
    return request.param


@pytest.fixture(scope="module", params=["float64", "int32", "uint32"])
def numeric_numpy_array(request):
    dtype = request.param
    return np.linspace(-5, 5, 4, dtype=dtype)


@pytest.fixture(scope="module")
def object_numpy_array(request):
    return np.array(["a", 1, [2, 3]])


@pytest.fixture(
    scope="module",
    params=[
        datetime.datetime(2003, 7, 12, 8, 34, 22),
        datetime.datetime.now(),
        np.datetime64(datetime.datetime.utcnow()),
        eastern.localize(datetime.datetime(2003, 7, 12, 8, 34, 22)),
        eastern.localize(datetime.datetime.now()),
    ],
)
def datetime_value(request):
    return request.param


@pytest.fixture(
    params=[
        lambda a: pd.DatetimeIndex(a),  # Pandas DatetimeIndex
        lambda a: pd.Series(pd.DatetimeIndex(a)),  # Pandas Datetime Series
        lambda a: pd.DatetimeIndex(a).values,  # Numpy datetime64 array
    ]
)
def datetime_array(request, datetime_value):
    return request.param([datetime_value] * 3)


# Encoding tests
def test_graph_object_input(engine, pretty):
    scatter = go.Scatter(x=[1, 2, 3], y=np.array([4, 5, 6]))
    result = pio.to_json_plotly(scatter, engine=engine)
    expected = """{"type":"scatter","x":[1,2,3],"y":[4,5,6]}"""
    assert result == expected
    check_roundtrip(result, engine=engine, pretty=pretty)


def test_numeric_numpy_encoding(numeric_numpy_array, engine, pretty):
    value = build_test_dict(numeric_numpy_array)
    result = pio.to_json_plotly(value, engine=engine, pretty=pretty)

    array_str = to_json_test(numeric_numpy_array.tolist())
    expected = build_test_dict_string(array_str, pretty=pretty)
    assert result == expected
    check_roundtrip(result, engine=engine, pretty=pretty)


def test_object_numpy_encoding(object_numpy_array, engine, pretty):
    value = build_test_dict(object_numpy_array)
    result = pio.to_json_plotly(value, engine=engine, pretty=pretty)

    array_str = to_json_test(object_numpy_array.tolist())
    expected = build_test_dict_string(array_str)
    assert result == expected
    check_roundtrip(result, engine=engine, pretty=pretty)


def test_datetime(datetime_value, engine, pretty):
    if engine == "legacy":
        pytest.skip("legacy encoder doesn't strip timezone from scalar datetimes")

    value = build_test_dict(datetime_value)
    result = pio.to_json_plotly(value, engine=engine, pretty=pretty)
    expected = build_test_dict_string('"{}"'.format(isoformat_test(datetime_value)))
    assert result == expected
    check_roundtrip(result, engine=engine, pretty=pretty)


def test_datetime_arrays(datetime_array, engine, pretty):
    value = build_test_dict(datetime_array)
    result = pio.to_json_plotly(value, engine=engine)

    if isinstance(datetime_array, pd.Series):
        dt_values = [d.isoformat() for d in datetime_array.dt.to_pydatetime().tolist()]
    elif isinstance(datetime_array, pd.DatetimeIndex):
        dt_values = [d.isoformat() for d in datetime_array.to_pydatetime().tolist()]
    else:  # numpy datetime64 array
        dt_values = datetime_array.tolist()

    array_str = to_json_test(dt_values)
    expected = build_test_dict_string(array_str)
    assert result == expected
    check_roundtrip(result, engine=engine, pretty=pretty)
