from cmeow.__init__ import __version__
from cmeow.util._arg_parser import ArgParser, build_type, c_std_version, cmake_version, dir_name, directory, proj_name
from cmeow.util._defaults import ArgDefault, Constant


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
    parser_new = commands.add_parser("new", description=desc_new, help=desc_new)

    parser_new.add_argument("project", help="Name of the project.", type=proj_name, metavar="project-name")
    parser_new.add_argument(
        "-v",
        "--verbose",
        help="Enable verbose logging for project initialization.",
        action="store_true",
    )
    parser_new.add_argument(
        "-b",
        "--build",
        dest="build_type",
        type=build_type,
        default=ArgDefault.build_type,
        help="Project build type [default: %(default)s]",
        metavar="<TYPE>",
    )

    for long_opt, _type, default, _help, mvar in (
        ("--path", directory, ArgDefault.directory, "Project location. [default: $PWD]", "<PATH>"),
        ("--cmake", cmake_version, ArgDefault.cmake, "Min. required CMake version [default: %(default)s]", "<CMAKE>"),
        ("--std", c_std_version, ArgDefault.std, "CMAKE_CXX_STANDARD [default: %(default)s]", "<STD>"),
        ("--src", dir_name, ArgDefault.src, "Source directory [default: %(default)s]", "<SRC>"),
        ("--target", dir_name, ArgDefault.target, "Target/build directory [default: %(default)s]", "<TARGET>"),
    ):
        parser_new.add_argument(long_opt, type=_type, default=default, help=_help, metavar=mvar)

    desc_build = "Build the project."
    parser_build = commands.add_parser("build", description=desc_build, help=desc_build)
    parser_build.add_argument("-v", "--verbose", help="Enable verbose logging for build process.", action="store_true")

    desc_run = "Run the project executable."
    parser_run = commands.add_parser("run", description=desc_run, help=desc_run)
    parser_run.add_argument("-v", "--verbose", help="Enable verbose logging (for build process).", action="store_true")

    return parser
