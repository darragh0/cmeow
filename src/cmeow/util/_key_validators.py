from abc import ABC, abstractmethod
from datetime import datetime as dt
from typing import Any, override

from semver import VersionInfo

from cmeow.util._console_io import join_choices, perr
from cmeow.util._defaults import Constant
from cmeow.util._enum import ExitCode


class SemverStr:
    def __init__(self, data: str) -> None:
        VersionInfo.parse(data)
        self.data = data

    @staticmethod
    def get_type_info() -> str:
        return "format = {major}.{minor}.{patch}[-stage][+metadata]"

    @staticmethod
    def get_type_name() -> str:
        return "semver str"


class Validator(ABC):
    @staticmethod
    def validate_type(
        key: str,
        value: Any,  # noqa: ANN401
        _type: type[Any],
        key_prefix: str,
        *,
        instance_check: bool = True,
        err_msg: str | None = None,
    ) -> Any:  # noqa: ANN401
        if instance_check and isinstance(value, _type):
            return value

        try:
            if _type is SemverStr:
                return _type(value).data
            return _type(value)
        except ValueError:
            type_name = _type.get_type_name() if hasattr(_type, "get_type_name") else _type.__name__

            if err_msg is None:
                msg = f"key `{key_prefix}{key}`: expected type `{type_name}`, but got `{type(value).__name__}`"
            else:
                msg = f"key `{key_prefix}{key}`: {err_msg}, but got `{type(value).__name__}"

            if hasattr(_type, "get_type_info"):
                msg += f" ({_type.get_type_info()})"

            perr(f"`{Constant.project_file}`: {msg}", ExitCode.INVALID_KEY_TYPE)

    @staticmethod
    @abstractmethod
    def validate(key: str, value: Any, key_prefix: str) -> Any:  # noqa: ANN401
        ...


class DatetimeValidator(Validator):
    @override
    @staticmethod
    def validate(key: str, value: Any, key_prefix: str) -> dt:
        return Validator.validate_type(key, value, dt, key_prefix)


class CmeowVersionValidator(Validator):
    @override
    @staticmethod
    def validate(key: str, value: Any, key_prefix: str) -> str:
        ret: str = Validator.validate_type(key, value, SemverStr, key_prefix, instance_check=False)

        if ret not in Constant.cmeow_versions:
            perr(
                f"`{Constant.project_file}`: key `{key_prefix}{key}`: cmeow version {value} is invalid",
                ExitCode.INVALID_KEY_VAL,
            )

        return ret


class CmakeVersionValidator(Validator):
    @override
    @staticmethod
    def validate(key: str, value: Any, key_prefix: str) -> str:
        return Validator.validate_type(key, value, str, key_prefix, instance_check=False)


class ProjectVersionValidator(Validator):
    @override
    @staticmethod
    def validate(key: str, value: Any, key_prefix: str) -> str:
        return Validator.validate_type(key, value, SemverStr, key_prefix)


class ProjectNameValidator(Validator):
    @override
    @staticmethod
    def validate(key: str, value: Any, key_prefix: str) -> str:
        return Validator.validate_type(key, value, str, key_prefix)


class StdVersionValidator(Validator):
    @override
    @staticmethod
    def validate(key: str, value: Any, key_prefix: str) -> int:
        choices = join_choices(Constant.supported_stds, fmt_spec="02")
        err_msg = "expected `int` value from {choices}"
        ret: int = Validator.validate_type(key, value, int, key_prefix, err_msg=err_msg)

        if ret in Constant.unsupported_stds:
            msg = f"std version <ylw>{ret:02}</ylw> is unsupported. choose from {choices}"
            perr(f"`{Constant.project_file}`: key `{key_prefix}{key}`: {msg}", ExitCode.INVALID_KEY_VAL)

        if ret not in Constant.supported_stds:
            msg = f"std version <ylw>{ret:02}</ylw> is invalid. choose from {choices}"
            perr(f"`{Constant.project_file}`: key `{key_prefix}{key}`: {msg}", ExitCode.INVALID_KEY_VAL)

        return ret


class StrValidator(Validator):
    @override
    @staticmethod
    def validate(key: str, value: Any, key_prefix: str) -> str:
        return Validator.validate_type(key, value, str, key_prefix)


class ReadmeValidator(Validator):
    @override
    @staticmethod
    def validate(key: str, value: Any, key_prefix: str) -> str:
        return str(value)
