from __future__ import annotations

from argparse import ArgumentTypeError
from pathlib import Path
from typing import TYPE_CHECKING

from cmeow.util._console_io import Style
from cmeow.util._defaults import BuildType

if TYPE_CHECKING:
    from collections.abc import Iterable
    from typing import Any


def _join_choices(choices: Iterable[Any], *, fmt_spec: str | None = None) -> str:
    if fmt_spec is None:
        fmt_spec = ""
    joined = ", ".join(f"{Style.YLW}{val:{fmt_spec}}{Style.RST}" for val in choices)
    return f"({joined})"


def build_type(value: str) -> BuildType:
    choices = _join_choices(BuildType._hashable_values_)

    if value.strip().lower() not in BuildType:
        msg = f"expected value from {choices}"
        raise ArgumentTypeError(msg)

    return BuildType(value)


def c_std_version(value: int) -> int:
    not_supported = (98, 3)
    supported = (11, 14, 17, 20)
    choices = _join_choices(supported, fmt_spec="02")
    default_err = ArgumentTypeError(f"expected value from {choices}")

    try:
        version = int(value)
    except ValueError as ve:
        raise default_err from ve

    if version in not_supported:
        msg = f"{Style.YLW}{version:02}{Style.RST} is unsupported ... choose from {choices}"
        raise ArgumentTypeError(msg)

    if version not in supported:
        raise default_err

    return version


def cmake_version(value: str) -> str:
    return value


def dir_name(value: str) -> str:
    return value


def directory(value: str) -> Path:
    return Path(value)


def proj_name(value: str) -> Path:
    return value
