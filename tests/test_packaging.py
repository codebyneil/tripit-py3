"""Packaging details that downstream projects depend on."""

from importlib.resources import files


def test_ships_py_typed_marker() -> None:
    # PEP 561: without this (empty) marker file, mypy won't use tripit's
    # inline type hints in projects that depend on it.
    assert files("tripit").joinpath("py.typed").is_file()
