from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field as dataclass_field
from datetime import UTC
from datetime import datetime as dt
from functools import partial
from types import NoneType, UnionType
from typing import TYPE_CHECKING, ClassVar, TypeVar, get_type_hints, override

import toml
from toml import TomlDecodeError

from cmeow.util._console_io import perr, pwarn
from cmeow.util._defaults import Constant
from cmeow.util._enum import ExitCode
from cmeow.util._key_validation import Validator

if TYPE_CHECKING:
    from pathlib import Path

    from cmeow.util._typing_ext import (
        TOML,
        KeysDict,
        ValidatorPartial,
    )


_K = TypeVar("_K", bound="_KeysBase")


@dataclass
class _KeysBase:
    def __init_subclass__(cls) -> None:
        field2type_map = get_type_hints(cls)

        optional: set[str] = set()
        required: set[str] = set()
        validators: dict[str, ValidatorPartial] = {}

        # writeln(f"<cyn>*key_group = {cls.__name__}:*</cyn>")
        for field, hint in field2type_map.items():
            if field.startswith("__"):
                continue

            # writeln(f"<grn>*field = {field}*:</grn>", indent=2)
            if hasattr(cls, field):
                validator = getattr(cls, field)
                validators[field] = partial(validator, field, key_prefix=cls.__group__ + ".")
                # writeln(f"- validator = `{validator.__name__}`", indent=4)

            if isinstance(hint, UnionType) and NoneType in hint.__args__:
                _types = " | ".join(typ.__name__ for typ in hint.__args__ if typ is not NoneType)
                optional.add(field)
                setattr(cls, field, dataclass_field(default=None))
                # writeln(f"- type = `{_types}`", indent=4)
                # writeln("- optional = True", indent=4)
            else:
                # writeln(f"- type = `{hint.__name__}`", indent=4)
                required.add(field)

        # writeln()
        cls.__validators__ = validators
        cls.__optional_fields__ = optional
        cls.__required_fields__ = required

    @classmethod
    def from_toml(cls, _toml: TOML) -> _K:
        field2type_map = get_type_hints(cls)
        keys: KeysDict = {}

        for key, val in _toml.items():
            if cls.check_unrecognized_key(key):
                continue

            _type = field2type_map[key]
            if not isinstance(_type, UnionType) and issubclass(_type, _KeysBase):
                # delegate `from_toml` to subclass
                keys[key] = _type.from_toml(val)
                continue

            if key in cls.__validators__:
                keys[key] = cls.__validators__[key](val)
            else:
                keys[key] = val

        cls.check_missing_keys(keys)
        return cls(**keys)

    def to_toml(self) -> KeysDict:
        _toml: KeysDict = {}
        for key, val in vars(self).items():
            if isinstance(val, _KeysBase):
                _toml[key] = val.to_toml()
            else:
                _toml[key] = val

        return _toml

    @classmethod
    def check_unrecognized_key(cls, key: str) -> bool:
        if key not in cls.__dataclass_fields__:
            pwarn(f"ignoring unrecognized key in `{Constant.project_file}`: {key}")
            return True

        return False

    @classmethod
    def check_missing_keys(cls, keys: KeysDict) -> None:
        key_prefix: str
        key_desc: str
        if cls.__group__ == "ROOT":
            key_prefix = ""
            key_desc = "table"
        else:
            key_prefix = cls.__group__ + "."
            key_desc = "key"

        missing_keys = {key for key in cls.__required_fields__ if key not in keys}

        if missing_keys:
            msg_suf = ", ".join(f"<ylw>{key_prefix}{key}</ylw>" for key in missing_keys)
            msg = f"missing {key_desc}(s) in {Constant.project_file}: {msg_suf}"
            perr(msg, ExitCode.MISSING_KEYS)


def _file_keys(cls: type[_K]) -> type[_K]:
    return dataclass(kw_only=True)(cls)


@_file_keys
class CmeowKeys(_KeysBase):
    __group__: ClassVar[str] = "cmeow"

    version: str = Validator.CMEOW_VER


@_file_keys
class CmakeKeys(_KeysBase):
    __group__: ClassVar[str] = "cmake"

    version: str = Validator.CMAKE_VER


@_file_keys
class ProjectKeys(_KeysBase):
    __group__: ClassVar[str] = "project"

    last_build: dt | None = Validator.DATETIME
    name: str = Validator.PROJECT_NAME
    version: str = Validator.SEMVER
    description: str | None = Validator.STR
    readme: str | None = Validator.FILE
    std: int = Validator.STD_VER

    @override
    @classmethod
    def from_toml(cls, project_keys: TOML) -> ProjectKeys:
        _instance = super().from_toml(project_keys)
        if _instance.last_build is None:
            _instance.last_build = dt.min.replace(tzinfo=UTC)
        return _instance


@_file_keys
class DependenciesKeys(_KeysBase):
    __group__: ClassVar[str] = "dependencies"


@_file_keys
class Keys(_KeysBase):
    __group__: ClassVar[str] = "ROOT"

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
