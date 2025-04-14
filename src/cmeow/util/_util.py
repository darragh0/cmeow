from __future__ import annotations

import subprocess as sp
from datetime import UTC
from datetime import datetime as dt
from os import chdir
from pathlib import Path
from sys import exit as sexit
from time import perf_counter

from cmeow.util._console_io import Style, perr, pwarn, yn_input
from cmeow.util._defaults import BuildType, Constant, MarkerFileDict
from cmeow.util._errors import ExitCode


def build_proj(proj_dir: Path, target_dir: Path, build_type: BuildType, *, verbose: bool = False) -> float:
    chdir(proj_dir)
    print(f"    {Style.BLD}{Style.GRN}Compiling{Style.RST} {proj_dir.name} ({proj_dir!s})")

    elapsed: float
    cmd = ["cmake", "--build", f"{target_dir.name}/{build_type.value}/build"]

    if not verbose:
        start = perf_counter()
        sp.run(cmd, check=True, stdout=sp.DEVNULL, stderr=sp.DEVNULL)  # noqa: S603
        elapsed = perf_counter() - start
    else:
        print(f"{Style.GRY}", end="")
        start = perf_counter()
        sp.run(cmd, check=True)  # noqa: S603
        elapsed = perf_counter() - start
        print(f"{Style.RST}")

    return elapsed


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
        prompt = f"{Style.BLD}{Style.RED}!{Style.RST} Override existing project"
        exit_code = ExitCode.PROJ_EXISTS
    else:
        msg_pre = "Folder"
        prompt = "Initialize new project here"
        exit_code = ExitCode.DIR_EXISTS

    msg = f"{msg_pre} `{proj_dir.name}` already exists."
    print()
    pwarn(msg, end="\n\n")

    if not yn_input(f"{prompt}? (y/n): "):
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


def init_cmake(proj_dir: Path, target_dir: Path, build_type: BuildType, *, verbose: bool) -> bool:
    required: list[Path] = [
        target_dir / build_type.value / "build" / p_str
        for p_str in ("CMakeFiles", "CMakeCache.txt", "cmake_install.cmake", "Makefile")
    ]

    all_exist = all(p.is_dir() if p.name == "CMakeFiles" else p.is_file() for p in required)
    should_init = not all_exist

    if should_init:
        # TODO: security  # noqa: FIX002, TD002, TD003
        chdir(proj_dir)
        build_type_cap = build_type.value.capitalize()
        cmd = ["cmake", f"-DCMAKE_BUILD_TYPE={build_type_cap}", "-B", f"{target_dir.name}/{build_type.value}/build"]
        if not verbose:
            sp.run(cmd, check=True, stdout=sp.DEVNULL, stderr=sp.DEVNULL)  # noqa: S603
        else:
            print(f"\n{Style.GRY}{Style.BLD}Creating CMake project in {proj_dir!s}:{Style.RST}{Style.GRY}")
            sp.run(cmd, check=True)  # noqa: S603
            print(f"{Style.RST}")

        return True

    return False


def need_build(proj_dir: Path, last_build: dt) -> bool:
    for file in proj_dir.rglob("*"):
        if file.is_file():
            # Get the last modified timestamp
            timestamp = file.stat().st_mtime
            mod_time = dt.fromtimestamp(timestamp, tz=UTC)

            if mod_time > last_build:
                return True

    return False


def parse_marker_file_keys(proj_dir: Path) -> MarkerFileDict:  # noqa: C901
    marker_file: Path = proj_dir / Constant.marker_file
    keys: MarkerFileDict = {
        "last_build": None,
        "build_type": None,
        "project": None,
        "version": None,
        "source": None,
        "target": None,
    }

    invalid_keys: set[str] = set()
    # TODO: Validate vals  # noqa: FIX002, TD002, TD003
    with marker_file.open(encoding="utf-8") as file:
        content: list[str] = file.readlines()
        for line in content:
            key, val = line.split(" = ")

            if key in keys and keys[key] is None:
                val: str = val.rstrip()
                if key in {"source", "target"}:
                    keys[key] = Path(proj_dir / val)
                elif key == "last_build":
                    if val == "-1":
                        keys[key] = dt.min.replace(tzinfo=UTC)
                    else:
                        keys[key] = dt.fromisoformat(val)
                elif key == "build_type":
                    if val in BuildType:
                        keys[key] = BuildType(val)
                else:
                    keys[key] = val
            elif key not in keys:
                invalid_keys.add(key)

    if invalid_keys:
        msg_suf: str = ", ".join(f"{Style.YLW}{key}{Style.RST}" for key in invalid_keys)
        msg: str = f"invalid keys in {Constant.marker_file}: {msg_suf}"
        perr(msg, ExitCode.INVALID_KEYS)

    missing_keys: set[str] = {key for key, value in keys.items() if value is None}
    if missing_keys:
        msg_suf: str = ", ".join(f"{Style.YLW}{key}{Style.RST}" for key in missing_keys)
        msg: str = f"missing keys in {Constant.marker_file}: {msg_suf}"
        perr(msg, ExitCode.MISSING_KEYS)

    return keys
