import pytest
from pydantic import ValidationError

from connection import Connection


def test_defaults() -> None:
    """A minimal connection has capacity 1."""
    conn = Connection(zone_a="a", zone_b="b")
    assert conn.max_link_capacity == 1


def test_self_loop_rejected() -> None:
    """A connection cannot link a zone to itself."""
    with pytest.raises(ValidationError):
        Connection(zone_a="a", zone_b="a")


def test_capacity_must_be_positive() -> None:
    """max_link_capacity is validated as >= 1."""
    with pytest.raises(ValidationError):
        Connection(zone_a="a", zone_b="b", max_link_capacity=0)


def test_connects() -> None:
    """connects() reports whether a zone is one of the two endpoints."""
    conn = Connection(zone_a="a", zone_b="b")
    assert conn.connects("a")
    assert conn.connects("b")
    assert not conn.connects("c")


def test_other() -> None:
    """other() returns the endpoint opposite the one given."""
    conn = Connection(zone_a="a", zone_b="b")
    assert conn.other("a") == "b"
    assert conn.other("b") == "a"
