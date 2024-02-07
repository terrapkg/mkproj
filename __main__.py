#!/bin/python3
import sys
import re
from . import spec
from .scm import Scm, GitHub
from .util import some
from typer import Argument, Option, Typer
from requests import get

app = Typer()


def determine_proj_type(files: list[str]) -> spec.BuildSys:
    if specfile := some(files, lambda x: x.endswith(".spec")):
        return spec.Spec(specfile)
    detected = []
    if "Cargo.toml" in files:
        detected.append("rs")
    if "go.mod" in files:
        detected.append("go")
    if "pyproject.toml" in files or "setup.py" in files:
        detected.append("py")
    if "Makefile" in files:
        detected.append("make")
    if "CMakeLists.txt" in files:
        detected.append("cmake")
    if "meson.build" in files:
        detected.append("meson")
    match len(detected):
        case 0:
            exit("ERROR: No buildsystem detected.")
        case 1:
            print(":: Found buildsystem: {detected[0]}")
            return spec.SYSID_TO_CLS[detected[0]]()
        case _:
            print(f"ERROR: Detected the following buildsystems: {', '.join(detected)}")
            exit("ERROR: Cannot determine project type.")


def main():
    if len(sys.argv) == 1:
        return app(args=["--help"])
    if some(sys.argv[1:], lambda arg: arg.startswith("-")):
        return app(args=["--help" if x == "-h" else x for x in sys.argv[1:]])
    arg = sys.argv[1]
    scm = None
    if re.match(r"^https://github\.com/.+", arg):
        print(":: Found SCM: GitHub")
        scm = GitHub(arg)
    if re.match(r"^https://gitlab\.com/.+", arg):
        print(":: Found SCM: GitLab")
        # TODO: GitLab support
    if not scm:
        exit("Cannot detect SCM.")
    files = scm.fetch_root_file_list()
    buildsys = determine_proj_type(files)
    buildsys()


if __name__ == "__main__":
    main()
