"""Triage web app: inbox, submit, live report detail. Run: uvicorn triage.app:app"""
import asyncio
import json
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from . import config, db, pipeline, sandbox

HERE = Path(__file__).parent
SAMPLES = {
    "real": ("a_real_sqlparse_recursion.md", "Real CVE", "A documented, already-fixed DoS in sqlparse 0.4.4."),
    "fabricated": ("b_fabricated_eval.md", "AI-written fake", "Polished CVSS 9.8 RCE in a function that does not exist."),
    "hostile": ("c_hostile_canary.md", "Hostile PoC", "A plausible bug whose PoC steals credentials and phones home."),
}
VERDICT_ORDER = "CASE verdict WHEN 'REPRODUCED' THEN 0 WHEN 'HOSTILE' THEN 1 WHEN 'INCONCLUSIVE' THEN 2 WHEN 'NOT_REPRODUCED' THEN 3 ELSE -1 END"


@asynccontextmanager
async def lifespan(_):
    db.init()
    pipeline.start_worker()
    yield


app = FastAPI(title="Triage", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=HERE / "static"), name="static")
templates = Jinja2Templates(directory=HERE / "templates")


def sample_text(key):
    return (HERE / "samples" / SAMPLES[key][0]).read_text()


def stats():
    r = db.rows("SELECT verdict, COUNT(*) n FROM reports WHERE status='done' GROUP BY verdict")
    s = {row["verdict"]: row["n"] for row in r}
    s["total"] = sum(s.values())
    s["runs"] = db.rows("SELECT COUNT(*) n FROM runs")[0]["n"]
    return s


@app.get("/", response_class=HTMLResponse)
def inbox(request: Request):
    reports = db.rows(f"SELECT id, title, status, verdict, confidence, created_at FROM reports "
                      f"ORDER BY status='done', {VERDICT_ORDER}, id DESC LIMIT 100")
    return templates.TemplateResponse(request, "inbox.html", {
        "reports": reports, "stats": stats(), "samples": SAMPLES, "runtime": sandbox.runtime(), "config": config})


@app.get("/submit", response_class=HTMLResponse)
def submit_page(request: Request, sample: str | None = None):
    text = sample_text(sample) if sample in SAMPLES else ""
    return templates.TemplateResponse(request, "submit.html", {"text": text, "samples": SAMPLES, "chosen": sample})


@app.post("/submit")
def submit_form(text: str = Form(...)):
    return RedirectResponse(f"/reports/{_submit(text)}", status_code=303)


@app.post("/run/{key}")
def run_sample(key: str):
    if key not in SAMPLES:
        raise HTTPException(404)
    return RedirectResponse(f"/reports/{_submit(sample_text(key))}", status_code=303)


def _submit(text: str) -> int:
    text = text.strip()
    if not text:
        raise HTTPException(400, "Empty report")
    if len(text) > config.MAX_REPORT_CHARS:
        raise HTTPException(413, f"Report longer than {config.MAX_REPORT_CHARS} characters")
    try:
        return pipeline.submit(text)
    except OverflowError:
        raise HTTPException(429, "Triage queue is full, try again in a minute")


@app.get("/reports/{rid}", response_class=HTMLResponse)
def report_page(request: Request, rid: int):
    r = db.report(rid)
    if not r:
        raise HTTPException(404)
    return templates.TemplateResponse(request, "report.html", {"r": r, "config": config})


@app.get("/reports/{rid}/panel", response_class=HTMLResponse)
def report_panel(request: Request, rid: int):
    """Server-rendered body of the report page; the live view swaps it in as evidence arrives."""
    r = db.report(rid)
    if not r:
        raise HTTPException(404)
    return templates.TemplateResponse(request, "_panel.html", {"r": r, "config": config})


# ---------- JSON API ----------

@app.post("/api/reports")
async def api_submit(request: Request):
    body = await request.json()
    return JSONResponse({"id": _submit(str(body.get("text", "")))}, status_code=201)


@app.get("/api/reports")
def api_list():
    return db.rows("SELECT id, title, status, verdict, confidence, created_at, finished_at FROM reports ORDER BY id DESC LIMIT 200")


@app.get("/api/reports/{rid}")
def api_report(rid: int):
    r = db.report(rid)
    if not r:
        raise HTTPException(404)
    r["events"] = db.rows("SELECT * FROM events WHERE report_id=? ORDER BY id", (rid,))
    return r


@app.get("/api/reports/{rid}/events")
async def api_events(rid: int, request: Request, after: int = 0):
    """Server-Sent Events: pipeline progress as it happens. Ends with an `end` event when the verdict lands."""
    async def stream():
        last = after
        while not await request.is_disconnected():
            for e in db.rows("SELECT * FROM events WHERE report_id=? AND id>? ORDER BY id", (rid, last)):
                last = e["id"]
                yield f"id: {e['id']}\ndata: {json.dumps(e)}\n\n"
            status = db.rows("SELECT status FROM reports WHERE id=?", (rid,))
            if not status or status[0]["status"] == "done":
                yield "event: end\ndata: {}\n\n"
                return
            await asyncio.sleep(0.5)
    return StreamingResponse(stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.get("/healthz")
def healthz():
    return {"ok": True, "runtime": sandbox.runtime(), "inference_key": bool(config.INFERENCE_KEY)}
