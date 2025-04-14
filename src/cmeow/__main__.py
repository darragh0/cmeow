# /// script
# requires-python = ">=3.12"
# ///

from __future__ import annotations

import subprocess as sp
from os import chdir
from typing import TYPE_CHECKING

from cmeow.__init__ import __version__
from cmeow.util import (
    ArgParser,
    BuildType,
    Constant,
    Default,
    ExitCode,
    MarkerFileKeys,
    Style,
    build_proj,
    c_std_version,
    check_dir_exists,
    check_proj_exists,
    cmake_files_exist,
    cmake_version,
    dir_name,
    directory,
    find_proj_dir,
    init_cmake,
    need_build,
    parse_marker_file_keys,
    perr,
    update_marker_file,
)

if TYPE_CHECKING:
    from pathlib import Path


def main() -> None:
    """Script main entry point."""

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

    parser_new.add_argument("project_name", help="Name of the project.", type=dir_name, metavar="project-name")
    parser_new.add_argument(
        "-v",
        "--verbose",
        help="Enable verbose logging for project initialization.",
        action="store_true",
    )
    parser_new.add_argument(
        "-r",
        "--release",
        help="Create project with a default build type of release (default is debug).",
        action="store_true",
    )

    for long_opt, _type, default, _help, mvar in (
        ("--path", directory, Default.directory, "Project location. [default: $PWD]", "<PATH>"),
        ("--cmake", cmake_version, Default.cmake, "Minimum required CMake version [default: %(default)s]", "<CMAKE>"),
        ("--std", c_std_version, Default.std, "CMAKE_CXX_STANDARD [default: %(default)s]", "<STD>"),
        ("--src", dir_name, Default.src, "Source directory [default: %(default)s]", "<SRC>"),
        ("--target", dir_name, Default.target, "Target/build directory [default: %(default)s]", "<TARGET>"),
    ):
        parser_new.add_argument(long_opt, type=_type, default=default, help=_help, metavar=mvar)

    desc_build = "Build the project."
    parser_build = commands.add_parser("build", description=desc_build, help=desc_build)
    parser_build.add_argument("-v", "--verbose", help="Enable verbose logging for build process.", action="store_true")

    desc_run = "Run the project executable."
    parser_run = commands.add_parser("run", description=desc_run, help=desc_run)
    parser_run.add_argument("-v", "--verbose", help="Enable verbose logging (for build process).", action="store_true")

    args = parser.parse_args()

    if args.command == "new":
        new(
            args.project_name,
            args.path,
            args.cmake,
            args.std,
            args.src,
            args.target,
            verbose=args.verbose,
            release=args.release,
        )
    elif args.command == "build":
        build(verbose=args.verbose)
    elif args.command == "run":
        run(verbose=args.verbose)
    elif args.command is None:
        parser.print_help()


def new(  # noqa: PLR0913
    project_name: str,
    path: Path,
    cmake: str,
    std: int,
    src: str,
    target: str,
    *,
    verbose: bool,
    release: bool,
) -> None:
    build_type = BuildType.RELEASE if release else BuildType.DEBUG
    proj_dir = path / project_name
    check_proj_exists(proj_dir)

    try:
        proj_dir.mkdir(parents=True)
    except FileExistsError:
        pass
    except OSError as ose:
        msg = f"could not create {proj_dir!s}: {ose!s}"
        perr(msg, ExitCode.CANNOT_CREATE_PROJ)

    src_dir = proj_dir / src
    target_dir = proj_dir / target
    try:
        src_dir.mkdir(parents=True)
        target_dir.mkdir(parents=True)
    except FileExistsError:
        pass
    except OSError as e:
        msg = f"could not create {src}/{target}: {e!s}"
        perr(msg, ExitCode.CANNOT_CREATE_PROJ)

    cmake_str = Constant.cmake_base_str.format(
        cmake_ver=cmake,
        proj_name=project_name,
        cmake_cxx_std=std,
        src_dir=src,
        target_dir=target,
    )

    for file, content in (
        (proj_dir / "CMakeLists.txt", cmake_str),
        (src_dir / "main.cpp", Constant.src_main_cpp_base_str),
    ):
        with file.open("w", encoding="utf-8") as f:
            f.write(content)

    with (proj_dir / Constant.marker_file).open("w", encoding="utf-8") as f:
        f.write("last_build = -1\n")
        f.write(f"build_type = {build_type.value}\n")
        f.write(f"project = {project_name}\n")
        f.write(f"version = {__version__}\n")
        f.write(f"cmake_version = {cmake}\n")
        f.write(f"cxx_std = {std}\n")
        f.write(f"source = {src}\n")
        f.write(f"target = {target}\n")

    init_cmake(proj_dir, target_dir, build_type, cmake, std, verbose=verbose)


def build(proj_dir: Path | None = None, keys: MarkerFileKeys | None = None, *, verbose: bool) -> None:
    called_by_run = proj_dir is not None and keys is not None
    should_build: bool

    if called_by_run:
        should_build = True
    else:
        proj_dir = find_proj_dir()
        keys = parse_marker_file_keys(proj_dir)

        should_build: bool

        if not cmake_files_exist(keys.target, keys.build_type):
            init_cmake(proj_dir, keys.target, keys.build_type, keys.cmake_version, keys.cxx_std, verbose=verbose)
            should_build = True
        else:
            should_build = need_build(proj_dir, keys.last_build)

        check_dir_exists(keys.source)

    secs = build_proj(proj_dir, keys.target, keys.build_type, verbose=verbose) if should_build else 0.0
    build_info = "build [unoptimized + debuginfo]" if keys.build_type == BuildType.DEBUG else "build [optimized]"

    print(f"     {Style.BLD}{Style.GRN}Finished{Style.RST} `{keys.build_type.value}` ", end="")
    print(f"{build_info} target(s) in {secs:.2f}s")

    if not should_build:
        return

    update_marker_file(proj_dir, keys)


def run(*, verbose: bool) -> None:
    proj_dir = find_proj_dir()
    keys = parse_marker_file_keys(proj_dir)

    should_build: bool

    if not cmake_files_exist(keys.target, keys.build_type):
        init_cmake(proj_dir, keys.target, keys.build_type, keys.cmake_version, keys.cxx_std, verbose=verbose)
        should_build = True
    else:
        should_build = need_build(proj_dir, keys.last_build)

    check_dir_exists(keys.source)

    if should_build:
        build(proj_dir, keys, verbose=verbose)

    # TODO: find other executable(s) # noqa: FIX002, TD002, TD003
    executable = keys.target / keys.build_type.value / keys.project
    check_dir_exists(executable, "could not find executable")

    rel_executable = executable.relative_to(proj_dir)
    print(f"      {Style.BLD}{Style.GRN}Running{Style.RST} `{rel_executable!s}`")

    chdir(proj_dir)
    exec_cmd = f"./{rel_executable}"
    sp.run(exec_cmd, check=True, shell=True)  # noqa: S602
