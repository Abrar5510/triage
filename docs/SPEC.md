# Triage: product and technical spec

Status: draft v1 · Owner: Abrar · Deadline: **Nov 9, 2026, 4:00 AM PKT**

## 1. One-liner

An agent that turns an incoming vulnerability report into a reproduced-or-rejected verdict, by running the report's claims in a disposable sandbox on Vultr and comparing the vulnerable version against the patched one.

## 2. Users and buyers

| Who | What they get |
|---|---|
| Open-source maintainers | Fake and low-quality reports filtered before they cost an evening. |
| Product security teams | A ranked inbox: reproduced reports first, with evidence attached. |
| Bug bounty platforms | Automated first-pass triage at intake, before a paid analyst looks. |

The human reviewer always makes the final decision. Triage orders the queue and supplies evidence.

## 3. Scope for the hackathon

**In scope**
- Python packages from PyPI only.
- Reports submitted as text through the web UI (paste or pick a sample).
- One sandbox run at a time per report, with a small retry budget.
- Three curated demo reports (real, fabricated, hostile).

**Out of scope (say so in the README)**
- Other ecosystems (npm, Go, native code). The design generalizes; the demo does not.
- Live targets of any kind. Triage only runs code against a local copy of a library inside the sandbox. It never touches a third-party system.
- Auto-publishing verdicts. Everything ends in a human review queue.

## 4. Agent pipeline

Each stage writes its output to the database so the UI can stream progress and the evidence bundle is complete.

| # | Stage | Input → output | Model |
|---|---|---|---|
| 1 | **Intake screen** | Raw report → flagged/clean, with reasons. Catches prompt-injection text aimed at the agent. | `nemotron-3.5-content-safety` |
| 2 | **Claim extraction** | Report → structured JSON: package, affected range, patched version, function, claimed impact, attached PoC (if any). | `glm-5.3-flash` |
| 3 | **Grounding** | Claims + real package source (downloaded by the orchestrator) → does the named function/module exist in the affected version? | `glm-5.3-flash` + deterministic source search |
| 4 | **Reproduce** | Claims + source → a test script that checks for the claimed behavior. Run in sandbox on the vulnerable version. On error, the output is fed back and the agent retries (max 3). | `glm-5.3` |
| 5 | **Control run** | The same script against the patched version, in a fresh sandbox. | none (deterministic) |
| 6 | **Verdict** | All runs + sandbox events → verdict, confidence, short explanation for the reviewer. | `glm-5.3` |

Rules the orchestrator enforces regardless of what the model says:
- Grounding failure → **Not reproduced**, no execution.
- Any sandbox policy event (blocked network, canary read, limit kill) caused by submitted code → **Hostile**, overrides everything else.
- Vulnerable run shows the behavior and patched run does not → eligible for **Reproduced**.
- Anything else → **Inconclusive**.

Model IDs are from the live list at `https://api.vultrinference.com/v1/models` on Nov 7, 2026. Keep them in one config value each so they can be swapped.

## 5. Sandbox design

**Runtime:** Docker with the gVisor `runsc` runtime on the Vultr VM. Fallback if gVisor will not install in time: plain Docker with the same flags (documented as a known gap).

**Per-run controls**

| Control | Setting |
|---|---|
| Network | Disabled for the run. |
| Filesystem | Read-only root; a small writable tmpfs for scratch. Package wheels and the script are mounted read-only. |
| Secrets | Empty environment. No host mounts beyond the read-only inputs. |
| Privileges | Non-root user, all capabilities dropped, no privilege escalation. |
| Limits | 1 CPU, 512 MB memory, 128 processes, 60 s wall clock. |
| Lifecycle | Container removed after every run. New container for every run, including the control run. |
| Canary | A fake credential file is placed in the sandbox. Any read of it is logged as a policy event. |

**Dependency flow:** the orchestrator downloads the exact wheels for the vulnerable and patched versions from PyPI into a host cache, verifies hashes, then mounts the relevant set read-only. The sandbox installs from the mount with no index access.

**Evidence captured per run:** script, stdout, stderr, exit code, wall time, peak memory, kill reason (if any), and sandbox policy events.

## 6. Threat model (short)

