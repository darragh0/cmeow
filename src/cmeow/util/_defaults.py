from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from cmeow.util._enum import BuildType

if TYPE_CHECKING:
    from datetime import datetime as dt

_cmake_lists_txt_str: str = """\
cmake_minimum_required(VERSION {cmake_ver})

project({proj_name} LANGUAGES C CXX)

set(CMAKE_CXX_STANDARD {cmake_cxx_std})
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

string(TOLOWER "${{CMAKE_BUILD_TYPE}}" BUILD_TYPE_LOWER)
set(TARGET_DIR "${{CMAKE_SOURCE_DIR}}/target/${{BUILD_TYPE_LOWER}}")

set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${{TARGET_DIR}})
set(CMAKE_LIBRARY_OUTPUT_DIRECTORY ${{TARGET_DIR}}/lib)
set(CMAKE_ARCHIVE_OUTPUT_DIRECTORY ${{TARGET_DIR}}/lib)

file(GLOB_RECURSE SRC_FILES CONFIGURE_DEPENDS "${{CMAKE_SOURCE_DIR}}/src/*.cpp" \
"${{CMAKE_SOURCE_DIR}}/src/*.c")

add_executable(${{PROJECT_NAME}} ${{SRC_FILES}})
"""

_src_main_cpp_str: str = """\
#include <iostream>

int main() {
    std::cout << "Hello, World!" << std::endl;
    return 0;
}
"""

_cmake_init_cmd: str = "cmake -DCMAKE_BUILD_TYPE={build_type} -B {build_dir}"
_cmake_build_cmd: str = "cmake --build {build_dir}"


class ArgDefault:
    directory: Path = Path.cwd()
    cpp_file: str = "main.cpp"
    cmake: str = "3.25"
    std: int = 17
    src: str = "src"
    target: str = "target"
    build_type: str = BuildType.DEBUG


class Constant:
    program: str = "cmeow"
    project_file: str = f".{program}-project"
    cmake_lists_txt_str: str = _cmake_lists_txt_str
    src_main_cpp_str: str = _src_main_cpp_str
    cmake_init_cmd: str = _cmake_init_cmd
    cmake_build_dir: str = "cmake_build"
    cmake_build_cmd: str = _cmake_build_cmd


@dataclass
class ProjectFileKeys:
    last_build: dt | None = None
    project: str | None = None
    version: str | None = None
    cmake: str | None = None
    std: int | None = None
    build_type: BuildType | None = None
