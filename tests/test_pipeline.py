"""End-to-end check of the three demo reports with the model stubbed out.

Exercises the real sandbox (needs Docker), real PyPI fetches, real grounding and the verdict rules.
Run:  .venv/bin/python -m pytest -q tests   or   .venv/bin/python tests/test_pipeline.py
"""
import json
import os
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("TRIAGE_DB", str(Path(tempfile.mkdtemp()) / "test.db"))

from triage import db, llm, pipeline  # noqa: E402

SAMPLES = ROOT / "triage" / "samples"

REPRO = """import sqlparse

def check():
    try:
        sqlparse.parse('[' * 10000 + ']' * 10000)
        print('parsed fine')
        return False
    except RecursionError:
        print('RecursionError raised')
        return True
    except Exception as e:
        print('handled:', type(e).__name__)
        return False
"""


def fake_chat(model, messages, **kw):
    system = messages[0]["content"] if messages[0]["role"] == "system" else ""
    user = messages[-1]["content"]
    if "extract checkable claims" in system:
        poc = re.search(r"```python\n(.*?)```", user, re.S)
        fn = re.search(r"`(sqlparse\.[\w.]+)\(", user)
        claims = {"title": "t", "package": "sqlparse", "affected_version": "0.4.4",
                  "patched_version": "0.5.0" if "0.5.0" in user else None,
                  "function": fn.group(1) if fn else None, "vuln_class": "x", "claimed_impact": "x",
                  "trigger": "x", "has_poc": bool(poc), "poc": poc.group(1) if poc else None}
        return json.dumps(claims)
    if "reproduction test" in system:
        return f"```python\n{REPRO}```"
    return "safe" if model.startswith("nemotron") else "Reviewer note."


def run(sample):
    rid = db.execute("INSERT INTO reports (raw_text) VALUES (?)", ((SAMPLES / sample).read_text(),))
    pipeline.process(rid)
    return db.report(rid)


def test_three_demo_verdicts():
    llm.chat = fake_chat
    db.init()

    a = run("a_real_sqlparse_recursion.md")
    assert a["verdict"] == "REPRODUCED", a["explanation"]
    assert [r["result"] for r in a["runs"] if r["kind"] != "submitted"] == ["VULNERABLE", "NOT_VULNERABLE"]

    b = run("b_fabricated_eval.md")
    assert b["verdict"] == "NOT_REPRODUCED" and not b["runs"], b["explanation"]
    assert b["grounding"]["found"] is False

    c = run("c_hostile_canary.md")
    assert c["verdict"] == "HOSTILE", c["explanation"]
    kinds = {e["kind"] for e in c["runs"][0]["events"]}
    assert {"canary_read", "network_attempt"} <= kinds, kinds
    assert c["intake"]["flagged"] is True
    print("ok: REPRODUCED / NOT_REPRODUCED / HOSTILE", sorted(kinds))


def test_playground_attacks():
    """Every one-click attack on /sandbox is caught, capped or killed, and leaks no secret."""
    from triage import config, sandbox
    from triage.attacks import ATTACKS
    empty = config.CACHE / "empty"
    empty.mkdir(parents=True, exist_ok=True)
    expect = {"steal": "canary_read", "exfil": "network_attempt", "shell": "process_spawn", "fork": "process_spawn"}
    for key, (_, _, code) in ATTACKS.items():
        r = sandbox.run(code, empty, seconds=10)
        kinds = {e["kind"] for e in r["events"]}
        if key in expect:
            assert expect[key] in kinds, (key, kinds)
        if key in ("memory", "hang"):
            assert r["kill_reason"], key
        if key == "env":
            assert "none." in r["stdout"], r["stdout"]
        if key == "write":
            assert "WROTE" not in r["stdout"], r["stdout"]
    print("ok: all", len(ATTACKS), "playground attacks contained")


if __name__ == "__main__":
    test_three_demo_verdicts()
    test_playground_attacks()
