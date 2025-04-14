from __future__ import annotations

from enum import EnumMeta, StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, TypedDict

if TYPE_CHECKING:
    from datetime import datetime as dt

_cmake_base_str: str = """\
cmake_minimum_required(VERSION {cmake_ver})

project({proj_name} LANGUAGES C CXX)

set(CMAKE_CXX_STANDARD {cmake_cxx_std})
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

string(TOLOWER "${{CMAKE_BUILD_TYPE}}" BUILD_TYPE_LOWER)
set(TARGET_DIR "${{CMAKE_SOURCE_DIR}}/{target_dir}/${{BUILD_TYPE_LOWER}}")

set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${{TARGET_DIR}})
set(CMAKE_LIBRARY_OUTPUT_DIRECTORY ${{TARGET_DIR}}/lib)
set(CMAKE_ARCHIVE_OUTPUT_DIRECTORY ${{TARGET_DIR}}/lib)

file(GLOB_RECURSE SRC_FILES CONFIGURE_DEPENDS "${{CMAKE_SOURCE_DIR}}/{src_dir}/*.cpp" \
"${{CMAKE_SOURCE_DIR}}/{src_dir}/*.c")

add_executable(${{PROJECT_NAME}} ${{SRC_FILES}})
"""

_src_main_cpp_base_str: str = """\
#include <iostream>

int main() {
    std::cout << "Hello, World!" << std::endl;
    return 0;
}
"""


class _BuildTypeMeta(EnumMeta):
    def __contains__(cls, b: str) -> bool:
        return b in cls._value2member_map_


class BuildType(StrEnum, metaclass=_BuildTypeMeta):
    DEBUG = "debug"
    RELEASE = "release"


class Constant:
    program: str = "cmeow"
    marker_file: str = f".{program}-project"
    cmake_base_str: str = _cmake_base_str
    src_main_cpp_base_str: str = _src_main_cpp_base_str


class Default:
    directory: Path = Path.cwd()
    cpp_file: str = "main.cpp"
    cmake: str = "3.25"
    std: int = 17
    src: str = "src"
    target: str = "target"
    build_type: str = BuildType.DEBUG


class MarkerFileDict(TypedDict):
    last_build: dt | None
    build_type: BuildType | None
    project: str | None
    version: str | None
    source: Path | None
    target: Path | None
