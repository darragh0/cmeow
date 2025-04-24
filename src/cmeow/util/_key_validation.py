from abc import ABC, abstractstaticmethod
from datetime import datetime as dt
from enum import Enum
from typing import TypeVar, override

from semver import VersionInfo

from cmeow.util._console_io import join_choices, perr
from cmeow.util._defaults import Constant
from cmeow.util._enum import ExitCode
from cmeow.util._typing_ext import TOMLValue, ValidatedValue, ValidatorFunc

_T = TypeVar("_T", bound="_CustomType")


class _CustomType(ABC):
    data: _T

    @abstractstaticmethod
    def get_type_info() -> str: ...

    @abstractstaticmethod
    def get_type_name() -> str: ...


class _SemverStr(_CustomType):
    def __init__(self, data: str) -> None:
        VersionInfo.parse(data)
        self.data = data

    @override
    @staticmethod
    def get_type_info() -> str:
        return (
            'format: <ylw>"</ylw>{<ylw>major</ylw>}.{<ylw>minor</ylw>}.{<ylw>patch</ylw>}'
            '[<ylw>-stage</ylw>][<ylw>+metadata</ylw>]<ylw>"</ylw>'
        )

    @override
    @staticmethod
    def get_type_name() -> str:
        return "semver str"


def _validate_type(
    key: str,
    value: TOMLValue,
    _type: type[ValidatedValue],
    key_prefix: str,
    *,
    err_msg: str | None = None,
) -> ValidatedValue:
    if not issubclass(_type, _CustomType) and isinstance(value, _type):
        return value

    try:
        if issubclass(_type, _CustomType):
            return _type(value).data
        return _type(value)
    except (ValueError, TypeError):
        type_name = _type.get_type_name() if issubclass(_type, _CustomType) else _type.__name__

        msg = f"key <ylw>{key_prefix}{key}</ylw>: "
        if err_msg is None:
            msg += f"expected type `{type_name}`"
        else:
            msg += err_msg

        if hasattr(_type, "get_type_info"):
            msg += f" ({_type.get_type_info()})"

        msg += f", but got `{type(value).__name__}`"

        perr(f"`{Constant.project_file}`: {msg}", ExitCode.INVALID_KEY_TYPE)


def validate_dt(key: str, value: TOMLValue, *, key_prefix: str) -> dt:
    return _validate_type(key, value, dt, key_prefix)


def validate_cmeow_version(key: str, value: TOMLValue, *, key_prefix: str) -> str:
    ret: str = _validate_type(key, value, _SemverStr, key_prefix)

    if ret not in Constant.cmeow_versions:
        perr(
            f"`{Constant.project_file}`: key `{key_prefix}{key}`: cmeow version {value} is invalid",
            ExitCode.INVALID_KEY_VAL,
        )

    return ret


def validate_cmake_version(key: str, value: TOMLValue, *, key_prefix: str) -> str:
    return _validate_type(key, value, str, key_prefix)


def validate_semver(key: str, value: TOMLValue, *, key_prefix: str) -> str:
    return _validate_type(key, value, _SemverStr, key_prefix)


def validate_proj_name(key: str, value: TOMLValue, *, key_prefix: str) -> str:
    return _validate_type(key, value, str, key_prefix)


def validate_std_version(key: str, value: TOMLValue, *, key_prefix: str) -> int:
    choices = join_choices(Constant.supported_stds, fmt_spec="02")
    err_msg = "expected `int` value from {choices}"
    ret: int = _validate_type(key, value, int, key_prefix, err_msg=err_msg)

    if ret in Constant.unsupported_stds:
        msg = f"std version <ylw>{ret:02}</ylw> is unsupported. choose from {choices}"
        perr(f"`{Constant.project_file}`: key `{key_prefix}{key}`: {msg}", ExitCode.INVALID_KEY_VAL)

    if ret not in Constant.supported_stds:
        msg = f"std version <ylw>{ret:02}</ylw> is invalid. choose from {choices}"
        perr(f"`{Constant.project_file}`: key `{key_prefix}{key}`: {msg}", ExitCode.INVALID_KEY_VAL)

    return ret


def validate_str(key: str, value: TOMLValue, *, key_prefix: str) -> str:
    return _validate_type(key, value, str, key_prefix)


def validate_file(key: str, value: TOMLValue, *, key_prefix: str) -> str:
    return _validate_type(key, value, str, key_prefix)


class Validator(Enum):
    DATETIME: ValidatorFunc = validate_dt
    CMEOW_VER: ValidatorFunc = validate_cmeow_version
    CMAKE_VER: ValidatorFunc = validate_cmake_version
    SEMVER: ValidatorFunc = validate_semver
    PROJECT_NAME: ValidatorFunc = validate_proj_name
    STD_VER: ValidatorFunc = validate_std_version
    STR: ValidatorFunc = validate_str
    FILE: ValidatorFunc = validate_file
