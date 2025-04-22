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
from cmeow.util._defaults import ArgDefault
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
        prog="cmeow",
        description="Small CLI tool to simplify working with CMake projects.",
        version=__version__,
        epilog=True,
        short_version=True,
        short_help=True,
    )

    commands = parser.add_subparsers(dest="command", title="Commands")

    #######################################################
    ###                    cmeow new                   ####
    #######################################################

    desc_new = "Create a new cmeow project."
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

    #######################################################
    ###                   cmeow init                   ####
    #######################################################

    desc_init = "Create a new cmeow project in current directory (and named as such)."
    cmd_init = commands.add_parser("init", description=desc_init, help=desc_init)

    cmd_init.add_argument("project", help="Name of the project.", type=proj_name, metavar="project-name")
    cmd_init.add_argument(
        "-v",
        "--verbose",
        help="Enable verbose logging for project initialization.",
        action="store_true",
    )

    for long_opt, _type, default, _help, mvar in (
        ("--cmake", cmake_version, ArgDefault.cmake, "Min. required CMake version [default: %(default)s]", "<CMAKE>"),
        ("--std", c_std_version, ArgDefault.std, "CMAKE_CXX_STANDARD [default: %(default)s]", "<STD>"),
        ("--version", proj_version, ArgDefault.version, "Project version [default: %(default)s]", "<VERSION>"),
    ):
        cmd_init.add_argument(long_opt, type=_type, default=default, help=_help, metavar=mvar)

    #######################################################
    ###             cmeow build / cmeow run            ####
    #######################################################

    for cmd_name, cmd_desc, desc2 in (
        ("build", "Build the project", "Build"),
        ("run", "Run the project executable", "Build & run"),
    ):
        cmd = commands.add_parser(cmd_name, description=cmd_desc, help=cmd_desc)
        cmd.add_argument("-v", "--verbose", help="Enable verbose logging for the build process.", action="store_true")
        _setup_mutex_group(cmd, desc2)

    return parser
