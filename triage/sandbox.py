"""Disposable sandbox: one fresh container per run, destroyed afterwards.

Every run gets: no network, empty environment, read-only root, non-root user, all
capabilities dropped, CPU/memory/PID/time caps, and gVisor (runsc) when the host has it.
A per-run fake credential (the canary) is mounted where credential stealers look.
"""
import json
import secrets
import shutil
import subprocess
import time
import uuid
from functools import cache
from pathlib import Path

from . import config

HARNESS = Path(__file__).with_name("harness.py")
MARK = "@@TRIAGE_EVENT@@"
HOSTILE_KINDS = {"canary_read", "canary_probe", "canary_leak", "network_attempt", "dns_lookup", "process_spawn", "native_load"}


@cache
def runtime() -> str:
    """'runsc' (gVisor) if the Docker daemon has it, else 'runc' (hardened flags still apply)."""
    try:
        out = subprocess.run(["docker", "info", "--format", "{{json .Runtimes}}"],
                             capture_output=True, text=True, timeout=20).stdout
        return "runsc" if "runsc" in out else "runc"
    except Exception:
        return "runc"


def _docker(*args, timeout=30):
    return subprocess.run(["docker", *args], capture_output=True, text=True, timeout=timeout)


def run(script: str, site_dir: Path) -> dict:
    """Run `script` against the packages in `site_dir`. Returns the evidence for this run."""
    run_id = uuid.uuid4().hex[:12]
    work = config.CACHE / "runs" / run_id
    work.mkdir(parents=True)
    (work / "poc.py").write_text(script)
    shutil.copy(HARNESS, work / "harness.py")
    token = "AKIA" + secrets.token_hex(8).upper()
    canary = work / "credentials"
    canary.write_text(f"[default]\naws_access_key_id = {token}\naws_secret_access_key = triage-canary-{secrets.token_hex(16)}\n")

    name = f"triage-{run_id}"
    cmd = [
        "docker", "run", "-d", "--name", name,
        "--runtime", runtime(),
        "--network", "none",
        "--read-only", "--tmpfs", "/tmp:rw,nosuid,nodev,size=64m",
        "--user", "65534:65534",
        "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
        "--cpus", config.LIMIT_CPUS, "--memory", config.LIMIT_MEMORY, "--memory-swap", config.LIMIT_MEMORY,
        "--pids-limit", config.LIMIT_PIDS,
        "--env", "HOME=/home/triage", "--env", "PYTHONDONTWRITEBYTECODE=1",
        "-v", f"{work / 'poc.py'}:/work/poc.py:ro",
        "-v", f"{work / 'harness.py'}:/work/harness.py:ro",
        "-v", f"{site_dir}:/site:ro",
        "-v", f"{canary}:/home/triage/.aws/credentials:ro",
        "--workdir", "/tmp",
        config.SANDBOX_IMAGE, "python", "-B", "-S", "/work/harness.py",
    ]
    started = time.monotonic()
    kill_reason = None
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if p.returncode != 0:
            raise RuntimeError(f"sandbox failed to start: {p.stderr.strip()[:500]}")
        try:
            _docker("wait", name, timeout=config.LIMIT_SECONDS)
        except subprocess.TimeoutExpired:
            _docker("kill", name)
            kill_reason = f"wall-clock limit ({config.LIMIT_SECONDS}s)"
        wall_ms = int((time.monotonic() - started) * 1000)
        state = json.loads(_docker("inspect", "--format", "{{json .State}}", name).stdout or "{}")
        logs = _docker("logs", name, timeout=60)
        stdout, raw_err = logs.stdout, logs.stderr
    finally:
        _docker("rm", "-f", name)
        shutil.rmtree(work, ignore_errors=True)

    events, usage_kb, err_lines = [], None, []
    for line in raw_err.splitlines():
        if line.startswith(MARK):
            try:
                e = json.loads(line[len(MARK):])
            except ValueError:
                continue
            if e["kind"] == "_usage":
                usage_kb = e["detail"]
            else:
                events.append(e)
        else:
            err_lines.append(line)
    stderr = "\n".join(err_lines)
    if token in stdout or token in stderr:
        events.append({"kind": "canary_leak", "detail": "canary credential appeared in program output"})
    if state.get("OOMKilled"):
        kill_reason = f"memory limit ({config.LIMIT_MEMORY})"
    exit_code = state.get("ExitCode")
    if kill_reason is None and exit_code == 137:
        kill_reason = "killed (resource limit)"

    return {
        "script": script,
        "stdout": stdout[-20_000:],
        "stderr": stderr[-20_000:],
        "exit_code": exit_code,
        "wall_ms": wall_ms,
        "peak_mem_mb": round(usage_kb / 1024, 1) if usage_kb else None,
        "kill_reason": kill_reason,
        "events": events,
        "runtime": runtime(),
    }


def verdict_line(stdout: str) -> str | None:
    """The agent's scripts end with `TRIAGE_RESULT: VULNERABLE` or `TRIAGE_RESULT: NOT_VULNERABLE`."""
    for line in reversed(stdout.splitlines()):
        if line.startswith("TRIAGE_RESULT:"):
            v = line.split(":", 1)[1].strip().split()[0] if line.split(":", 1)[1].strip() else ""
            return v if v in ("VULNERABLE", "NOT_VULNERABLE") else None
    return None
