from argparse import Namespace
from os import chdir
from pathlib import Path

from colorama import Style

from cmeow.command._resolve_fail import resolve_init_fail, resolve_new_fail
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
    pwarn,
    run_cmd,
    update_project_file,
    write,
    writeln,
)


def _new(args: Namespace, *, called_via_init: bool = False) -> None:
    proj_dir = args.path / args.project

    exists = check_proj_exists(proj_dir, ignore_folder=called_via_init)

    try:
        keys = mk_proj_files(proj_dir, args)
        init_cmake(proj_dir, args.project, keys, verbose=args.verbose, first_time=not exists)
    except KeyboardInterrupt:
        warn_pre = "<ylw>*[warning::interrupt]*</ylw> "
        writeln(f"{Style.RESET_ALL}")
        pwarn(f"new project `{args.project}` may not have been fully initialized.", prefix=warn_pre)
        if called_via_init:
            resolve_init_fail()
        else:
            resolve_new_fail(args)


def _init(args: Namespace) -> None:
    cwd = Path.cwd()
    args.path = cwd.parent
    args.project = cwd.name

    _new(args, called_via_init=True)


def _build(args: Namespace, proj_dir: Path | None = None, keys: Keys | None = None) -> None:
    called_via_run = proj_dir is not None and keys is not None
    if not called_via_run:
        proj_dir = find_proj_dir()
        keys = parse_project_file(proj_dir)

    should_build: bool

    if not cmake_files_exist(proj_dir, args.build_type):
        init_cmake(proj_dir, keys.project.name, keys, args.build_type, verbose=args.verbose, first_time=False)
        should_build = True
    else:
        exe = proj_dir / Constant.target_dir / args.build_type / keys.project.name
        # TODO: Check if CMakeLists.txt project name, std version, cmake version not match keys
        should_build = True if not exe.exists() else need_build(proj_dir, keys.project.last_build)

    check_dir_exists(proj_dir / Constant.src_dir)

    secs = build_proj(proj_dir, keys.project.name, args.build_type, verbose=args.verbose) if should_build else 0.0
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
    "new": {
        "function": _new,
    },
    "init": {
        "function": _init,
    },
    "build": {
        "function": _build,
        "fail_msg": "project may not have been fully built.",
    },
    "run": {
        "function": _run,
        "fail_msg": "could not run project executable.",
    },
}
