from argparse import Namespace
from os import chdir
from pathlib import Path

from cmeow.util import (
    BuildType,
    Constant,
    Keys,
    build_proj,
    check_dir_exists,
    check_proj_exists,
    cmake_files_exist,
    find_proj_dir,
    init_cmake,
    mk_proj_files,
    need_build,
    parse_project_file,
    run_cmd,
    update_project_file,
    write,
    writeln,
)


def _new(args: Namespace) -> None:
    proj_dir = args.path / args.project

    check_proj_exists(proj_dir)
    keys = mk_proj_files(proj_dir, args)

    init_cmake(proj_dir, keys, verbose=args.verbose)


def _build(args: Namespace, proj_dir: Path | None = None, keys: Keys | None = None) -> None:
    called_via_run = proj_dir is not None and keys is not None
    if not called_via_run:
        proj_dir = find_proj_dir()
        keys = parse_project_file(proj_dir)

    should_build: bool
    if not cmake_files_exist(proj_dir, args.build_type):
        init_cmake(proj_dir, keys, args.build_type, verbose=args.verbose, first_time=False)
        should_build = True
    else:
        exe = proj_dir / Constant.target_dir / args.build_type / keys.project.name
        should_build = True if not exe.exists() else need_build(proj_dir, keys.project.last_build)

    check_dir_exists(proj_dir / Constant.src_dir)

    secs = build_proj(proj_dir, args.build_type, verbose=args.verbose) if should_build else 0.0
    build_info = "build [unoptimized + debuginfo]" if args.build_type == BuildType.DEBUG else "build [optimized]"

    write(f"<grn>*Finished*</grn> <mag>{args.build_type}</mag> ", indent=5)
    write(f"{build_info} target(s) in {secs:.2f}s")

    if not should_build:
        writeln("<ylw>[files unchanged]</ylw>", indent=1)
        return

    writeln()
    update_project_file(proj_dir, keys)


def _run(args: Namespace) -> None:
    proj_dir = find_proj_dir()
    keys = parse_project_file(proj_dir)

    _build(args, proj_dir, keys)

    exe = proj_dir / Constant.target_dir / args.build_type / keys.project.name
    check_dir_exists(exe, "could not find executable")

    cmd = str(exe.relative_to(proj_dir))
    writeln(f"*<grn>Running</grn>* `./{cmd}`", indent=6)

    chdir(proj_dir)
    run_cmd(cmd, bg=False, verbose=False, spinner=False)


cmd_map = {
    "new": _new,
    "build": _build,
    "run": _run,
}
