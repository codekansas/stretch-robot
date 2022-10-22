#!/usr/bin/env python
# pylint: disable=import-outside-toplevel

import multiprocessing
import os
import platform
import shutil
import subprocess
import sysconfig
from pathlib import Path

from setuptools import Extension, setup
from setuptools.command.build_ext import build_ext


class CMakeExtension(Extension):
    def __init__(self, name: str) -> None:
        super().__init__(name, sources=[])

        self.source_path = os.path.abspath(name)
        self.name = name


class CMakeBuild(build_ext):
    """Defines a build command for CMake projects."""

    cmake_prefix_path: str
    cmake_cxx_flags: str
    python_path: str

    def run(self) -> None:
        import pybind11  # pylint: disable=import-error

        if not shutil.which("cmake"):
            raise RuntimeError("CMake installation not found")

        cmake_cxx_flags = [
            "-fPIC",
            "-Wl,-undefined,dynamic_lookup",
            "-Wno-unused-command-line-argument",
        ]

        system = platform.system()
        if system == "Darwin":
            cmake_cxx_flags += ["-mmacosx-version-min=10.10"]

        # System include paths.
        cmake_include_dirs = [pybind11.get_include()]
        python_include_path = sysconfig.get_path("include", scheme="posix_prefix")
        if python_include_path is not None:
            cmake_include_dirs += [python_include_path]
        cmake_cxx_flags += [f"-isystem {dir_name}" for dir_name in cmake_include_dirs]

        # Sets paths to various CMake stuff.
        self.cmake_prefix_path = ";".join([pybind11.get_cmake_dir()])
        self.cmake_cxx_flags = " ".join(cmake_cxx_flags)

        # Gets the path to the Python installation.
        if not (python_path := shutil.which("python")):
            raise RuntimeError("Python path not found")
        self.python_path = python_path

        for ext in self.extensions:
            assert isinstance(ext, CMakeExtension)
            self.build_cmake(ext)

    def build_cmake(self, ext: CMakeExtension) -> None:
        config = "Debug" if self.debug else "Release"

        cmake_args = [
            f"-DCMAKE_LIBRARY_OUTPUT_DIRECTORY={os.path.abspath(ext.name)}",
            f"-DCMAKE_PREFIX_PATH={self.cmake_prefix_path}",
            f"-DPYTHON_EXECUTABLE:FILEPATH={self.python_path}",
            f"-DCMAKE_BUILD_TYPE={config}",
            f"-DCMAKE_CXX_FLAGS='{self.cmake_cxx_flags}'",
        ]

        env = os.environ.copy()

        # Builds CMake to a temp directory.
        build_temp = os.path.abspath(self.build_temp)
        if not os.path.exists(build_temp):
            os.makedirs(build_temp)
        subprocess.check_call(["cmake", f"-S{ext.source_path}", f"-B{build_temp}"] + cmake_args, env=env)

        # Compiles the project.
        build_lib = os.path.abspath(self.build_lib)
        if not os.path.exists(build_lib):
            os.makedirs(build_lib)
        subprocess.check_call(
            [
                "cmake",
                "--build",
                build_temp,
                "--",
                f"-j{multiprocessing.cpu_count()}",
            ],
            cwd=build_lib,
            env=env,
        )

        # Runs stubgen, if it is installed.
        if shutil.which("stubgen") is not None:
            project_root = Path(__file__).resolve().parent
            subprocess.check_call(["stubgen", "-p", "stretch.cpp", "-o", "."], cwd=project_root, env=env)


with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="stretch",
    version="0.0.1",
    description="Stretch robot project",
    author="Benjamin Bolte",
    url="https://github.com/codekansas/stretch-robot",
    long_description=long_description,
    long_description_content_type="text/markdown",
    classifiers=[
        "Programming Language :: Python :: 3",
    ],
    ext_modules=[CMakeExtension("stretch/cpp")],
    cmdclass={"build_ext": CMakeBuild},
    setup_requires=[
        "pybind11",
        "mypy",
    ],
    install_requires=[
        "aiohttp",
        "aiortc",
    ],
    python_requires=">=3.8",
    extras_require={
        "dev": {
            "black",
            "darglint",
            "flake8",
            "mypy-extensions",
            "mypy",
            "pylint",
            "pytest",
            "types-setuptools",
            "typing_extensions",
        },
    },
)
