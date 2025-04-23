from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from dataclasses import field as dataclass_field
from datetime import UTC
from datetime import datetime as dt
from types import NoneType, UnionType
from typing import TYPE_CHECKING, Any, TypeVar, get_type_hints, override

import toml
from toml import TomlDecodeError

from cmeow.util._console_io import perr, pwarn
from cmeow.util._defaults import Constant
from cmeow.util._enum import ExitCode
from cmeow.util._key_validators import (
    CmakeVersionValidator,
    CmeowVersionValidator,
    DatetimeValidator,
    ProjectNameValidator,
    ProjectVersionValidator,
    ReadmeValidator,
    StdVersionValidator,
    StrValidator,
    Validator,
)

if TYPE_CHECKING:
    from pathlib import Path

    from cmeow.util._typing import TOML, CmakeKeysDict, CmeowKeysDict, DependenciesKeysDict, KeysDict, ProjectKeysDict

_T = TypeVar("_T", bound="_KeyBase")


def _check_unrecognized_key(cls: type[_T], key: str) -> bool:
    if key not in cls.__dataclass_fields__:
        pwarn(f"ignoring unrecognized key in `{Constant.project_file}`: {key}")
        return True

    return False


def _check_missing_keys(cls: type[_T], keys: dict[str, Any], key_prefix: str | None = None) -> None:
    if key_prefix is None:
        key_prefix = ""

    missing_keys = {key for key in cls.__required_fields__ if key not in keys}
    if missing_keys:
        msg_suf = ", ".join(f"<ylw>{key_prefix}{key}</ylw>" for key in missing_keys)
        msg = f"missing keys in {Constant.project_file}: {msg_suf}"
        perr(msg, ExitCode.MISSING_KEYS)


@dataclass
class _KeyBase(ABC):
    def __init_subclass__(cls) -> None:
        optional = set()
        required = set()
        for field, hint in get_type_hints(cls).items():
            if isinstance(hint, UnionType) and NoneType in hint.__args__:
                optional.add(field)
                setattr(cls, field, dataclass_field(default=None))
            else:
                required.add(field)

        cls.__optional_fields__ = optional
        cls.__required_fields__ = required

    @classmethod
    @abstractmethod
    def from_toml(cls: type[_T], data: dict[str, Any]) -> _T: ...

    def to_toml(self) -> CmeowKeysDict | CmakeKeysDict | ProjectKeysDict | KeysDict:
        _toml = {}
        for key, val in vars(self).items():
            if isinstance(val, _KeyBase):
                _toml[key] = val.to_toml()
            else:
                _toml[key] = val

        return _toml


def _file_keys(cls: type[_T]) -> type[_T]:
    return dataclass(kw_only=True)(cls)


@_file_keys
class CmeowKeys(_KeyBase):
    version: str

    @staticmethod
    def get_validators() -> dict[str, Validator]:
        return {"version": CmeowVersionValidator}

    @override
    @classmethod
    def from_toml(cls, cmeow_keys: TOML) -> CmeowKeys:
        keys: CmeowKeysDict = {}
        validators = cls.get_validators()

        for key, val in cmeow_keys.items():
            if _check_unrecognized_key(cls, key):
                continue

            validator = validators[key]
            keys[key] = validator.validate(key, val, "cmeow.")

        _check_missing_keys(cls, keys, "cmeow.")
        return cls(**keys)


@_file_keys
class CmakeKeys(_KeyBase):
    version: str

    @staticmethod
    def get_validators() -> dict[str, Validator]:
        return {"version": CmakeVersionValidator}

    @override
    @classmethod
    def from_toml(cls, cmake_keys: TOML) -> CmakeKeys:
        keys: CmakeKeysDict = {}
        validators = cls.get_validators()

        for key, val in cmake_keys.items():
            if _check_unrecognized_key(cls, key):
                continue

            validator = validators[key]
            keys[key] = validator.validate(key, val, "cmake.")

        _check_missing_keys(cls, keys, "cmake.")
        return cls(**keys)


@_file_keys
class ProjectKeys(_KeyBase):
    last_build: dt | None
    name: str
    version: str
    description: str | None
    readme: str | None
    std: int

    @staticmethod
    def get_validators() -> dict[str, Validator]:
        return {
            "last_build": DatetimeValidator,
            "name": ProjectNameValidator,
            "version": ProjectVersionValidator,
            "description": StrValidator,
            "readme": ReadmeValidator,
            "std": StdVersionValidator,
        }

    @override
    @classmethod
    def from_toml(cls, project_keys: TOML) -> ProjectKeys:
        # TODO: Type validation  # noqa: FIX002, TD002, TD003
        keys: ProjectKeysDict = {}
        validators = cls.get_validators()

        for key, val in project_keys.items():
            if _check_unrecognized_key(cls, key):
                continue

            validator = validators[key]
            keys[key] = validator.validate(key, val, "project.")

        if "last_build" not in keys:
            keys["last_build"] = dt.min.replace(tzinfo=UTC)

        _check_missing_keys(cls, keys, "project.")
        return cls(**keys)


@_file_keys
class DependenciesKeys(_KeyBase):
    @override
    @classmethod
    def from_toml(cls, dep_keys: TOML) -> DependenciesKeys:
        keys: DependenciesKeysDict = {}

        for key in dep_keys:
            if _check_unrecognized_key(cls, key):
                continue

        _check_missing_keys(cls, keys, "dependencies.")
        return cls(**keys)


@_file_keys
class Keys(_KeyBase):
    project: ProjectKeys
    dependencies: DependenciesKeys
    cmeow: CmeowKeys
    cmake: CmakeKeys

    @staticmethod
    def from_toml_file(file: Path) -> None:
        try:
            with file.open("r", encoding="utf-8") as f:
                toml_data = toml.load(f)
                return Keys.from_toml(toml_data)
        except TomlDecodeError as tde:
            perr(f"`{file.name}`: {str(tde).lower()}", ExitCode.DUPLICATE_KEYS)

    @override
    @classmethod
    def from_toml(cls, toml_keys: TOML) -> Keys:
        keys: KeysDict = {}

        for key, val in toml_keys.items():
            if _check_unrecognized_key(cls, key):
                continue

            if key == "project":
                keys["project"] = ProjectKeys.from_toml(val)
            elif key == "cmeow":
                keys["cmeow"] = CmeowKeys.from_toml(val)
            elif key == "cmake":
                keys["cmake"] = CmakeKeys.from_toml(val)
            elif key == "dependencies":
                keys["dependencies"] = DependenciesKeys.from_toml(val)

        _check_missing_keys(cls, keys)
        return cls(**keys)
