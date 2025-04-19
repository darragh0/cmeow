# /// script
# requires-python = ">=3.12"
# ///

from __future__ import annotations

from os import chdir
from typing import TYPE_CHECKING

from colorama import just_fix_windows_console

from cmeow.util import (
    BuildType,
    MarkerFileKeys,
    build_proj,
    check_dir_exists,
    check_proj_exists,
    cmake_files_exist,
    find_proj_dir,
    init_cmake,
    init_parser,
    mk_proj_files,
    need_build,
    parse_marker_file_keys,
    run_cmd,
    update_marker_file,
    write,
    writeln,
)

if TYPE_CHECKING:
    from argparse import Namespace
    from pathlib import Path


def main() -> None:
    """Script main entry point."""

    just_fix_windows_console()

    parser = init_parser()
    args = parser.parse_args()

    cmds = {"new": new, "build": build, "run": run}
    if args.command in cmds:
        cmds[args.command](args)
    else:
        parser.print_help()


def new(args: Namespace) -> None:
    args.proj_dir = args.path / args.project
    args.target_dir = args.proj_dir / args.target
    args.src_dir = args.proj_dir / args.src

    check_proj_exists(args)
    mk_proj_files(args)

    init_cmake(args.proj_dir, args, verbose=args.verbose)


def build(args: Namespace, proj_dir: Path | None = None, keys: MarkerFileKeys | None = None) -> None:
    called_by_run = proj_dir is not None and keys is not None
    if not called_by_run:
        proj_dir = find_proj_dir()
        keys = parse_marker_file_keys(proj_dir)

    should_build: bool
    if not cmake_files_exist(keys.target_dir, keys.build_type):
        init_cmake(proj_dir, keys, verbose=args.verbose)
        should_build = True
    else:
        should_build = need_build(proj_dir, keys.last_build)

    check_dir_exists(keys.src_dir)

    secs = build_proj(proj_dir, keys.target_dir, keys.build_type, verbose=args.verbose) if should_build else 0.0
    build_info = "build [unoptimized + debuginfo]" if keys.build_type == BuildType.DEBUG else "build [optimized]"

    write(f"     <grn>*Finished*</grn> `{keys.build_type.value}` ")
    write(f"{build_info} target(s) in {secs:.2f}s")

    if not should_build:
        writeln(" <ylw>[files unchanged]</ylw>")
        return

    writeln()
    update_marker_file(proj_dir, keys)


def run(args: Namespace) -> None:
    proj_dir = find_proj_dir()
    keys = parse_marker_file_keys(proj_dir)

    build(args, proj_dir, keys)

    # TODO: find other executable(s) # noqa: FIX002, TD002, TD003
    executable = keys.target_dir / keys.build_type / keys.project
    check_dir_exists(executable, "could not find executable")

    rel_executable = executable.relative_to(proj_dir)
    writeln(f"      *<grn>Running</grn>* `{rel_executable!s}`")

    cmd = f"./{rel_executable}"
    chdir(proj_dir)
    run_cmd(cmd, verbose=False, spinner=False)
