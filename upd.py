from . import spec, scm
from .spec import BuildSys


def write_upd(content: str):
    with open("update.rhai", "w+") as f:
        f.write(content)
    print("out: update.rhai")


def generate_upd(bs: BuildSys):
    if isinstance(bs, spec.Rust):
        return write_upd(f'rpm.version(crates("{bs.crate}");')
    if isinstance(bs, spec.Python):
        return write_upd(f'rpm.version(pypi("{bs.get_pypi()}"));')
    if isinstance(bs.scm, scm.GitHub):
        return write_upd(f'rpm.version(gh("{bs.scm.repo()}"));')
