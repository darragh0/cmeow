from __future__ import annotations

import subprocess as sp
from argparse import Namespace
from datetime import UTC
from datetime import datetime as dt
from itertools import cycle
from os import chdir
from pathlib import Path
from sys import exit as sexit
from threading import Event, Thread
from time import perf_counter, sleep
from typing import Literal

import toml
from colorama import Style

from cmeow.__init__ import __version__
from cmeow.util._console_io import perr, pwarn, write, writeln, yn_input
from cmeow.util._defaults import Constant
from cmeow.util._enum import BuildType, ExitCode
from cmeow.util._keys import CmakeKeys, CmeowKeys, DependenciesKeys, Keys, ProjectKeys


def _spinner(stop_event: Event) -> None:
    spinner_frames = ("⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏")
    sleep_time = 0.08

    write(f"\033[?25l{Style.DIM}")
    for frame in cycle(spinner_frames):
        if stop_event.is_set():
            break

        write(frame, end="\b")
        sleep(sleep_time)

    writeln(f" {Style.RESET_ALL}\033[?25h")


def run_cmd(cmd: str, *, bg: bool, verbose: bool, spinner: bool, verbose_indent: int = 0) -> float:
    _stdout: None | int
    _stderr: None | int
    if bg and not verbose:
        _stdout = sp.DEVNULL
        _stderr = sp.DEVNULL
    else:
        _stdout = None
        _stderr = None

    stop_event: Event
    spinner_thread: Thread
    if spinner:
        write(" ")
        stop_event = Event()
        spinner_thread = Thread(target=_spinner, args=(stop_event,))
        spinner_thread.start()

    start = perf_counter()

    try:
        if verbose:
            writeln()
            with sp.Popen(cmd, stdout=sp.PIPE, stderr=sp.STDOUT, text=True, shell=True) as proc:  # noqa: S602
                for line in proc.stdout:
                    write(f"${line}$", indent=verbose_indent)
            write(Style.RESET_ALL)
        else:
            sp.run(cmd, check=True, stdout=_stdout, stderr=_stderr, shell=True)  # noqa: S602
    finally:
        if spinner:
            stop_event.set()
            spinner_thread.join()

    return perf_counter() - start


def build_proj(proj_dir: Path, build_type: BuildType, *, verbose: bool = False) -> float:
    chdir(proj_dir)
    write(f"*<grn>Compiling</grn>* {proj_dir.name} ({proj_dir!s})", indent=4)

    target_dir = proj_dir / Constant.target_dir
    cmd = Constant.cmake_build_cmd.format(build_dir=f"{target_dir.name}/{build_type}/{Constant.cmake_build_dir}")
    return run_cmd(cmd, bg=True, verbose=verbose, spinner=not verbose, verbose_indent=4)


def check_dir_exists(path: Path, msg: str | None = None) -> None:
    msg: str = "could not find directory" if msg is None else msg
    if not path.exists():
        msg: str = f"{msg} `{path.name}`"
        perr(msg, ExitCode.DIR_NOT_EXISTS)


def _write_cmake_lists_txt(proj_dir: Path, proj_name: str, cmake: str, std: int) -> None:
    cmake_str = Constant.cmake_lists_txt_str.format(
        cmake_ver=cmake,
        proj_name=proj_name,
        cmake_cxx_std=std,
    )

    with (proj_dir / "CMakeLists.txt").open("w", encoding="utf-8") as file:
        file.write(cmake_str)


def _write_main_src_file(proj_dir: Path) -> None:
    with (proj_dir / Constant.src_dir / Constant.main_src_file).open("w", encoding="utf-8") as file:
        file.write(Constant.main_src_file_str)


def _write_readme_file(proj_dir: Path, proj_name: str) -> None:
    readme_str = Constant.readme_str.format(proj_name=proj_name)
    with (proj_dir / Constant.readme_file).open("w", encoding="utf-8") as file:
        file.write(readme_str)


def _write_project_file(proj_dir: Path, args: Namespace | Keys) -> Keys:
    project_keys: ProjectKeys
    cmake_keys: CmakeKeys
    cmeow_keys: CmeowKeys

    if isinstance(args, Namespace):
        project_keys = ProjectKeys(
            name=args.project,
            version=args.version,
            description="Add your description here!",
            readme="README.md",
            std=args.std,
        )
        cmake_keys = CmakeKeys(version=args.cmake)
        cmeow_keys = CmeowKeys(version=__version__)
    else:
        project_keys = args.project
        cmake_keys = args.cmake
        cmeow_keys = args.cmeow

    dep_keys = DependenciesKeys()
    keys = Keys(project=project_keys, dependencies=dep_keys, cmeow=cmeow_keys, cmake=cmake_keys)

    proj_file = proj_dir / Constant.project_file

    with proj_file.open("w", encoding="utf-8") as f:
        toml.dump(keys.to_toml(), f)

    return keys


