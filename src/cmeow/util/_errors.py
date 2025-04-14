from __future__ import annotations

from enum import IntEnum, auto


class ExitCode(IntEnum):
    SUCCESS = auto()
    FAILURE = auto()
    INVALID_CMD = auto()
    INVALID_ARGS = auto()
    PROJ_EXISTS = auto()
    DIR_EXISTS = auto()
    CANNOT_CREATE_PROJ = auto()
    PROJ_NOT_EXISTS = auto()
    INVALID_KEYS = auto()
    MISSING_KEYS = auto()
    DIR_NOT_EXISTS = auto()