| Threat | Mitigation |
|---|---|
| Submitted PoC attacks the host | gVisor isolation, no privileges, read-only root, destroyed after use. |
| PoC tries to steal secrets | No secrets inside; canary detects the attempt and flags the report. |
| PoC tries to reach the network | No network during runs; attempt is recorded as a policy event. |
| PoC exhausts resources | CPU, memory, process and time caps; kill is recorded. |
| Report text manipulates the agent | Intake screening; orchestrator rules override model output; model never chooses sandbox settings. |
| Agent writes harmful code on its own | Same sandbox applies to agent-written code; no target outside the sandbox exists. |
| API key leakage | Key lives only in the orchestrator's environment on the VM. |

## 7. Web app

**Stack:** FastAPI, Jinja templates, a little vanilla JS with Server-Sent Events for live progress, SQLite. One process, one VM. Deployed behind Caddy for HTTPS on a public URL.

**Pages**
1. **Inbox:** list of reports with verdict badge, confidence, and time.
2. **Submit:** paste a report or pick one of the samples.
3. **Report detail:** the pipeline as a live timeline (stage by stage), the extracted claims, each sandbox run side by side (vulnerable vs patched), policy events highlighted in red, and the final verdict with explanation.

**API**

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/reports` | Submit a report, start the pipeline. |
| `GET` | `/api/reports` | List reports. |
| `GET` | `/api/reports/{id}` | Full report with claims, runs, verdict. |
| `GET` | `/api/reports/{id}/events` | SSE stream of pipeline progress. |

**Data model**
- `reports`: id, raw_text, status, verdict, confidence, explanation, created_at
- `claims`: report_id, json
- `runs`: id, report_id, kind (vulnerable / patched), attempt, script, stdout, stderr, exit_code, wall_ms, peak_mem_mb, kill_reason
- `events`: report_id, run_id (nullable), stage, level, message, created_at

## 8. Demo set

Chosen in hour one and verified before anything else is built on top of them.

| Report | Selection rule |
|---|---|
| **A: Real** | A publicly documented, already-fixed issue in a small pure-Python PyPI library, where the fixed release is clearly identified and the behavior can be checked locally in seconds on a CPU. |
| **B: Fabricated** | Written by us in the style of AI-generated reports, naming a function that does not exist in that library version. |
| **C: Hostile** | Written by us. Its attached script makes a benign-looking claim but also reads the planted canary file and attempts an outbound connection. Both are blocked and recorded. |

## 9. Judging criteria map

| Criterion | How Triage scores |
|---|---|
| Application of technology | Multi-model pipeline on Vultr Serverless Inference; real execution in gVisor sandboxes on Vultr Compute; differential vulnerable-vs-patched runs. |
| Presentation | One 3-minute story: the problem, three reports, three verdicts, the containment moment. Live timeline UI makes the agent's work visible. |
| Business value | Clear buyers (maintainers, product security, bounty platforms); saves senior-engineer hours on every fake report. |
| Originality | Containment is the reason the product exists, not a rule being satisfied. Differential reproduction as evidence. |

## 10. Build plan (PKT)

| Window | Goal | Done when |
|---|---|---|
| Sat 18:30 – 20:30 | Vultr VM up, Docker + gVisor installed, inference key working. Demo report A selected and checked by hand. | A hello-world container runs under `runsc`; one chat completion succeeds. |
| Sat 20:30 – Sun 01:00 | Sandbox runner + orchestrator rules, tested from the command line. | Report A reproduces on vulnerable, fails on patched; report C produces policy events. |
| Sun 01:00 – 07:00 | Sleep. | |
| Sun 07:00 – 12:00 | Agent stages 1–6 wired to Inference; SQLite persistence. | All three reports reach the right verdict end to end from the CLI. |
| Sun 12:00 – 17:00 | Web app: inbox, submit, live report detail. | Full flow works in the browser locally. |
| Sun 17:00 – 20:00 | Deploy to the Vultr VM with HTTPS. README setup section. | Public URL runs all three demos. |
| Sun 20:00 – 23:30 | Demo video, slides, cover image. | Video shows the containment moment clearly. |
| Sun 23:30 – Mon 03:00 | Buffer, polish, submit on lablab.ai. | Submitted with an hour to spare. |

**Cut list if behind (in order):** intake screening model → SSE live updates (fall back to polling) → gVisor (fall back to hardened Docker, disclosed) → retries.

## 11. Submission checklist

- [ ] Public GitHub repo, MIT license
- [ ] README: Vultr services used, architecture, how the agent executes real work
- [ ] App deployed on a Vultr VM, public URL
- [ ] Demo video with the containment moment
- [ ] Slide deck
- [ ] Cover image
- [ ] Project title, short and long description, tags on lablab.ai
- [ ] Optional: post on Vultr Community
