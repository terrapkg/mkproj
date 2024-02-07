import re
from subprocess import Popen, PIPE
import os, sys
import typing
import toml
from .log import get_logger
from .util import some
from .anda import gen_scm_anda, gen_anda
from .scm import Scm

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
        cargo_toml = toml.loads(self.scm.get_file_content("Cargo.toml"))
        self.crate = cargo_toml.get("package", {}).get("name", "")
        if not self.crate:
            bsl.warn("Cannot get crate name")
        self.license = cargo_toml.get("package", {}).get("license", "")
        if not self.license:
            bsl.warn("Cannot get crate license")

    def rust2rpm(self) -> typing.Optional[str]:
        if Popen(["which", "rust2rpm"]).wait():
            bsl.error("rust2rpm is not installed.")
            sys.exit(1)
        proc = Popen(["rust2rpm", self.crate], stderr=PIPE)
        _, stderr = proc.communicate()
        if proc.returncode:
            bsl.error("Non-zero return code from rust2rpm")
            sys.exit(1)
        REGEX = r"^• Generated: (\N+)$"
        files = [m.group(1) for m in re.finditer(REGEX, str(stderr), flags=re.M)]
        return some(files, lambda f: f.endswith(".spec"))

    def edit_spec(self, specfile: str):
        bsl.debug("Reading spec")
        with open(specfile, "r") as f:
            content = f.read()
        bsl.info("Editing spec")
        content = re.sub(self.RE_LICENSE, content, r"\2" + self.license)
        content = re.sub(self.RE_DEVEL_FILES, content, r"\1")
        content = re.sub(self.RE_LICENSE_DEPS, content, "#license LICENSE.dependencies")
        content = re.sub(self.RE_PREP, content, r"\1_online\n\3")
        (content, n) = re.subn(self.RE_BUILD, content, "")
        if n != 2:
            bsl.warn(f"RE_BUILD substituted {n} times (expected 2 only)")
        bsl.debug("Writing spec")
        with open(specfile, "w") as f:
            f.write(content)
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
    pass


class Python(BuildSys):
    pass


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
