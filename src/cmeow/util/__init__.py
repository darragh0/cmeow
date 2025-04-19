from __future__ import annotations

from cmeow.util._console_io import write, writeln
from cmeow.util._defaults import BuildType, MarkerFileKeys
from cmeow.util._parser import init_parser
from cmeow.util._util import (
    build_proj,
    check_dir_exists,
    check_proj_exists,
    cmake_files_exist,
    find_proj_dir,
    init_cmake,
    mk_proj_files,
    need_build,
    parse_marker_file_keys,
    run_cmd,
    update_marker_file,
)

__all__: list[str] = [
    "BuildType",
    "MarkerFileKeys",
    "build_proj",
    "check_dir_exists",
    "check_proj_exists",
    "cmake_files_exist",
    "find_proj_dir",
    "init_cmake",
    "init_parser",
    "mk_proj_files",
    "need_build",
    "parse_marker_file_keys",
    "run_cmd",
    "update_marker_file",
    "write",
    "writeln",
]
