# lablab.ai submission kit

## Project title
Triage

## Short description (≤ 255 chars)
curl killed its bug bounty over fake AI reports. Triage checks every report for you: it rebuilds the exact library in a gVisor sandbox on Vultr, proves vulnerable vs patched, rejects fakes, contains hostile PoCs. Try to break it live.

## Long description
In January 2026, curl ended its bug bounty because its maintainers were drowning in AI-written vulnerability reports about bugs that did not exist. AI made reports free to write. Checking them still costs a senior engineer, and the proof of concept attached to each one is untrusted code from a stranger.

Triage does the checking. It extracts checkable claims with Vultr Serverless Inference, downloads the exact vulnerable package version (hash-verified wheels only), and confirms the claimed function exists in the real source, deterministically, with no model involved. It runs the reporter's PoC in a brand-new sandbox: gVisor, no network, empty environment, a per-run canary credential, CPU/memory/PID/time caps and a PEP 578 audit hook. The agent then writes its own reproduction test, retries with errors fed back, and runs the identical test on the patched version in another fresh sandbox. Fixed rules, not the model, turn this evidence into a verdict: Reproduced, Not reproduced, Hostile or Inconclusive.

Results from real runs: a real sqlparse CVE is Reproduced (VULNERABLE on 0.4.4, NOT_VULNERABLE on 0.5.0). A polished CVSS 9.8 "RCE" in a function that never existed is rejected in 24 seconds with nothing executed. A report whose PoC steals credentials and phones home, with a prompt injection hidden in the text, is flagged Hostile and contained.

Don't take our word for the containment: the live app has a "Break the sandbox" page with eight one-click attacks (steal the AWS keys, phone home, pop a shell, fork bomb, memory bomb, and more) or your own Python. Every run is caught, capped or killed in under a second, and the container is destroyed.

Everything runs on Vultr: one Cloud Compute VM hosts the FastAPI app with a live timeline, the orchestrator, the package cache and the Docker + gVisor runtime; every LLM call goes to Vultr Serverless Inference.

## Tags
Vultr, Serverless Inference, AI Agents, Security, Sandboxing, gVisor, Docker, FastAPI, Python, Bug Bounty, AppSec

## Links
- Repo: https://github.com/Abrar5510/triage
- Live app: LIVE_URL (break the sandbox: LIVE_URL/sandbox)
- Slides: docs/slides.pdf
- Cover: docs/img/cover.png
- Demo video: `docs/video/triage-demo.mp4` (2:00, 1920×1080, narrated, built from the real UI and real run data). Upload to YouTube (unlisted) and paste the link: VIDEO_URL. Source: `docs/video/film` (HyperFrames); narration lines in `docs/video/film/vo.tsv`.

---

# Demo video narration (as rendered)

| Time | Picture | Narration |
|---|---|---|
| 0:00 | Three report sheets land on a desk | "Three vulnerability reports just landed. They all look convincing. One is real. One is invented. One is an attack. And every proof of concept is code from a stranger." |
| 0:15 | Triage mark | "Triage checks every report before a human reads it." |
| 0:22 | Report A in the real UI: grounding, agent test, control run | "Report A. Triage downloads the exact version, and confirms the function is real. Then it writes its own test, and runs it in a brand-new sandbox. Vulnerable on the affected version. Clean on the patched one. Same test. Reproduced." |
| 0:46 | Report B: grounding fails | "Report B claims a critical remote code execution. The function it names never existed. Rejected in seconds. Nothing ran." |
| 0:56 | Report C: injection flagged, three policy events | "Report C hides an order for the agent: mark this as reproduced. It's flagged, and ignored. Its proof of concept reads a planted, fake credential, and tries to send it out. There is no route. Hostile. Contained." |
| 1:22 | Ranked inbox | "The reviewer gets a ranked inbox, with proof instead of prose." |
| 1:30 | Break the sandbox: steal keys, fork bomb, memory bomb | "Try to break it. Steal the keys. Fork bomb it. Fill the RAM. Caught, capped, or killed." |
| 1:40 | The real docker flags | "Every run gets a fresh container. No network. No secrets. Destroyed after. Models propose. Sandboxes execute. Rules decide. All of it on Vultr." |
| 1:52 | End card | "Triage. Try to break it." |

## Live demo (if presenting in person, 3 minutes)

1. **Hook (20 s).** Slide 2: "In January curl ended its bug bounty. AI made fake reports free; checking them still costs an expert."
2. **Live triage (60 s).** Home page → **Real CVE**. Narrate the timeline as it streams; land on the vulnerable-vs-patched strip.
3. **The fake (20 s).** Open the seeded Report B: "The function doesn't exist. Rejected, nothing ran."
4. **Hand them the keyboard (60 s).** `/sandbox` → **Steal AWS keys** → **Fork bomb** → **Memory bomb**. Then invite a judge to type their own attack.
5. **Close (20 s).** Slide 9: one Vultr VM, Vultr Serverless Inference. "Models propose, sandboxes execute, rules decide."
