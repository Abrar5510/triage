"""SQLite persistence. One file, one connection per call, WAL so the web app reads while the agent writes."""
import json
import sqlite3
from contextlib import closing
from pathlib import Path

from . import config

SEED = Path(__file__).with_name("samples") / "seed.json"

SCHEMA = """
CREATE TABLE IF NOT EXISTS reports (
  id INTEGER PRIMARY KEY, title TEXT, raw_text TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'queued',
  verdict TEXT, confidence REAL, explanation TEXT, claims TEXT, grounding TEXT, intake TEXT,
  created_at TEXT DEFAULT (datetime('now')), finished_at TEXT
);
CREATE TABLE IF NOT EXISTS runs (
  id INTEGER PRIMARY KEY, report_id INTEGER NOT NULL, kind TEXT NOT NULL, attempt INTEGER, version TEXT,
  script TEXT, stdout TEXT, stderr TEXT, exit_code INTEGER, wall_ms INTEGER, peak_mem_mb REAL,
  kill_reason TEXT, events TEXT, runtime TEXT, result TEXT, created_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS events (
  id INTEGER PRIMARY KEY, report_id INTEGER NOT NULL, run_id INTEGER, stage TEXT, level TEXT, message TEXT,
  created_at TEXT DEFAULT (datetime('now'))
);
"""


def conn():
    c = sqlite3.connect(config.DB_PATH, timeout=30)
    c.row_factory = sqlite3.Row
    return c


def init():
    with closing(conn()) as c:
        c.execute("PRAGMA journal_mode=WAL")
        c.executescript(SCHEMA)
        # A restart mid-run leaves reports stuck; mark them so the inbox stays honest.
        c.execute("UPDATE reports SET status='done', verdict='INCONCLUSIVE', explanation='Interrupted by a server restart.' "
                  "WHERE status NOT IN ('done')")
        if not c.execute("SELECT 1 FROM reports LIMIT 1").fetchone():
            _seed(c)
        c.commit()


def _seed(c):
    """A fresh install opens on three recorded runs (one per verdict), so the inbox is never empty."""
    def put(table, row):
        c.execute(f"INSERT INTO {table} ({', '.join(row)}) VALUES ({', '.join('?' * len(row))})", list(row.values()))
    for r in json.loads(SEED.read_text()):
        runs, log = r.pop("runs"), r.pop("log")
        put("reports", {k: json.dumps(v) if k in ("claims", "grounding", "intake") and v is not None else v for k, v in r.items()})
        for run in runs:
            put("runs", {**run, "events": json.dumps(run["events"])})
        put("events", {"report_id": r["id"], "stage": "replay", "level": "info", "created_at": r["created_at"],
                       "message": "Recorded demo run, loaded at install. Press a demo button for a live triage."})
        for e in log:
            put("events", {k: v for k, v in e.items() if k != "id"})


def execute(sql, args=()):
    with closing(conn()) as c:
        cur = c.execute(sql, args)
        c.commit()
        return cur.lastrowid


def rows(sql, args=()):
    with closing(conn()) as c:
        return [dict(r) for r in c.execute(sql, args)]


def update_report(report_id, **fields):
    for k in ("claims", "grounding", "intake"):
        if k in fields and not isinstance(fields[k], str):
            fields[k] = json.dumps(fields[k])
    sets = ", ".join(f"{k}=?" for k in fields)
    execute(f"UPDATE reports SET {sets} WHERE id=?", (*fields.values(), report_id))


def event(report_id, stage, message, level="info", run_id=None):
    execute("INSERT INTO events (report_id, run_id, stage, level, message) VALUES (?,?,?,?,?)",
            (report_id, run_id, stage, level, message))


def add_run(report_id, kind, attempt, version, ev: dict, result):
    return execute(
        "INSERT INTO runs (report_id, kind, attempt, version, script, stdout, stderr, exit_code, wall_ms, peak_mem_mb, "
        "kill_reason, events, runtime, result) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (report_id, kind, attempt, version, ev["script"], ev["stdout"], ev["stderr"], ev["exit_code"], ev["wall_ms"],
         ev["peak_mem_mb"], ev["kill_reason"], json.dumps(ev["events"]), ev["runtime"], result))


def report(report_id):
    r = rows("SELECT * FROM reports WHERE id=?", (report_id,))
    if not r:
        return None
    r = r[0]
    for k in ("claims", "grounding", "intake"):
        r[k] = json.loads(r[k]) if r[k] else None
    r["runs"] = rows("SELECT * FROM runs WHERE report_id=? ORDER BY id", (report_id,))
    for run in r["runs"]:
        run["events"] = json.loads(run["events"] or "[]")
    r["log"] = rows("SELECT * FROM events WHERE report_id=? ORDER BY id", (report_id,))
    return r
