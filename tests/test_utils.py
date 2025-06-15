import pytest
from enum import Enum
from nomos.utils.utils import create_base_model, create_enum
from nomos.utils.url import join_urls


def test_create_base_model_no_description():
    Model = create_base_model("TestModel", {"a": {"type": int, "description": ""}})
    assert Model.model_fields["a"].description is None


def test_create_base_model_missing_description():
    Model = create_base_model("TestModel", {"a": {"type": int}})
    assert Model.model_fields["a"].description is None


def test_create_enum_basic():
    Color = create_enum("Color", {"RED": 1, "BLUE": 2})
    assert issubclass(Color, Enum)
    assert Color.RED.value == 1
    assert [member.name for member in Color] == ["RED", "BLUE"]


def test_join_urls():
    assert (
        join_urls("http://example.com", "path/to/resource")
        == "http://example.com/path/to/resource"
    )
    assert (
        join_urls("http://example.com", "/path/to/resource")
        == "http://example.com/path/to/resource"
    )
    assert (
        join_urls("http://example.com/", "path/to/resource")
        == "http://example.com/path/to/resource"
    )
    assert join_urls("http://example.com", "") == "http://example.com"