def update_project_file(proj_dir: Path, keys: Keys) -> None:
    keys.project.last_build = dt.now(tz=UTC)
    _write_project_file(proj_dir, keys)


def parse_project_file(proj_dir: Path) -> Keys:
    proj_file = proj_dir / Constant.project_file
    return Keys.from_toml_file(proj_file)


def mk_proj_files(proj_dir: Path, args: Namespace) -> Keys:
    for path in (proj_dir, proj_dir / Constant.src_dir, proj_dir / Constant.target_dir):
        try:
            path.mkdir(parents=True, exist_ok=True)
        except OSError as ose:
            msg = f"could not create {path.name}: {ose!s}"
            perr(msg, ExitCode.CANNOT_CREATE_PROJ)

    _write_cmake_lists_txt(proj_dir, proj_name=args.project, cmake=args.cmake, std=args.std)
    _write_readme_file(proj_dir, proj_name=args.project)
    _write_main_src_file(proj_dir)
    return _write_project_file(proj_dir, args)


def check_proj_exists(proj_dir: Path, build_type: BuildType = BuildType.DEBUG, *, ignore_folder: bool = False) -> bool:
    if not proj_dir.exists():
        return False

    is_project = (proj_dir / Constant.project_file).exists()
    dir_type: Literal["project", "folder"]
    exit_code: ExitCode
    msg_suf: str
    prompt: str

    if is_project:
        dir_type = "project"
        exit_code = ExitCode.PROJ_EXISTS

        if cmake_files_exist(proj_dir, build_type):
            msg_suf = f" (with <mag>{build_type}</mag> profile)"
            prompt = f"<ylw>*[continue?]*</ylw> override `{Constant.project_file}` & build files"
        else:
            msg_suf = ""
            prompt = f"<ylw>*[continue?]*</ylw> override `{Constant.project_file}`"
    elif ignore_folder:
        return False
    else:
        dir_type = "folder"
        exit_code = ExitCode.DIR_EXISTS
        msg_suf = ""
        prompt = "Initialize new project here"

    msg = f"{dir_type} `{proj_dir.name}` exists{msg_suf}."
    pwarn(msg)

    if not yn_input(f"{prompt}? (y/n): ", indent=2):
        sexit(exit_code.value)

    return True


def find_proj_dir() -> Path:
    origin = Path.cwd()
    cwd = origin

    while cwd != cwd.parent:
        if (cwd / Constant.project_file).exists():
            return cwd
        cwd = cwd.parent

    perr(f"could not find `{Constant.project_file}` in `{origin}` or any parent directory", ExitCode.PROJ_NOT_EXISTS)
    return None


def cmake_files_exist(proj_dir: Path, build_type: BuildType) -> bool:
    cmake_build_dir = proj_dir / Constant.target_dir / build_type / Constant.cmake_build_dir

    req_files = (
        *(cmake_build_dir / p for p in Constant.cmake_build_files),
        *(proj_dir / p for p in Constant.cmake_base_files),
    )
    req_dirs = (cmake_build_dir / p for p in Constant.cmake_build_dirs)

    return all(p.is_file() for p in req_files) and all(p.is_dir() for p in req_dirs)


def init_cmake(
    proj_dir: Path,
    keys: Keys,
    build_type: BuildType = BuildType.DEBUG,
    *,
    first_time: bool = True,
    verbose: bool = False,
) -> None:
    msg: str
    if first_time:
        msg = f"<grn>*Creating*</grn> cmeow project: `{proj_dir.name}`"
    else:
        msg = f"<grn>*Initializing*</grn> <mag>{build_type}</mag> build files for `{proj_dir.name}`"

    writeln(msg, indent=3)
    write(
        f"<grn>*⤷* with:</grn> <cyn>CMake v{keys.cmake.version}</cyn> & <cyn>C++ Standard {keys.project.std}</cyn>",
        indent=4,
    )

    target_dir = proj_dir / Constant.target_dir

    # TODO: security  # noqa: FIX002, TD002, TD003
    cmd = Constant.cmake_init_cmd.format(
        build_type=build_type.capitalize(),
        build_dir=f"{target_dir.name}/{build_type}/{Constant.cmake_build_dir}",
    )

    chdir(proj_dir)
    run_cmd(cmd, bg=True, verbose=verbose, spinner=not verbose, verbose_indent=5)


def need_build(proj_dir: Path, last_build: dt) -> bool:
    for file in proj_dir.rglob("*"):
        if file.is_file():
            # Get the last modified timestamp
            timestamp = file.stat().st_mtime
            mod_time = dt.fromtimestamp(timestamp, tz=UTC)

            if mod_time > last_build:
                return True

    return False
