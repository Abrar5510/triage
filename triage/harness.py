"""Runs INSIDE the sandbox, before the untrusted script.

It installs a CPython audit hook (PEP 578) that reports file opens of the planted canary,
outbound socket activity and process spawns. Audit hooks cannot be removed once added, and
events go to a private duplicate of stderr, so a script that closes or redirects its own
stderr cannot hide them. A sandbox policy event is a fact the orchestrator acts on; the
model never sees or decides sandbox settings.

This file is standard library only and must not import anything from the triage package.
"""
import json
import os
import resource
import runpy
import sys
import traceback

MARK = "@@TRIAGE_EVENT@@"
CANARY_DIR = "/home/triage/.aws"
_out = os.fdopen(os.dup(2), "w", buffering=1)
_seen = set()


def emit(kind, detail):
    key = (kind, detail)
    if key in _seen:
        return
    _seen.add(key)
    _out.write(MARK + json.dumps({"kind": kind, "detail": detail}) + "\n")


def _path(arg):
    try:
        return os.path.abspath(os.fsdecode(arg))
    except Exception:
        return ""


def hook(event, args):
    if event == "open" and args and isinstance(args[0], (str, bytes, os.PathLike)):
        p = _path(args[0])
        if p.startswith(CANARY_DIR):
            emit("canary_read", p)
    elif event in ("os.listdir", "os.scandir") and args and args[0] is not None:
        if _path(args[0]).startswith(CANARY_DIR):
            emit("canary_probe", _path(args[0]))
    elif event == "socket.connect":
        emit("network_attempt", f"connect to {args[1]!r}")
    elif event == "socket.sendto":
        emit("network_attempt", f"sendto {args[1]!r}")
    elif event == "socket.getaddrinfo":
        emit("dns_lookup", f"resolve {args[0]!r}")
    elif event in ("subprocess.Popen", "os.system", "os.exec", "os.posix_spawn", "os.spawn", "pty.spawn"):
        emit("process_spawn", f"{event}: {str(args[:2])[:200]}")
    elif event == "ctypes.dlopen":
        emit("native_load", f"dlopen {args[0]!r}")


def main():
    sys.addaudithook(hook)
    sys.path.insert(0, "/site")
    sys.argv = ["/work/poc.py"]
    code = 0
    try:
        runpy.run_path("/work/poc.py", run_name="__main__")
    except SystemExit as e:
        code = e.code if isinstance(e.code, int) else (0 if e.code is None else 1)
    except BaseException:
        traceback.print_exc()
        code = 1
    sys.stdout.flush()
    peak_kb = max(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                  resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss)
    _out.write(MARK + json.dumps({"kind": "_usage", "detail": peak_kb}) + "\n")
    os._exit(code)


main()
