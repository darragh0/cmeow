from __future__ import annotations

import re
from argparse import ONE_OR_MORE, OPTIONAL, Action, ArgumentError, ArgumentParser, ArgumentTypeError
from gettext import ngettext
from sys import exit as sexit
from sys import stderr, stdout
from typing import TYPE_CHECKING, Any, ClassVar, NoReturn, TextIO, override

from cmeow.util._console_io import Style as S  # noqa: N817
from cmeow.util._console_io import perr
from cmeow.util._errors import ExitCode

if TYPE_CHECKING:
    from collections import Namespace
    from collections.abc import Sequence


class _ArgError(ArgumentError):
    @override
    def __str__(self) -> str:
        if self.argument_name is None:
            return super().__str__()

        return f"argument {S.BLD}{S.CYN}{self.argument_name}{S.RST}: {self.message}"


class ArgParser(ArgumentParser):
    _subparsers_short_help: ClassVar[bool] = False

    @override
    def __init__(
        self,
        *args: Any,
        version: str | None = None,
        epilog: bool = False,
        short_version: bool = False,
        short_help: bool = False,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs, add_help=False)

        if short_help:
            ArgParser._subparsers_short_help = True

        help_args = ("-h", "--help") if self._subparsers_short_help else ("--help",)
        ver_args = ("-V", "--version") if short_version else ("--version",)

        self.add_argument(*help_args, action="help", help=f"Show help for `{self.prog}` and exit.")

        if version is not None:
            self.add_argument(
                *ver_args,
                action="version",
                version=f"{self.prog} v{version}",
                help=f"Show {self.prog} version and exit.",
            )

        if epilog:
            self.epilog = (
                f"Run {S.BLD}{S.CYN}cmeow{S.RST} {S.CYN}<command> {S.BLD}"
                f"--help{S.RST} for information on a specific command."
            )

        self._positionals.title = "Arguments"
        self._optionals.title = "Options"

    def _format_entry(self, entry: str) -> str:
        sep = entry.rfind("  ") + 2

        _left, _right = entry[:sep], entry[sep:]
        pad = len(_left)

        left: str = ""
        right: str = ""

        for word in _left.rstrip().split():
            if word.startswith("<"):
                left += f" {S.BLU}{word}{S.RST}"
                pad += len(S.CYN) + len(S.RST)
            elif word.endswith(","):
                left += f"{S.BLD}{S.CYN}{word[:-1]}{S.RST}, "
                pad += len(S.BLD) + len(S.CYN) + len(S.RST)
            else:
                left += f"{S.BLD}{S.CYN}{word}{S.RST}"
                pad += len(S.BLD) + len(S.CYN) + len(S.RST)

        default = _right.rfind("[default:")
        right = f"{_right[:default]}{S.YLW}{_right[default:]}{S.RST}" if default != -1 else _right

        return f"{left:<{pad}} {right}"

    @override
    def format_usage(self) -> str:
        usage_str: str = f"{S.BLD}{S.GRN}Usage: {S.CYN}{self.prog}{S.RST}{S.CYN} "

        headings: set[str] = set()
        for action_group in self._action_groups:
            if action_group._group_actions:  # noqa: SLF001
                headings.add(action_group.title)

        usage_strs = []
        if "Options" in headings:
            usage_strs.append("[OPTIONS]")

        if "Commands" in headings:
            usage_strs.append("<COMMAND>")

        if "Arguments" in headings:
            usage_strs.append("[ARGUMENTS]")

        usage_str += f"{' '.join(usage_strs)}{S.RST}"
        return usage_str

    @override
    def print_usage(self, file: TextIO) -> None:
        print(self.format_usage(), file=stdout if file is None else file)

    @override
    def format_help(self) -> str:
        help_out: list[str] = []
        if self.description is not None:
            help_out.append(f"{self.description}\n\n")

        help_out.append(f"{S.BLD}{S.GRN}Usage: {S.CYN}{self.prog}{S.RST}{S.CYN} ")

        headings: set[str] = set()
        for action_group in self._action_groups:
            if grp_actions := action_group._group_actions:  # noqa: SLF001
                heading = f"\n{S.BLD}{S.GRN}{action_group.title}:{S.RST}\n"
                headings.add(action_group.title)

                formatter = self._get_formatter()
                formatter.add_arguments(grp_actions)

                formatted_entries = [
                    f"  {self._format_entry(entry.lstrip())}\n"
                    for entry in formatter.format_help().split("\n")
                    if entry and not entry.startswith("{")
                ]

                help_out.append(heading)
                help_out.extend(formatted_entries)

        if self.epilog is None:
            help_out.append("\n")
        else:
            help_out.append(f"\n{self.epilog}\n")

        usage_strs = []
        if "Options" in headings:
            usage_strs.append("[OPTIONS]")

        if "Commands" in headings:
            usage_strs.append("<COMMAND>")

        if "Arguments" in headings:
            usage_strs.append("[ARGUMENTS]")

        help_out.insert(2, f"{' '.join(usage_strs)}{S.RST}\n")

        return "".join(help_out)

    @override
    def _match_argument(self, action: Action, arg_strings_pattern: str) -> int:
        nargs_pattern = self._get_nargs_pattern(action)
        match = re.match(nargs_pattern, arg_strings_pattern)

        if match is None:
            nargs_errors = {
                None: "expected one argument",
                OPTIONAL: "expected at most one argument",
                ONE_OR_MORE: "expected at least one argument",
            }
            msg = nargs_errors.get(action.nargs)
            if msg is None:
                msg = ngettext("expected %s argument", "expected %s arguments", action.nargs) % action.nargs
            msg += " for "
            if len(action.option_strings) == 1:
                msg += f"{S.BLD}{S.CYN}{action.option_strings[0]}{S.RST}"
            else:
                msg += (
                    f"{S.BLD}{S.CYN}{action.option_strings[0]}{S.RST}/{S.BLD}{S.CYN}{action.option_strings[1]}{S.RST}"
                )

            self.error(msg, ExitCode.INVALID_ARGS)

        return len(match.group(1))

    @override
    def _get_value(self, action: Action, arg_string: str) -> Any:
        type_func = self._registry_get("type", action.type, action.type)
        if not callable(type_func):
            msg = f"{type_func} is not callable"
            raise ArgumentError(action, msg)

        try:
            result = type_func(arg_string)

        except ArgumentTypeError as e:
            msg = str(e)
            raise ArgumentError(action, msg) from e

        except (TypeError, ValueError):
            name = getattr(action.type, "__name__", repr(action.type))
            msg = f"invalid {name} value for "
            if len(action.option_strings) == 1:
                msg += f"{S.BLD}{S.CYN}{action.option_strings[0]}{S.RST}"
            else:
                msg += (
                    f"{S.BLD}{S.CYN}{action.option_strings[0]}{S.RST}/{S.BLD}{S.CYN}{action.option_strings[1]}{S.RST}"
                )

            msg += f": {S.YLW}'{arg_string}'{S.RST}"
            self.error(msg, ExitCode.INVALID_ARGS)

        return result

    @override
    def parse_args(self, args: Sequence[str] | None = None, namespace: Namespace | None = None) -> tuple[Namespace]:
        args, argv = self.parse_known_args(args, namespace)

        if argv:
            args = 0
            opts = 0
            colored_args = []
            for arg in argv:
                if arg.startswith(("-", "--")):
                    opts += 1
                else:
                    args += 1
                colored_args.append(f"{S.YLW}{arg}{S.RST}")

            argv_str = ", ".join(colored_args)
            msg_strs: set[str] = set()

            if opts:
                msg_strs.add("option(s)" if opts > 1 else "option")
            if args:
                msg_strs.add("arg(s)" if args > 1 else "arg")

            msg = f"unexpected {'/'.join(msg_strs)}: {argv_str}"
            self.error(msg, ExitCode.INVALID_ARGS)

        return args

    @override
    def _check_value(self, action: Action, value: Any) -> None:
        if action.choices is not None and value not in action.choices:
            choices = ", ".join(f"{S.BLD}{S.CYN}{choice}{S.RST}" for choice in action.choices)
            msg = f"invalid command: {S.BLD}{S.RED}{value}{S.RST} (choose from: {choices})"
            self.error(msg, ExitCode.INVALID_CMD)

    @override
    def _get_value(self, action: Action, arg_string: str) -> Any:
        type_func = self._registry_get("type", action.type, action.type)
        if not callable(type_func):
            msg = f"{type_func} is not callable"
            raise _ArgError(action, msg)

        # convert the value to the appropriate type
        try:
            result = type_func(arg_string)

        # ArgumentTypeErrors indicate errors
        except ArgumentTypeError as err:
            name = getattr(action.type, "__name__", repr(action.type))
            msg = str(err)
            raise _ArgError(action, msg) from err

        # TypeErrors or ValueErrors also indicate errors
        except (TypeError, ValueError) as e:
            name = getattr(action.type, "__name__", repr(action.type))
            msg = f"invalid {name} value: {arg_string}"
            raise _ArgError(action, msg) from e

        # return the converted value
        return result

    @override
    def error(self, message: str, exit_code: ExitCode = ExitCode.FAILURE) -> NoReturn:
        perr(message, end="\n\n")
        self.print_usage(stderr)
        sexit(exit_code.value)
