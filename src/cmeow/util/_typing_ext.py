from collections.abc import Callable
from datetime import datetime as dt
from typing import NotRequired, TypedDict, TypeVar

ValidatedValue = TypeVar("ValidatedValue")

type TOMLValue = str | int | float | bool | list[TOMLValue] | dict[str, TOMLValue]
type TOML = dict[str, TOMLValue]
type ValidatorFunc = Callable[[str, TOMLValue, str], ValidatedValue]
type ValidatorPartial = Callable[[str], ValidatedValue]


class _CmeowKeysDict(TypedDict):
    version: str


class _CmakeKeysDict(TypedDict):
    version: str


class _ProjectKeysDict(TypedDict):
    last_build: NotRequired[dt]
    name: str
    version: str
    description: NotRequired[str]
    readme: NotRequired[str]
    std: int


class _DependenciesKeysDict(TypedDict): ...


class _RootKeysDict(TypedDict):
    project: _ProjectKeysDict
    dependencies: _DependenciesKeysDict
    cmeow: _CmeowKeysDict
    cmake: _CmakeKeysDict


type KeysDict = _CmeowKeysDict | _CmakeKeysDict | _ProjectKeysDict | _DependenciesKeysDict | _RootKeysDict
