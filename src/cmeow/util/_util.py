from __future__ import annotations

import subprocess as sp
from datetime import UTC
from datetime import datetime as dt
from itertools import cycle
from os import chdir
from pathlib import Path
from sys import exit as sexit
from threading import Event, Thread
from time import perf_counter, sleep
from typing import TYPE_CHECKING

from colorama import Style

from cmeow.__init__ import __version__
from cmeow.util._console_io import perr, pwarn, write, writeln, yn_input
from cmeow.util._defaults import BuildType, Constant, MarkerFileKeys
from cmeow.util._errors import ExitCode

if TYPE_CHECKING:
    from argparse import Namespace


def _spinner(stop_event: Event) -> None:
    spinner_frames = ("⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏")
    sleep_time = 0.08

    write(f"\033[?25l{Style.DIM}")
    for frame in cycle(spinner_frames):
        if stop_event.is_set():
            break

        write(frame, end="\b")
        sleep(sleep_time)

    write(f" {Style.RESET_ALL}\033[?25h")


def run_cmd(cmd: str, *, verbose: bool, spinner: bool, verbose_indent: int = 0) -> float:
    _stdout: None | int
    _stderr: None | int
    if not verbose:
        _stdout = sp.DEVNULL
        _stderr = sp.DEVNULL
    else:
        _stdout = None
        _stderr = None

    stop_event: Event
    spinner_thread: Thread
    if spinner:
        stop_event = Event()
        spinner_thread = Thread(target=_spinner, args=(stop_event,))
        spinner_thread.start()

    start = perf_counter()

    try:
        if verbose:
            writeln()
            with sp.Popen(cmd, stdout=sp.PIPE, stderr=sp.STDOUT, text=True, shell=True) as proc:  # noqa: S602
                for line in proc.stdout:
                    write(f"{' ' * verbose_indent}${line}$")
            write(Style.RESET_ALL)
        else:
            sp.run(cmd, check=True, stdout=_stdout, stderr=_stderr, shell=True)  # noqa: S602
    finally:
        if spinner:
            stop_event.set()
            spinner_thread.join()

    return perf_counter() - start


def build_proj(proj_dir: Path, target_dir: Path, build_type: BuildType, *, verbose: bool = False) -> float:
    chdir(proj_dir)
    write(f"    *<grn>Compiling</grn>* {proj_dir.name} ({proj_dir!s}) ")

    cmd = Constant.cmake_build_cmd.format(build_dir=f"{target_dir.name}/{build_type.value}/{Constant.cmake_build_dir}")
    return run_cmd(cmd, verbose=verbose, spinner=not verbose, verbose_indent=4)


def check_dir_exists(path: Path, msg: str | None = None) -> None:
    msg: str = "could not find directory" if msg is None else msg
    if not path.exists():
        msg: str = f"{msg} `{path.name}` as specified in {Constant.marker_file}"
        perr(msg, ExitCode.DIR_NOT_EXISTS)


def _write_cmake_lists_txt(proj_dir: Path, args: Namespace) -> None:
    cmake_str = Constant.cmake_lists_txt_str.format(
        cmake_ver=args.cmake,
        proj_name=args.project,
        cmake_cxx_std=args.std,
        src_dir=args.src,
        target_dir=args.target,
    )

    with (proj_dir / "CMakeLists.txt").open("w", encoding="utf-8") as file:
        file.write(cmake_str)


def _write_src_main_cpp(src_dir: Path) -> None:
    with (src_dir / "main.cpp").open("w", encoding="utf-8") as file:
        file.write(Constant.src_main_cpp_str)


def _write_marker_file(proj_dir: Path, args: Namespace) -> None:
    with (proj_dir / Constant.marker_file).open("w", encoding="utf-8") as f:
        f.write("last_build = -1\n")
        f.write(f"build_type = {args.build_type}\n")
        f.write(f"project = {args.project}\n")
        f.write(f"version = {__version__}\n")
        f.write(f"cmake = {args.cmake}\n")
        f.write(f"std = {args.std}\n")
        f.write(f"src_dir = {args.src}\n")
        f.write(f"target_dir = {args.target}\n")


def mk_proj_files(args: Namespace) -> None:
    try:
        args.proj_dir.mkdir(parents=True, exist_ok=True)
    except OSError as ose:
        msg = f"could not create {args.proj_dir!s}: {ose!s}"
        perr(msg, ExitCode.CANNOT_CREATE_PROJ)

    try:
        args.src_dir.mkdir(parents=True, exist_ok=True)
        args.target_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        msg = f"could not create {args.src}/{args.target}: {e!s}"
        perr(msg, ExitCode.CANNOT_CREATE_PROJ)

    _write_cmake_lists_txt(args.proj_dir, args)
    _write_src_main_cpp(args.src_dir)
    _write_marker_file(args.proj_dir, args)


