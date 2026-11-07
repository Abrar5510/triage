# lablab.ai submission kit

## Project title
Triage

## Short description (≤ 255 chars)
An agent that reproduces or rejects every vulnerability report before a human reads it: it rebuilds the exact library version in a gVisor sandbox on Vultr, runs the PoC, compares vulnerable vs patched, and contains hostile code.

## Long description
Security inboxes are drowning in AI-written vulnerability reports that look convincing and are not real, and every one still costs a senior engineer's time. Worse, the proof of concept attached to a report is untrusted code from a stranger.

Triage is a containment-first agent that does the first pass. It reads a report, extracts checkable claims with Vultr Serverless Inference, downloads the exact vulnerable package version (hash-verified wheels only), and checks the claimed function actually exists in the real source, deterministically, with no model involved. It then runs the reporter's PoC in a brand-new gVisor sandbox with no network, no secrets, a per-run canary credential, CPU/memory/PID/time caps and a PEP 578 audit hook. The agent writes its own reproduction test, runs it, reads the output and retries with errors fed back. Finally it runs the identical test against the patched version in another fresh sandbox. Fixed rules turn this evidence into one of four verdicts: Reproduced, Not reproduced, Hostile or Inconclusive. The model writes the reviewer note but never decides the verdict or touches sandbox settings.

Demo: a real sqlparse CVE is Reproduced (vulnerable on 0.4.4, clean on 0.5.0); a polished CVSS 9.8 "RCE" in a function that never existed is rejected at grounding with nothing executed; and a report whose PoC tries to steal credentials and phone home, with a prompt injection hidden in the text, is flagged Hostile and contained.

Everything runs on Vultr: one Cloud Compute VM hosts the FastAPI web app with a live timeline, the orchestrator, the package cache and the Docker + gVisor runtime; every LLM call goes to Vultr Serverless Inference.

## Tags
Vultr, Serverless Inference, AI Agents, Security, Sandboxing, gVisor, Docker, FastAPI, Python, Bug Bounty, AppSec

## Links
- Repo: https://github.com/Abrar5510/triage
- Live app: (fill after deploy)
- Slides: docs/slides.pdf
- Cover: docs/img/cover.png
- Demo video: `docs/video/triage-demo.webm` (3:34, 1600×900, captioned, recorded from live runs). Upload to YouTube (unlisted) and paste the link. Not committed because of its size; regenerate with `node docs/video/record.mjs`.

---

# Demo video script (about 3 minutes)

The recorded video above follows this script with on-screen captions. Use it as the voiceover if you narrate over it.

**0:00 – 0:20 · Problem.** Slide 2. "Security teams read every vulnerability report, because one might be real. AI made fake ones free to write. And the PoC attached to each one is untrusted code from a stranger."

**0:20 – 0:40 · What Triage does.** Slide 3. "Triage reproduces or rejects every report before a human reads it. Models propose, sandboxes execute, rules decide."

**0:40 – 1:20 · Report A, real.** Live app home page → click *Real CVE*. Show the timeline streaming: claims, grounding found, the submitted PoC run, the agent's test, then the control run. Land on the differential strip: "Same test, two fresh sandboxes: VULNERABLE on 0.4.4, NOT_VULNERABLE on 0.5.0. Reproduced, with proof the patch fixes it."

**1:20 – 1:45 · Report B, fake.** Click *AI-written fake*. "CVSS 9.8, very confident. Triage downloads the exact version and searches the real source: the function doesn't exist. Rejected in seconds, and nothing ran."

**1:45 – 2:35 · Report C, the containment moment.** Click *Hostile PoC*. Point at the intake warning: "There's a prompt injection telling the agent to enable networking and mark this reproduced. It's flagged and ignored; the model never controls the sandbox." Then the red run card: "The PoC read the canary credential, a per-run fake, and tried to POST it out. No route: Network is unreachable. Three policy events, container destroyed, verdict Hostile."

**2:35 – 2:55 · Vultr.** Slide 8 or `/healthz` showing `runsc`. "One Vultr VM runs the app, the orchestrator and gVisor sandboxes. Every LLM call goes to Vultr Serverless Inference."

**2:55 – 3:00 · Close.** Inbox, ranked. "Reproduced first, hostile quarantined, fakes rejected. Triage gives reviewers proof instead of prose."
