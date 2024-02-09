import os
import sys
import time
from contextlib import suppress
from multiprocessing import Process, Queue
from subprocess import PIPE, Popen
from typing import IO, Callable, Optional, TypeVar

T = TypeVar("T")


def some(arr: list[T], f: Callable[[T], bool]) -> Optional[T]:
    for x in arr:
        if f(x):
            return x
    return None


def prefix_lines(s: str, prefix: str) -> str:
    return "\n".join([f"{prefix}{line}" for line in s.splitlines()])


def _just_read(qin: Queue, qres: Queue, fd: IO[bytes]):
    os.set_blocking(fd.fileno(), False)
    while True:
        with suppress(TypeError):
            if not (r := fd.read(1)):
                if not qin.empty():
                    break
                time.sleep(0.05)
                continue
            qres.put_nowait(r)
    qin.get()


def run_show_output(cmd: list[str], prefix: str = "") -> tuple[int, str, str]:
    # TODO: optimizations?
    print(end=f"\n{prefix}", flush=True)
    # Cannot use universal_newlines because it replaces \r with \n
    proc = Popen(cmd, stdout=PIPE, stderr=PIPE, bufsize=0)
    assert proc.stdout
    assert proc.stderr
    qiout, qierr, qrout, qrerr = Queue(), Queue(), Queue(), Queue()
    th_out = Process(target=_just_read, args=[qiout, qrout, proc.stdout])
    th_err = Process(target=_just_read, args=[qierr, qrerr, proc.stderr])
    th_out.start()
    th_err.start()
    out, err, tmpout, tmperr = "", "", b"", b""
    while True:
        while not qrout.empty():
            tmpout += qrout.get_nowait()
        with suppress(TypeError):
            out += (sout := tmpout.decode("utf-8"))
            tmpout = b""
            sys.stdout.write(
                sout.replace("\n", f"\n{prefix}").replace("\r", f"\r{prefix}")
            )
        while not qrerr.empty():
            tmperr += qrerr.get_nowait()
        with suppress(TypeError):
            err += (serr := tmperr.decode("utf-8"))
            tmperr = b""
            sys.stderr.write(
                serr.replace("\n", f"\n{prefix}").replace("\r", f"\r{prefix}")
            )
        if qrerr.empty() and qrout.empty() and (rc := proc.poll()) is not None:
            break
    if len(tmpout) > 0:
        print(f"Some bytes can't be decoded: {tmpout}")
    qiout.put(0)
    qierr.put(0)
    th_out.join()
    th_err.join()
    print()
    return rc, out, err


# if __name__ == "__main__":
#     rc, out, err = run_show_output(["rust2rpm", "anda"], "hai > ")
#     print()
#     print(f"{rc=}, {out=}, {err=}")