def check_proj_exists(args: Namespace) -> None:
    if not args.proj_dir.exists():
        return

    is_project = (args.proj_dir / Constant.marker_file).exists()
    msg_pre: str
    prompt: str
    exit_code: ExitCode
    warn: bool

    if is_project:
        msg_pre = f"Project `{args.proj_dir.name}`"
        prompt = "Override this"
        exit_code = ExitCode.PROJ_EXISTS

        if cmake_files_exist(args.target_dir, args.build_type):
            msg_pre += f" with <mag>{args.build_type}</mag> build profile"
            warn = True
        else:
            warn = False
    else:
        msg_pre = f"Folder `{args.proj_dir.name}`"
        prompt = "Initialize new project here"
        exit_code = ExitCode.DIR_EXISTS
        warn = True

    if warn:
        msg = f"{msg_pre} already exists."
        pwarn(msg)

        if not yn_input(f"  {prompt}? (y/n): "):
            sexit(exit_code.value)


def find_proj_dir() -> Path:
    origin = Path.cwd()
    cwd = origin

    while cwd != cwd.parent:
        if (cwd / Constant.marker_file).exists():
            return cwd
        cwd = cwd.parent

    perr(f"could not find `{Constant.marker_file}` in `{origin}` or any parent directory", ExitCode.PROJ_NOT_EXISTS)
    return None


def cmake_files_exist(target_dir: Path, build_type: BuildType) -> bool:
    required = [
        target_dir / build_type.value / Constant.cmake_build_dir / p_str
        for p_str in ("CMakeFiles", "CMakeCache.txt", "cmake_install.cmake", "Makefile")
    ]

    return all(p.is_dir() if p.name == "CMakeFiles" else p.is_file() for p in required)


def init_cmake(proj_dir: Path, args: Namespace | MarkerFileKeys, *, verbose: bool = False) -> None:
    write(f"   *<grn>Creating</grn>* {Constant.program} project: `{proj_dir.name}` ")
    writeln(f"[build-type: <mag>{args.build_type}</mag>")
    write(f"    ⤷ <grn>with:</grn> <cyn>CMake v{args.cmake}</cyn> ")
    write(f"& <cyn>C++ Standard {args.std}</cyn> ")

    # TODO: security  # noqa: FIX002, TD002, TD003
    cmd = Constant.cmake_init_cmd.format(
        build_type=args.build_type.capitalize(),
        build_dir=f"{args.target_dir.name}/{args.build_type}/{Constant.cmake_build_dir}",
    )

    chdir(proj_dir)
    run_cmd(cmd, verbose=verbose, spinner=not verbose, verbose_indent=5)


def need_build(proj_dir: Path, last_build: dt) -> bool:
    for file in proj_dir.rglob("*"):
        if file.is_file():
            # Get the last modified timestamp
            timestamp = file.stat().st_mtime
            mod_time = dt.fromtimestamp(timestamp, tz=UTC)

            if mod_time > last_build:
                return True

    return False


def parse_marker_file_keys(proj_dir: Path) -> MarkerFileKeys:  # noqa: C901, PLR0912
    marker_file: Path = proj_dir / Constant.marker_file
    keys = MarkerFileKeys()

    invalid_keys: set[str] = set()
    # TODO: Validate vals  # noqa: FIX002, TD002, TD003
    with marker_file.open(encoding="utf-8") as file:
        content: list[str] = file.readlines()
        for line in content:
            key, val = line.split(" = ")

            if key in keys.__dict__ and getattr(keys, key, None) is None:
                val: str = val.rstrip()
                if key == "src_dir":
                    keys.src_dir = Path(proj_dir / val)
                elif key == "target_dir":
                    keys.target_dir = Path(proj_dir / val)
                elif key == "last_build":
                    if val == "-1":
                        keys.last_build = dt.min.replace(tzinfo=UTC)
                    else:
                        keys.last_build = dt.fromisoformat(val)
                elif key == "build_type" and val in BuildType:
                    keys.build_type = BuildType(val)
                elif key == "std":
                    keys.std = int(val)
                else:
                    setattr(keys, key, val)
            elif key not in keys.__dict__:
                invalid_keys.add(key)

    if invalid_keys:
        msg_suf: str = ", ".join(f"<ylw>{key}</ylw>" for key in invalid_keys)
        msg: str = f"invalid keys in {Constant.marker_file}: {msg_suf}"
        perr(msg, ExitCode.INVALID_KEYS)

    missing_keys: set[str] = {key for key, value in keys.__dict__.items() if value is None}
    if missing_keys:
        msg_suf: str = ", ".join(f"<ylw>{key}</ylw>" for key in missing_keys)
        msg: str = f"missing keys in {Constant.marker_file}: {msg_suf}"
        perr(msg, ExitCode.MISSING_KEYS)

    return keys


def update_marker_file(proj_dir: Path, keys: MarkerFileKeys) -> None:
    with (proj_dir / Constant.marker_file).open("w", encoding="utf-8") as file:
        for key, value in keys.__dict__.items():
            if key in {"src_dir", "target_dir"}:
                file.write(f"{key} = {value.name}\n")
            elif key == "last_build":
                file.write(f"{key} = {dt.now(tz=UTC).isoformat()}\n")
            elif key == "build_type":
                file.write(f"{key} = {value.value}\n")
            else:
                file.write(f"{key} = {value}\n")
