from argparse import Namespace
from collections.abc import Callable
from typing import ClassVar, Self

from cmeow.command._command import cmd_map
from cmeow.command._parser import init_parser
from cmeow.util import ExitCode, perr, writeln


class _AwesomeDict(dict):
    _success: ClassVar[bool] = False

    def __init__(self, val: dict[str, Callable[[Namespace], None]]) -> None:
        super().__init__(val)

    def run(self, args: Namespace) -> Self:
        if args.command in self:
            try:
                self[args.command]["function"](args)
            except KeyboardInterrupt:
                if (fail_msg := self[args.command].get("fail_msg", None)) is not None:
                    warn_pre = "<ylw>*[warning::interrupt]*</ylw> "
                    writeln()
                    perr(fail_msg, ExitCode.KB_INT, prefix=warn_pre)
                else:
                    raise
            else:
                self._success = True

        return self

    def otherwise(self, func: Callable[[], None]) -> None:
        if not self._success:
            func()


command = _AwesomeDict(cmd_map)

__all__ = [
    "command",
    "init_parser",
]
