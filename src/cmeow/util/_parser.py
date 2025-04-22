from argparse import ArgumentParser

from cmeow.__init__ import __version__
from cmeow.util._arg_parser import (
    ArgParser,
    c_std_version,
    cmake_version,
    directory,
    proj_name,
    proj_version,
)
from cmeow.util._defaults import ArgDefault, Constant
from cmeow.util._enum import BuildType


def _setup_mutex_group(parser: ArgumentParser, help_prefix: str) -> None:
    grp = parser.add_argument_group("Mutex Options")
    mutex = grp.add_mutually_exclusive_group()
    mutex.add_argument(
        "-r",
        "--release",
        action="store_const",
        help=f"{help_prefix} in release mode.",
        dest="build_type",
        const=BuildType.RELEASE,
    )
    mutex.add_argument(
        "-d",
        "--debug",
        action="store_const",
        help=f"{help_prefix} in debug mode.",
        dest="build_type",
        const=BuildType.DEBUG,
    )
    parser.set_defaults(build_type=BuildType.DEBUG)


def init_parser() -> ArgParser:
    parser = ArgParser(
        prog=Constant.program,
        description="Small CLI tool to simplify working with CMake projects.",
        version=__version__,
        epilog=True,
        short_version=True,
        short_help=True,
    )

    commands = parser.add_subparsers(dest="command", title="Commands")

    desc_new = f"Create a new {Constant.program} project."
    cmd_new = commands.add_parser("new", description=desc_new, help=desc_new)

    cmd_new.add_argument("project", help="Name of the project.", type=proj_name, metavar="project-name")
    cmd_new.add_argument(
        "-v",
        "--verbose",
        help="Enable verbose logging for project initialization.",
        action="store_true",
    )

    for long_opt, _type, default, _help, mvar in (
        ("--path", directory, ArgDefault.directory, "Project location. [default: $PWD]", "<PATH>"),
        ("--cmake", cmake_version, ArgDefault.cmake, "Min. required CMake version [default: %(default)s]", "<CMAKE>"),
        ("--std", c_std_version, ArgDefault.std, "CMAKE_CXX_STANDARD [default: %(default)s]", "<STD>"),
        ("--version", proj_version, ArgDefault.version, "Project version [default: %(default)s]", "<VERSION>"),
    ):
        cmd_new.add_argument(long_opt, type=_type, default=default, help=_help, metavar=mvar)

    for name, desc1, desc2 in (
        ("build", "Build the project", "Build"),
        ("run", "Run the project executable", "Build & run"),
    ):
        cmd = commands.add_parser(name, description=desc1, help=desc1)
        cmd.add_argument("-v", "--verbose", help="Enable verbose logging for the build process.", action="store_true")
        _setup_mutex_group(cmd, desc2)

    return parser
