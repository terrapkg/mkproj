from os import path

import jinja2

tmplenv = jinja2.Environment(loader=jinja2.FileSystemLoader("mkproj/templates"))


def gen_scm_anda(name: str, spec: str, url: str, branch: str, dest: str):
    """Generates `anda.hcl` with SCM opts."""
    tmpl = tmplenv.get_template("anda-scm.hcl")
    x = tmpl.render(name=name, spec=spec, url=url, branch=branch)
    with open(path.join(dest, "anda.hcl"), "w+") as f:
        f.write(x)
    print(f"out: {dest}/anda.hcl")


def gen_anda(spec: str, dest: str):
    """Generates `anda.hcl` normally."""
    tmpl = tmplenv.get_template("anda.hcl")
    x = tmpl.render(spec=spec)
    with open(path.join(dest, "anda.hcl"), "w+") as f:
        f.write(x)
    print(f"out: {dest}/anda.hcl")
