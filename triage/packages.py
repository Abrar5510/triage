"""Fetch exact package versions from PyPI (orchestrator side) and ground claims in real source.

Only binary wheels are accepted: building an sdist would run untrusted setup.py code on the
host. pip verifies the hashes PyPI publishes. Wheels are unpacked into a per-version
directory that is later mounted read-only into the sandbox.
"""
import platform
import re
import subprocess
import sys
import zipfile
from pathlib import Path

from . import config


class NotOnPyPI(Exception):
    """The package or version the report names does not exist."""


def _arch():
    m = platform.machine().lower()
    return {"arm64": "aarch64", "amd64": "x86_64"}.get(m, m)


def fetch(package: str, version: str) -> Path:
    """Return a directory containing `package==version` and its dependencies, unpacked."""
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,100}", package or "") or \
       not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.+!_-]{0,50}", version or ""):
        raise NotOnPyPI(f"invalid package spec {package!r}=={version!r}")
    site = config.CACHE / "site" / f"{package.lower()}-{version}"
    if (site / ".complete").exists():
        return site
    wheels = config.CACHE / "wheels" / f"{package.lower()}-{version}"
    wheels.mkdir(parents=True, exist_ok=True)
    arch = _arch()
    cmd = [sys.executable, "-m", "pip", "download", f"{package}=={version}", "-d", str(wheels),
           "--only-binary=:all:", "--python-version", config.SANDBOX_PYTHON,
           "--implementation", "cp", "--disable-pip-version-check", "--no-input",
           "--platform", f"manylinux_2_28_{arch}", "--platform", f"manylinux_2_17_{arch}",
           "--platform", f"manylinux2014_{arch}", "--platform", "any"]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if p.returncode != 0:
        err = p.stderr.strip()
        if "No matching distribution" in err or "Could not find a version" in err:
            raise NotOnPyPI(f"{package}=={version} has no installable release on PyPI")
        raise RuntimeError(f"pip download failed: {err[-800:]}")
    site.mkdir(parents=True, exist_ok=True)
    for whl in wheels.glob("*.whl"):
        with zipfile.ZipFile(whl) as z:
            z.extractall(site)  # zipfile strips absolute paths and '..' components
    (site / ".complete").touch()
    return site


def latest_version(package: str) -> str | None:
    """Newest version pip can see. Used when a report does not name the patched version."""
    p = subprocess.run([sys.executable, "-m", "pip", "index", "versions", package, "--disable-pip-version-check"],
                       capture_output=True, text=True, timeout=60)
    m = re.search(r"\((\S+)\)", p.stdout)
    return m.group(1) if m else None


def ground(site: Path, symbol: str | None) -> dict:
    """Deterministically check that `symbol` (e.g. 'sqlparse.utils.eval_expression') exists in the source.

    Returns {"found": bool, "locations": [...], "snippet": str}. No model is involved, so a
    persuasive report cannot talk its way past this step.
    """
    if not symbol:
        return {"found": True, "locations": [], "snippet": "", "note": "report names no specific function"}
    name = re.split(r"[.:]", symbol.strip().rstrip("()"))[-1]
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
        return {"found": False, "locations": [], "snippet": "", "note": f"not a valid identifier: {symbol!r}"}
    pat = re.compile(rf"^\s*(?:async\s+def|def|class)\s+{name}\b|^{name}\s*=")
    locations, snippet = [], ""
    for f in sorted(site.rglob("*.py")):
        try:
            lines = f.read_text(errors="replace").splitlines()
        except OSError:
            continue
        for i, line in enumerate(lines):
            if pat.search(line):
                rel = f.relative_to(site).as_posix()
                locations.append(f"{rel}:{i + 1}")
                if not snippet:
                    indent = len(line) - len(line.lstrip())
                    body = [line]
                    for nxt in lines[i + 1:i + 80]:
                        if nxt.strip() and len(nxt) - len(nxt.lstrip()) <= indent and not nxt.lstrip().startswith((")", "]", "@")):
                            break
                        body.append(nxt)
                    snippet = f"# {rel}:{i + 1}\n" + "\n".join(body)
    return {"found": bool(locations), "locations": locations[:20], "snippet": snippet[:6000], "symbol": name}


def module_files(site: Path, package: str, limit=40) -> list[str]:
    """Top-level file listing, given to the model so it writes imports that exist."""
    top = package.lower().replace("-", "_")
    files = [f.relative_to(site).as_posix() for f in site.rglob("*.py") if f.relative_to(site).parts[0].lower() == top]
    return sorted(files)[:limit]
