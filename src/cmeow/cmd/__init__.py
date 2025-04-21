from argparse import Namespace
from collections.abc import Callable
from typing import ClassVar, Self

from cmeow.cmd._cmd import cmd_map


class _AwesomeDict(dict):
    _success: ClassVar[bool] = False

    def __init__(self, val: dict[str, Callable[[Namespace], None]]) -> None:
        super().__init__(val)

    def run(self, args: Namespace) -> Self:
        if args.command in self:
            self[args.command](args)
            self._success = True
        return self

    def otherwise(self, func: Callable[[], None]) -> None:
        if not self._success:
            func()


command = _AwesomeDict(cmd_map)

__all__ = [
    "command",
]
