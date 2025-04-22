from __future__ import annotations

from argparse import ArgumentTypeError
from pathlib import Path

from cmeow.util._console_io import join_choices
from cmeow.util._defaults import BuildType, Constant


def build_type(value: str) -> BuildType:
    choices = join_choices(BuildType._value2member_map_)

    if value.strip().lower() not in BuildType:
        msg = f"expected value from {choices}"
        raise ArgumentTypeError(msg)

    return BuildType(value)


def c_std_version(value: str) -> int:
    choices = join_choices(Constant.supported_stds, fmt_spec="02")
    err_msg = "expected {err_msg_infix} value from {choices}"

    try:
        version = int(value)
    except ValueError as ve:
        msg = err_msg.format(err_msg_infix="`int`", choices=choices)
        raise ArgumentTypeError(msg) from ve

    if version in Constant.unsupported_stds:
        msg = f"version <ylw>{version:02}</ylw> is unsupported. choose from {choices}"
        raise ArgumentTypeError(msg)

    if version not in Constant.supported_stds:
        msg = err_msg.format(err_msg_infix="\b", choices=choices)
        raise ArgumentTypeError(msg)

    return version


def cmake_version(value: str) -> str:
    return value


def dir_name(value: str) -> str:
    return value


def directory(value: str) -> Path:
    return Path(value)


def proj_name(value: str) -> Path:
    return value
