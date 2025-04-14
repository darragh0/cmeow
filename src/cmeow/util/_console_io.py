from __future__ import annotations

from enum import StrEnum
from sys import exit as sexit
from sys import stderr
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cmeow.util._errors import ExitCode
    from cmeow.util._typing import PrintKwargs


class Style(StrEnum):
    GRY = "\033[90m"
    RED = "\033[91m"
    GRN = "\033[92m"
    YLW = "\033[93m"
    BLU = "\033[94m"
    MAG = "\033[95m"
    CYN = "\033[96m"
    WHT = "\033[97m"
    BLD = "\033[1m"
    BLD_RST = "\033[22m"
    DIM = "\033[2m"
    DIM_RST = "\033[22m"
    ITL = "\033[3m"
    ITL_RST = "\033[23m"
    UND = "\033[4m"
    UND_RST = "\033[24m"
    BLN = "\033[5m"
    BLN_RST = "\033[25m"
    REV = "\033[7m"
    REV_RST = "\033[27m"
    HID = "\033[8m"
    HID_RST = "\033[28m"
    STK = "\033[9m"
    STK_RST = "\033[28m"
    RST = "\033[0m"


def perr(msg: str, exit_code: ExitCode | None = None, *, prefix: bool = True, **print_kwargs: PrintKwargs) -> None:
    if prefix:
        print(f"{Style.BLD}{Style.RED}error:{Style.RST} ", end="", file=stderr)

    print(msg, file=stderr, **print_kwargs)

    if exit_code is not None:
        sexit(exit_code.value)


def pwarn(msg: str, *, prefix: bool = True, **print_kwargs: PrintKwargs) -> None:
    if prefix:
        print(f"{Style.BLD}{Style.YLW}warning:{Style.RST} ", end="")

    print(msg, **print_kwargs)


def yn_input(prompt: str) -> bool:
    pos = {"yes", "y", "yeah", "yea", "ye"}
    neg = {"no", "n", "nope"}

    while True:
        inp = input(prompt).lower()

        if inp in pos:
            return True

        if inp in neg:
            return False

        perr("invalid input (enter 'y'/'yes' or 'n'/'no')")
