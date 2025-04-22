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

import toml
from colorama import Style

from cmeow.__init__ import __version__
from cmeow.util._console_io import perr, pwarn, write, writeln, yn_input
from cmeow.util._defaults import Constant
from cmeow.util._enum import BuildType, ExitCode
from cmeow.util._keys import CmakeKeys, CmeowKeys, Keys, ProjectKeys


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


def _write_cmake_lists_txt(proj_dir: Path, args: Namespace) -> None:
    cmake_str = Constant.cmake_lists_txt_str.format(
        cmake_ver=args.cmake,
        proj_name=args.project,
        cmake_cxx_std=args.std,
    )

    with (proj_dir / "CMakeLists.txt").open("w", encoding="utf-8") as file:
        file.write(cmake_str)


def _write_src_main_cpp(proj_dir: Path) -> None:
    with (proj_dir / Constant.src_dir / Constant.main_file).open("w", encoding="utf-8") as file:
        file.write(Constant.src_main_cpp_str)


def _write_project_file(proj_dir: Path, args: Namespace | Keys) -> Keys:
    project_keys = ProjectKeys.from_parsed_args(args) if isinstance(args, Namespace) else args.project
    cmake_keys = CmakeKeys.from_parsed_args(args) if isinstance(args, Namespace) else args.cmake
    cmeow_keys = CmeowKeys(version=__version__) if isinstance(args, Namespace) else args.cmeow
    keys = Keys(project=project_keys, cmeow=cmeow_keys, cmake=cmake_keys)

    proj_file = proj_dir / Constant.project_file
    toml_data = keys.to_toml()

    with proj_file.open("w", encoding="utf-8") as f:
        toml.dump(toml_data, f)

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

    _write_cmake_lists_txt(proj_dir, args)
    _write_src_main_cpp(proj_dir)
    return _write_project_file(proj_dir, args)


def check_proj_exists(proj_dir: Path, build_type: BuildType = BuildType.DEBUG) -> None:
    if not proj_dir.exists():
        return

    is_project = (proj_dir / Constant.project_file).exists()
    msg_pre: str
    prompt: str
    exit_code: ExitCode
    warn: bool

    if is_project:
        msg_pre = "Project"

        if cmake_files_exist(proj_dir, build_type):
            msg_pre += f" with <mag>{build_type}</mag> build profile"
            prompt = "Override this"
            exit_code = ExitCode.PROJ_EXISTS
            warn = True
        else:
            warn = False
    else:
        msg_pre = "Folder"
        prompt = "Initialize new project here"
        exit_code = ExitCode.DIR_EXISTS
        warn = True

    if warn:
        msg = f"{msg_pre} `{proj_dir.name}` already exists."
        pwarn(msg)

        if not yn_input(f"  {prompt}? (y/n): "):
            sexit(exit_code.value)


def find_proj_dir() -> Path:
    origin = Path.cwd()
    cwd = origin

    while cwd != cwd.parent:
        if (cwd / Constant.project_file).exists():
            return cwd
        cwd = cwd.parent

    perr(f"could not find `{Constant.project_file}` in `{origin}` or any parent directory", ExitCode.PROJ_NOT_EXISTS)
    return None


def cmake_files_exist(project_dir: Path, build_type: BuildType) -> bool:
    required = [
        project_dir / Constant.target_dir / build_type / Constant.cmake_build_dir / p_str
        for p_str in ("CMakeFiles", "CMakeCache.txt", "cmake_install.cmake", "Makefile")
    ]

    return all(p.is_dir() if p.name == "CMakeFiles" else p.is_file() for p in required)


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
        msg = f"<grn>*Creating*</grn> {Constant.program} project: `{proj_dir.name}`"
    else:
        msg = f"<grn>*Initializing*</grn> <mag>{build_type}</mag> build files for `{proj_dir.name}`"

    writeln(msg, indent=3)
    write(
        f"⤷ <grn>with:</grn> <cyn>CMake v{keys.cmake.version}</cyn> & <cyn>C++ Standard {keys.project.std}</cyn>",
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
