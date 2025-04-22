# /// script
# requires-python = ">=3.12"
# ///

from __future__ import annotations

from colorama import just_fix_windows_console

from cmeow.command import command, init_parser
from cmeow.util import ExitCode, perr


def main() -> None:
    """Cmeow main entry point."""

    try:
        just_fix_windows_console()
        parser = init_parser()
        args = parser.parse_args()
        command.run(args).otherwise(parser.print_help)

    except KeyboardInterrupt as ki:
        msg = f"`cmeow {args.command if args.command else '\b'}` was interrupted"
        if str(ki):
            msg += f":{ki!s}"
        perr(msg, ExitCode.KB_INT)
