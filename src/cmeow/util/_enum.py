from collections.abc import Iterator
from enum import EnumMeta, IntEnum, StrEnum, auto
from typing import Self


class _BuildTypeMeta(EnumMeta):
    def __contains__(cls, b: str) -> bool:
        return b in cls._value2member_map_

    def __iter__(cls) -> Iterator[str]:
        return iter(cls._value2member_map_)


class BuildType(StrEnum, metaclass=_BuildTypeMeta):
    DEBUG = "debug"
    RELEASE = "release"

    def opposite(self) -> Self:
        return BuildType.DEBUG if self == BuildType.DEBUG else BuildType.RELEASE


class ExitCode(IntEnum):
    SUCCESS = auto()
    FAILURE = auto()
    KB_INT = auto()
    INVALID_CMD = auto()
    INVALID_ARGS = auto()
    PROJ_EXISTS = auto()
    DIR_EXISTS = auto()
    CANNOT_CREATE_PROJ = auto()
    PROJ_NOT_EXISTS = auto()
    INVALID_KEY_TYPE = auto()
    INVALID_KEY_VAL = auto()
    DUPLICATE_KEYS = auto()
    MISSING_KEYS = auto()
    DIR_NOT_EXISTS = auto()
