from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from datetime import UTC
from datetime import datetime as dt
from typing import TYPE_CHECKING, Any, TypeVar, get_type_hints, override

import toml
from toml import TomlDecodeError

from cmeow.util._console_io import perr, pwarn
from cmeow.util._defaults import Constant
from cmeow.util._enum import BuildType, ExitCode

if TYPE_CHECKING:
    from argparse import Namespace
    from pathlib import Path

T = TypeVar("T", bound="KeyBase")


@dataclass
class KeyBase(ABC):
    def __init_subclass__(cls) -> None:
        hints = get_type_hints(cls)
        for name in hints:
            if not hasattr(cls, name):
                setattr(cls, name, field(default=None))

    def to_toml(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    @abstractmethod
    def from_toml(cls: type[T], data: dict[str, Any]) -> T:
        pass


def _check_unrecognized_key(key: str, keys: T) -> bool:
    if key not in keys.__dict__:
        pwarn(f"ignoring unrecognized key in `{Constant.project_file}`: {key}")
        return True

    return False


def _check_missing_keys(keys: T) -> None:
    missing_keys = {key for key, val in keys.__dict__.items() if val is None}
    cls_name = type(keys).__name__
    key_prefix = cls_name[: cls_name.find("Keys")].lower()

    if key_prefix:
        key_prefix += "."

    if missing_keys:
        msg_suf = ", ".join(f"<ylw>{key_prefix}{key}</ylw>" for key in missing_keys)
        msg = f"missing keys in {Constant.project_file}: {msg_suf}"
        perr(msg, ExitCode.MISSING_KEYS)


@dataclass
class CmeowKeys(KeyBase):
    version: str

    @override
    @classmethod
    def from_toml(cls, cmeow_keys: dict[str, Any]) -> CmeowKeys:
        keys = cls()

        for key, val in cmeow_keys.items():
            if _check_unrecognized_key(key, keys):
                continue

            setattr(keys, key, val)

        _check_missing_keys(keys)
        return keys


@dataclass
class CmakeKeys(KeyBase):
    version: str

    @classmethod
    def from_parsed_args(cls, args: Namespace) -> CmakeKeys:
        return cls(version=args.cmake)

    @override
    @classmethod
    def from_toml(cls, cmake_keys: dict[str, Any]) -> CmakeKeys:
        keys = cls()

        for key, val in cmake_keys.items():
            if _check_unrecognized_key(key, keys):
                continue

            setattr(keys, key, val)

        _check_missing_keys(keys)
        return keys


@dataclass
class ProjectKeys(KeyBase):
    last_build: dt
    name: str
    version: str
    std: int

    @classmethod
    def from_parsed_args(cls, args: Namespace) -> ProjectKeys:
        if not hasattr(args, "last_build"):
            args.last_build = None

        return cls(
            last_build=args.last_build,
            name=args.project,
            version=args.version,
            std=args.std,
        )

    @override
    def to_toml(self) -> dict[str, dt | str | int | BuildType | None]:
        return {
            "last_build": self.last_build,
            "name": self.name,
            "version": self.version,
            "std": self.std,
        }

    @override
    @classmethod
    def from_toml(cls, project_keys: dict[str, Any]) -> ProjectKeys:
        # TODO: Type validation  # noqa: FIX002, TD002, TD003
        keys = cls()

        for key, val in project_keys.items():
            if _check_unrecognized_key(key, keys):
                continue

            if key == "std":
                keys.std = int(val)
            else:
                setattr(keys, key, val)

        if keys.last_build is None:
            keys.last_build = dt.min.replace(tzinfo=UTC)

        _check_missing_keys(keys)
        return keys


@dataclass
class Keys(KeyBase):
    project: ProjectKeys
    cmeow: CmeowKeys
    cmake: CmakeKeys

    @override
    def to_toml(self) -> dict[str, CmeowKeys | ProjectKeys]:
        return {
            "project": self.project.to_toml(),
            "cmeow": self.cmeow.to_toml(),
            "cmake": self.cmake.to_toml(),
        }

    @override
    @classmethod
    def from_toml(cls, toml_keys: dict[str, Any]) -> Keys:
        keys = cls()

        for key, val in toml_keys.items():
            if _check_unrecognized_key(key, keys):
                continue

            if key == "project":
                keys.project = ProjectKeys.from_toml(val)
            elif key == "cmeow":
                keys.cmeow = CmeowKeys.from_toml(val)
            elif key == "cmake":
                keys.cmake = CmakeKeys.from_toml(val)

        _check_missing_keys(keys)
        return keys

    @classmethod
    def from_toml_file(cls, file: Path) -> None:
        try:
            with file.open("r", encoding="utf-8") as f:
                toml_data = toml.load(f)
                return Keys.from_toml(toml_data)
        except TomlDecodeError as tde:
            perr(f"`{file.name}`: {str(tde).lower()}", ExitCode.DUPLICATE_KEYS)
