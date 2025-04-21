# /// script
# requires-python = ">=3.12"
# ///

from __future__ import annotations

from colorama import just_fix_windows_console

from cmeow.cmd import command
from cmeow.util import init_parser


def main() -> None:
    """Cmeow main entry point."""

    just_fix_windows_console()

    parser = init_parser()
    args = parser.parse_args()

    command.run(args).otherwise(parser.print_help)
