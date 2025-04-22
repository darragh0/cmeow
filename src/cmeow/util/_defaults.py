from pathlib import Path

from cmeow.__init__ import __version__
from cmeow.util._enum import BuildType

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
    cmake: str = "3.25"
    std: int = 17
    build_type: str = BuildType.DEBUG
    version: str = "0.1.0"


class Constant:
    project_file: str = "cmeow.toml"
    src_dir: str = "src"
    target_dir: str = "target"
    cmake_lists_txt_str: str = _cmake_lists_txt_str
    main_src_file_str: str = _src_main_cpp_str
    main_src_file: str = "main.cpp"
    cmake_build_dir: str = "cmake_build"
    cmake_init_cmd: str = _cmake_init_cmd
    cmake_build_cmd: str = _cmake_build_cmd
    unsupported_stds: tuple[int] = (98, 3)
    supported_stds: tuple[int] = (11, 14, 17, 20)
    cmeow_versions: tuple[str] = (__version__,)
    cmake_build_files: tuple[str] = ("CMakeCache.txt", "cmake_install.cmake", "Makefile")
    cmake_build_dirs: tuple[str] = ("CMakeFiles",)
    cmake_base_files: tuple[str] = ("CMakeLists.txt",)
