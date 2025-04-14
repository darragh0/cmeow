from argparse import ArgumentTypeError
from pathlib import Path

from cmeow.util._console_io import Style


def c_std_version(value: int) -> int:
    not_supported = (98, 3)
    supported = (11, 14, 17, 20)
    colored_vals = ", ".join(f"{Style.YLW}{val:02}{Style.RST}" for val in supported)
    default_err = ArgumentTypeError(f"expected value from ({colored_vals})")

    try:
        version = int(value)
    except ValueError as ve:
        raise default_err from ve

    if version in not_supported:
        msg = f"{Style.YLW}{version:02}{Style.RST} is unsupported ... choose from ({colored_vals})"
        raise ArgumentTypeError(msg)

    if version not in supported:
        raise default_err

    return version


def cmake_version(version: str) -> str:
    return version


def dir_name(value: str) -> str:
    # TODO: Argument validation  # noqa: FIX002, TD002, TD003
    return value


def directory(path: str) -> Path:
    return Path(path)
