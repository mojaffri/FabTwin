"""Build a host library; set CXX to a compiler path, or use --zig PATH."""

import argparse
import importlib.util
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--zig", type=Path)
    args = parser.parse_args()
    compiler = os.environ.get("CXX") or shutil.which("g++") or shutil.which("clang++")
    if not args.zig and not compiler:
        spec = importlib.util.find_spec("ziglang")
        if spec and spec.submodule_search_locations:
            args.zig = Path(next(iter(spec.submodule_search_locations))) / (
                "zig.exe" if sys.platform == "win32" else "zig"
            )
    if args.zig:
        command = [str(args.zig.resolve()), "c++"]
    elif compiler:
        command = [compiler]
    elif shutil.which("cmake"):
        subprocess.run(
            ["cmake", "-S", str(ROOT / "controller"), "-B", str(ROOT / "build")], check=True
        )
        subprocess.run(["cmake", "--build", str(ROOT / "build"), "--config", "Release"], check=True)
        subprocess.run(
            ["ctest", "--test-dir", str(ROOT / "build"), "-C", "Release", "--output-on-failure"],
            check=True,
        )
        return
    else:
        raise SystemExit(
            "Install a C++17 compiler + CMake, or pip install ziglang and pass --zig <path to zig>. No Python controller fallback is used."
        )
    suffix = ".dll" if sys.platform == "win32" else ".dylib" if sys.platform == "darwin" else ".so"
    (ROOT / "build").mkdir(exist_ok=True)
    flags = ["-std=c++17", "-O2", "-Wall", "-Wextra", "-shared"]
    if sys.platform != "win32":
        flags += ["-fPIC"]
    subprocess.run(
        command
        + flags
        + [
            "-I" + str(ROOT / "controller/include"),
            str(ROOT / "controller/src/bridge.cpp"),
            "-o",
            str(ROOT / "build" / ("fabtwin_controller" + suffix)),
        ],
        check=True,
    )
    print("Built host C++ controller in", ROOT / "build")
    test_binary = (
        ROOT / "build" / ("controller_tests.exe" if sys.platform == "win32" else "controller_tests")
    )
    subprocess.run(
        command
        + [
            "-std=c++17",
            "-O2",
            "-Wall",
            "-Wextra",
            "-I" + str(ROOT / "controller/include"),
            str(ROOT / "controller/tests/core_tests.cpp"),
            "-o",
            str(test_binary),
        ],
        check=True,
    )
    subprocess.run([str(test_binary)], check=True)


if __name__ == "__main__":
    main()
