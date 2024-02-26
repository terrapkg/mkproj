#!/bin/python3
import re
import sys

from . import spec
from .scm import GitHub
from .upd import generate_upd
from .util import some

from typer import Argument, Option, Typer, Context

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
            print(f":: Found buildsystem: {detected[0]}")
            return spec.SYSID_TO_CLS[detected[0]]()
        case _:
            print(f"ERROR: Detected the following buildsystems: {', '.join(detected)}")
            exit("ERROR: Cannot determine project type.")


@app.callback(no_args_is_help=True)
def cb():
    """Program to generate files for a new Terra project."""
    pass


@app.command()
def rs(crate: str):
    """Make a new project with rust crate name."""
    pass


@app.command()
def scm(url: str):
    """Make a new project with url to repo."""
    scm = None
    if re.match(r"^https://github\.com/.+", url):
        print(":: Found SCM: GitHub")
        scm = GitHub(url)
    if re.match(r"^https://gitlab\.com/.+", url):
        print(":: Found SCM: GitLab")
        # TODO: GitLab support
    if not scm:
        exit("Cannot detect SCM.")
    files = scm.fetch_root_file_list()
    buildsys = determine_proj_type(files)
    buildsys.scm = scm
    buildsys()
    generate_upd(buildsys)


app()
