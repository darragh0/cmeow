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

from cmeow.util._console_io import Style, perr, pwarn, yn_input
from cmeow.util._defaults import BuildType, Constant, MarkerFileKeys
from cmeow.util._errors import ExitCode


def _spinner(stop_event: Event) -> None:
    spinner_frames = ("⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏")
    sleep_time = 0.08

    print(f"\033[?25l{Style.GRY}", end="")
    for frame in cycle(spinner_frames):
        if stop_event.is_set():
            break

        print(frame, end="\b", flush=True)
        sleep(sleep_time)

    print(f" {Style.RST}\033[?25h", end="")


def _run_cmd(cmd: str, *, verbose: bool, spinner: bool) -> float:
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
        sp.run(cmd, check=True, stdout=_stdout, stderr=_stderr)  # noqa: S603
    finally:
        if spinner:
            stop_event.set()
            spinner_thread.join()

    return perf_counter() - start


def build_proj(proj_dir: Path, target_dir: Path, build_type: BuildType, *, verbose: bool = False) -> float:
    chdir(proj_dir)
    print(f"    {Style.BLD}{Style.GRN}Compiling{Style.RST} {proj_dir.name} ({proj_dir!s}) ", end="")

    cmd = ["cmake", "--build", f"{target_dir.name}/{build_type.value}/build"]

    if verbose:
        print(f"{Style.GRY}")

    ret = _run_cmd(cmd, verbose=verbose, spinner=not verbose)

    if verbose:
        print(f"{Style.RST}")
    else:
        print()

    return ret


def check_dir_exists(path: Path, msg: str | None = None) -> None:
    msg: str = "could not find directory" if msg is None else msg
    if not path.exists():
        msg: str = f"{msg} `{path.name}` as specified in {Constant.marker_file}"
        perr(msg, ExitCode.DIR_NOT_EXISTS)


def check_proj_exists(proj_dir: Path) -> None:
    if not proj_dir.exists():
        return

    is_project = (proj_dir / Constant.marker_file).exists()
    msg_pre: str
    prompt: str
    exit_code: ExitCode

    if is_project:
        msg_pre = "Project"
        prompt = "Override existing project"
        exit_code = ExitCode.PROJ_EXISTS
    else:
        msg_pre = "Folder"
        prompt = "Initialize new project here"
        exit_code = ExitCode.DIR_EXISTS

    msg = f"{msg_pre} `{proj_dir.name}` already exists."
    pwarn(msg)

    if not yn_input(f"  {prompt}? ({Style.GRN}y{Style.RST}/{Style.RED}n{Style.RST}): "):
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
        target_dir / build_type.value / "build" / p_str
        for p_str in ("CMakeFiles", "CMakeCache.txt", "cmake_install.cmake", "Makefile")
    ]

    return all(p.is_dir() if p.name == "CMakeFiles" else p.is_file() for p in required)


def init_cmake(  # noqa: PLR0913
    proj_dir: Path,
    target_dir: Path,
    build_type: BuildType,
    cmake: str,
    std: int,
    *,
    verbose: bool,
) -> None:
    print(f"   {Style.BLD}{Style.GRN}Creating{Style.RST} {Constant.program} project: `{proj_dir.name}` ", end="")
    print(f"[build-type: {Style.MAG}{build_type.value}{Style.RST}]")
    print(f"    ⤷ {Style.GRN}with: {Style.CYN}CMake v{cmake}{Style.RST} ", end="")
    print(f"& {Style.CYN}C++ Standard {std}{Style.RST} ", end="")

    # TODO: security  # noqa: FIX002, TD002, TD003
    chdir(proj_dir)
    build_type_cap = build_type.value.capitalize()
    cmd = ["cmake", f"-DCMAKE_BUILD_TYPE={build_type_cap}", "-B", f"{target_dir.name}/{build_type.value}/build"]

    if verbose:
        print(f"\n\n{Style.DIM}{Style.BLD}Creating CMake project in {proj_dir!s}:{Style.RST}{Style.DIM}")

    _run_cmd(cmd, verbose=verbose, spinner=not verbose)

    if verbose:
        print(f"{Style.RST}")
    else:
        print()


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
                if key == "source":
                    keys.source = Path(proj_dir / val)
                elif key == "target":
                    keys.target = Path(proj_dir / val)
                elif key == "last_build":
                    if val == "-1":
                        keys.last_build = dt.min.replace(tzinfo=UTC)
                    else:
                        keys.last_build = dt.fromisoformat(val)
                elif key == "build_type" and val in BuildType:
                    keys.build_type = BuildType(val)
                elif key == "cxx_std":
                    keys.cxx_std = int(val)
                else:
                    setattr(keys, key, val)
            elif key not in keys:
                invalid_keys.add(key)

    if invalid_keys:
        msg_suf: str = ", ".join(f"{Style.YLW}{key}{Style.RST}" for key in invalid_keys)
        msg: str = f"invalid keys in {Constant.marker_file}: {msg_suf}"
        perr(msg, ExitCode.INVALID_KEYS)

    missing_keys: set[str] = {key for key, value in keys.__dict__.items() if value is None}
    if missing_keys:
        msg_suf: str = ", ".join(f"{Style.YLW}{key}{Style.RST}" for key in missing_keys)
        msg: str = f"missing keys in {Constant.marker_file}: {msg_suf}"
        perr(msg, ExitCode.MISSING_KEYS)

    return keys


def update_marker_file(proj_dir: Path, keys: MarkerFileKeys) -> None:
    with (proj_dir / Constant.marker_file).open("w", encoding="utf-8") as file:
        for key, value in keys.__dict__.items():
            if key in {"source", "target"}:
                file.write(f"{key} = {value.name}\n")
            elif key == "last_build":
                file.write(f"{key} = {dt.now(tz=UTC).isoformat()}\n")
            elif key == "build_type":
                file.write(f"{key} = {value.value}\n")
            else:
                file.write(f"{key} = {value}\n")
