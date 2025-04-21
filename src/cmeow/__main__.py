# /// script
# requires-python = ">=3.12"
# ///

from __future__ import annotations

from os import chdir
from typing import TYPE_CHECKING

from colorama import just_fix_windows_console

from cmeow.util import (
    BuildType,
    ProjectFileKeys,
    build_proj,
    check_dir_exists,
    check_proj_exists,
    cmake_files_exist,
    find_proj_dir,
    init_cmake,
    init_parser,
    mk_proj_files,
    need_build,
    parse_project_file,
    run_cmd,
    update_project_file,
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
    proj_dir = args.path / args.project

    check_proj_exists(proj_dir, args.build_type)
    mk_proj_files(proj_dir, args)

    init_cmake(proj_dir, args, verbose=args.verbose)


def build(args: Namespace, proj_dir: Path | None = None, keys: ProjectFileKeys | None = None) -> None:
    called_by_run = proj_dir is not None and keys is not None
    if not called_by_run:
        proj_dir = find_proj_dir()
        keys = parse_project_file(proj_dir)

    should_build: bool
    if not cmake_files_exist(proj_dir, keys.build_type):
        init_cmake(proj_dir, keys, verbose=args.verbose)
        should_build = True
    else:
        should_build = need_build(proj_dir, keys.last_build)

    check_dir_exists(proj_dir / "src")

    secs = build_proj(proj_dir, keys.build_type, verbose=args.verbose) if should_build else 0.0
    build_info = "build [unoptimized + debuginfo]" if keys.build_type == BuildType.DEBUG else "build [optimized]"

    write(f"<grn>*Finished*</grn> `{keys.build_type.value}` ", indent=5)
    write(f"{build_info} target(s) in {secs:.2f}s")

    if not should_build:
        writeln("<ylw>[files unchanged]</ylw>", indent=1)
        return

    writeln()
    update_project_file(proj_dir, keys)


def run(args: Namespace) -> None:
    proj_dir = find_proj_dir()
    keys = parse_project_file(proj_dir)

    build(args, proj_dir, keys)

    # TODO: find other executable(s) # noqa: FIX002, TD002, TD003
    executable = proj_dir / "target" / keys.build_type / keys.project
    check_dir_exists(executable, "could not find executable")

    cmd = str(executable.relative_to(proj_dir))
    writeln(f"*<grn>Running</grn>* `./{cmd}`", indent=6)

    chdir(proj_dir)
    run_cmd(cmd, bg=False, verbose=False, spinner=False)
