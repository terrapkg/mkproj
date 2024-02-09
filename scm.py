import sys
from functools import cache
from subprocess import Popen

from requests import get

from .log import get_logger

log = get_logger("scm")


class Scm:
    repourl: str = ""
    branch: str = ""
    ver_scheme: str = ""

    def repo(self) -> str:
        log.fatal("Unexpected call to `ScmBase.repo()`.")
        sys.exit(1)

    def fetch_file_content(self, filename: str) -> str:
        log.fatal(f"Unexpected call to `ScmBase.fetch_file_content('{filename}')`.")
        sys.exit(1)

    def fetch_root_file_list(self) -> list[str]:
        log.fatal("Unexpected call to `ScmBase.fetch_root_file_list()`.")
        sys.exit(1)

    def fetch_version(self) -> str:
        log.fatal("Unexpected call to `ScmBase.fetch_version()`.")
        sys.exit(1)

    def clone(self) -> str:
        log.info("$ git clone {self.repourl}")
        if rc := Popen(["git", "clone", self.repourl]).wait():
            log.error(f"git returned non-zero exit code: {rc}")
            sys.exit(1)
        dir = self.repo().split("/")[-1]
        log.info("Cloned repo to ./{dir}")
        return dir


class GitHub(Scm):
    def __init__(self, repourl: str):
        self.repourl = repourl

    @cache
    def repo(self) -> str:  # type: ignore
        return self.repourl.removeprefix("https://github.com/")

    def fetch_file_content(self, filename: str) -> str:
        url = f"https://github.com/{self.repo()}/raw/{self.branch}/{filename}"
        print(end=f"scm: Downloading {url} ...")
        out = get(url, allow_redirects=True).text
        print(" done.")
        return out

    @cache
    def fetch_root_file_list(self) -> list[str]:  # type: ignore
        url = f"https://api.github.com/repos/{self.repo()}/contents/"
        if self.branch:
            url += f"?ref={self.branch}"
        print("scm: Fetching root list:")
        print(end=f"scm: GET {url} ...")
        repocontent = get(url)
        print(" done.")
        repocontent = repocontent.json()
        print(f"scm: Parsed response JSON, found {len(repocontent)} entries.")
        if not any(repocontent):
            exit("scm: Cannot continue with an empty repository.")
        if not self.branch:
            self.branch = repocontent[0]["url"].split("?ref=")[1]
            print(f"scm: Determined default branch `{self.branch}` from response")
        return [f["name"] for f in repocontent]

    def fetch_version(self) -> str:
        if not self.ver_scheme:
            # release
            url = f"https://api.github.com/repos/{self.repo()}/releases/latest"
            print(end=f"scm: GET {url} ...")
            releases = get(url).json()
            print(" done.")
            if any(releases):
                self.ver_scheme = "release"
                return releases[0]["tag_name"]
            # tags
            url = f"https://api.github.com/repos/{self.repo()}/tags"
            print(end=f"scm: GET {url} ...")
            tags = get(url).json()
            print(" done.")
            if any(tags):
                self.ver_scheme = "tag"
                return tags[0]["tag_name"]
            # we don't freaxing know
            print("scm: SCM does not have any releases/tags whatsoever.")
            print("scm: Cannot determine versioning scheme.")
            return ""
        if self.ver_scheme == "release":
            url = f"https://api.github.com/repos/{self.repo()}/releases/latest"
            print(end=f"scm: GET {url} ...")
            releases = get(url).json()
            print(" done.")
            if any(releases):
                return releases[0]["tag_name"]
            print("scm: ver_scheme specified as release but no releases in SCM.")
            return ""
        if self.ver_scheme == "tag":
            url = f"https://api.github.com/repos/{self.repo()}/tag"
            print(end=f"scm: GET {url} ...")
            tags = get(url).json()
            print(" done.")
            if any(tags):
                return tags[0]["tag_name"]
            print("scm: ver_scheme specified as tag but no tags in SCM.")
            return ""
        log.fatal("GitHub.fetch_version(): Unreachable code reached.")
        sys.exit(1)
