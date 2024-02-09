import re
import sys
import typing
from subprocess import PIPE, Popen
from functools import cache

import toml

from .anda import gen_anda, gen_scm_anda
from .log import get_logger
from .scm import Scm
from .util import run_show_output, some

bsl = get_logger("buildsys")


class BuildSys:
    name: str
    version: str
    scm: Scm

    def determine_name(self) -> None:
        bsl.error("Attempted to call BuildSys.determine_name()")
        sys.exit(1)

    def get_version(self) -> None:
        self.version = self.scm.fetch_version()

    def make_spec(self) -> None:
        if not self.name:
            self.determine_name()

    def __call__(self) -> None:
        bsl.error("Attempted to call BuildSys.__call__()")
        sys.exit(1)


class SpecGenerator(BuildSys):
    specpath: str
    versioning: str
    # TODO: everything??


class Rust(BuildSys):
    RE_LICENSE = re.compile(
        r"^(# FIXME: paste output of %%cargo_license_summary here\n)(License: {8})# FIXME(\n# [^\n]+)$",
        flags=re.M,
    )
    RE_DEVEL_FILES = re.compile(
        r"(%files\s+devel\n)((%(license|doc) [^\n]+\n)+)", flags=re.M
    )
    RE_LICENSE_DEPS = re.compile(r"^%license LICENSE\.dependencies$", flags=re.M)
    RE_PREP = re.compile(r"(%cargo_prep)(.+?)(\n%build)", flags=re.S)
    RE_BUILD = re.compile(r"^%{cargo_license.+$", flags=re.M)

    crate: str
    license: str

    def populate(self):
        cargo_toml = toml.loads(self.scm.fetch_file_content("Cargo.toml"))
        self.crate = cargo_toml.get("package", {}).get("name", "")
        if not self.crate:
            bsl.warn("Cannot get crate name")
        self.license = cargo_toml.get("package", {}).get("license", "")
        if not self.license:
            bsl.warn("Cannot get crate license")

    def rust2rpm(self) -> typing.Optional[str]:
        if Popen(["which", "rust2rpm"], stdout=PIPE, stderr=PIPE).wait():
            bsl.error("rust2rpm is not installed.")
            sys.exit(1)
        bsl.info("Running rust2rpm")
        rc, _, stderr = run_show_output(["rust2rpm", self.crate], "rust2rpm │ ")
        if rc:
            bsl.error(f"rust2rpm returned code {rc=}")
            sys.exit(1)
        REGEX = r" Generated: ([\w.-]+)"
        files = [m.group(1) for m in re.finditer(REGEX, stderr, flags=re.M)]
        bsl.info(f"rust2rpm generated {len(files)} file(s)")
        # assumption: rust2rpm only generates 1 .spec file all the time
        return some(files, lambda f: f.endswith(".spec"))

    def edit_spec(self, specfile: str):
        bsl.debug("Reading spec")
        with open(specfile, "r") as f:
            spec = f.read()
        bsl.info("Editing spec")
        spec = re.sub(self.RE_LICENSE, r"\2" + self.license, spec)
        spec = re.sub(self.RE_DEVEL_FILES, r"\1", spec)
        spec = re.sub(self.RE_LICENSE_DEPS, r"\#license LICENSE.dependencies", spec)
        spec = re.sub(self.RE_PREP, r"\1_online\n\3", spec)
        (spec, n) = re.subn(self.RE_BUILD, "", spec)
        if n != 2:
            bsl.warn(f"RE_BUILD substituted {n} times (expected 2 only)")
        bsl.debug("Writing spec")
        with open(specfile, "w") as f:
            f.write(spec)
        print(f"out: {specfile}")

    def __call__(self):
        self.populate()
        if not self.crate:
            bsl.error("Cannot continue without knowing crate name")
            bsl.error("Because that indicates Cargo.toml couldn't be parsed")
            sys.exit(1)
        if not (spec := self.rust2rpm()):
            bsl.error("rust2rpm did not generate a spec file.")
            sys.exit(1)
        self.edit_spec(spec)
        gen_anda(spec, ".")


class Go(BuildSys):
    def go2rpm(self, ref: str) -> str:
        if Popen(["which", "go2rpm"], stdout=PIPE, stderr=PIPE).wait():
            bsl.error("go2rpm is not installed.")
            sys.exit(1)
        rc, stdout, _ = run_show_output(["go2rpm", ref], "go2rpm │ ")
        if rc:
            bsl.error(f"go2rpm returned code {rc=}")
            sys.exit(1)
        return stdout.strip()

    def __call__(self):
        gen_anda(self.go2rpm(self.scm.repourl), ".")


class Python(BuildSys):
    @cache
    def get_pypi(self) -> str:
        rootfiles = self.scm.fetch_root_file_list()
        if "pyproject.toml" in rootfiles:
            pyproject = toml.loads(self.scm.fetch_file_content("pyproject.toml"))
            return pyproject.get("project", {}).get("name", "")
        elif "setup.py" in rootfiles:
            setuppy = self.scm.fetch_file_content("setup.py")
            res = re.findall(r'\s*name="(.+)"', setuppy, re.M)
            if len(res) != 1:
                bsl.error(f"Cannot parse setup.py, found name {len(res)} times.")
                sys.exit(1)
            return res[0]
        else:
            bsl.fatal("Cannot find files for getting PyPI package name.")
            sys.exit(1)

    def pyp2rpm(self, pypi: str):
        if Popen(["which", "pyp2rpm"], stdout=PIPE, stderr=PIPE).wait():
            bsl.error("pyp2rpm is not installed.")
            sys.exit(1)
        rc, stdout, _ = run_show_output(["pyp2rpm", pypi], "pyp2rpm │ ")
        if rc:
            bsl.error(f"pyp2rpm returned code {rc=}")
            sys.exit(1)
        bsl.info("Writing spec")
        with open(f"python-{pypi}.spec", "w+") as f:
            f.write(stdout)
        print(f"out: python-{pypi}.spec")
        return f"python-{pypi}.spec"

    def __call__(self):
        gen_anda(self.pyp2rpm(self.get_pypi()), ".")


class Make(BuildSys):
    pass


class CMake(BuildSys):
    pass


class Meson(BuildSys):
    pass


class Spec(BuildSys):
    specfile: str

    def __init__(self, specfile: str):
        self.specfile = specfile

    def __call__(self):
        scm = self.scm
        name = scm.repo().split()[-1]
        gen_scm_anda(name, self.specfile, scm.repourl, scm.branch, ".")


SYSID_TO_CLS: dict[str, type[BuildSys]] = {
    "rs": Rust,
    "go": Go,
    "py": Python,
    "make": Make,
    "cmake": CMake,
    "meson": Meson,
    "spec": Spec,
}
