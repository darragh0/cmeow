from datetime import datetime as dt
from typing import NotRequired, TypedDict

type TOMLValue = str | int | float | bool | list[TOMLValue] | dict[str, TOMLValue]
type TOML = dict[str, TOMLValue]


class CmeowKeysDict(TypedDict):
    version: str


class CmakeKeysDict(TypedDict):
    version: str


class ProjectKeysDict(TypedDict):
    last_build: NotRequired[dt]
    name: str
    version: str
    description: NotRequired[str]
    readme: NotRequired[str]
    std: int


class DependenciesKeysDict(TypedDict): ...


class KeysDict(TypedDict):
    project: ProjectKeysDict
    dependencies: DependenciesKeysDict
    cmeow: CmeowKeysDict
    cmake: CmakeKeysDict
