// Record the demo video and README screenshots by driving a running Triage instance.
//
//   node docs/video/record.mjs [http://localhost:8000]
//
// Runs the three demo reports live (real sandbox, real model), overlays captions, and writes
// docs/video/triage-demo.webm (and .mp4 if ffmpeg works) plus docs/img/*.png. Needs Node Playwright.
// NO_WEBFONTS=1 records without Google Fonts. PLAYWRIGHT_MODULE / CHROME_PATH override where Playwright and the browser come from.
import { execFileSync } from "node:child_process";
import { copyFileSync, mkdirSync, rmSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const require = createRequire(import.meta.url);
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || "playwright");
const BASE = process.argv[2] || "http://localhost:8000";
const HERE = dirname(fileURLToPath(import.meta.url));
const DOCS = join(HERE, "..");
const W = 1600, H = 900;
const sleep = s => new Promise(r => setTimeout(r, s * 1000));

const CAPTION_JS = `
window.__cap = (text, tone) => {
  let el = document.getElementById('__cap');
  if (!el) {
    el = document.createElement('div'); el.id = '__cap';
    el.style.cssText = 'position:fixed;left:50%;bottom:36px;transform:translateX(-50%);z-index:99999;max-width:1180px;' +
      'padding:16px 26px;border-radius:14px;background:rgba(7,9,12,.93);border:1px solid #2c3446;color:#e7eaf0;' +
      'font:500 24px/1.4 "Inter Tight",system-ui,sans-serif;letter-spacing:-.01em;text-align:center;' +
      'box-shadow:0 20px 60px rgba(0,0,0,.6);transition:opacity .35s ease;opacity:0;pointer-events:none';
    document.body.appendChild(el);
  }
  el.style.borderColor = tone === 'danger' ? 'rgba(255,92,108,.75)' : tone === 'ok' ? 'rgba(61,220,151,.65)' : '#2c3446';
  el.style.opacity = 0;
  setTimeout(() => { el.textContent = text; el.style.opacity = text ? 1 : 0; }, text ? 200 : 0);
};`;

const rawDir = join(HERE, "raw");
rmSync(rawDir, { recursive: true, force: true });
mkdirSync(join(DOCS, "img"), { recursive: true });

const browser = await chromium.launch(process.env.CHROME_PATH ? { executablePath: process.env.CHROME_PATH } : {});
const ctx = await browser.newContext({
  viewport: { width: W, height: H }, deviceScaleFactor: 1,
  recordVideo: { dir: rawDir, size: { width: W, height: H } },
});
await ctx.addInitScript(CAPTION_JS);
// Offline recording: skip web fonts so pages don't wait on an unreachable stylesheet (system fonts are used).
if (process.env.NO_WEBFONTS) await ctx.route(/fonts\.(googleapis|gstatic)\.com/, r => r.abort());
const page = await ctx.newPage();

const cap = async (text, tone = "", hold = 0) => { await page.evaluate(([t, s]) => window.__cap(t, s), [text, tone]); await sleep(hold); };
const scrollTo = async (sel, hold = 0, offset = 90) => {
  await page.evaluate(([s, off]) => { const el = document.querySelector(s);
    if (el) window.scrollTo({ top: el.getBoundingClientRect().top + scrollY - off, behavior: "smooth" }); }, [sel, offset]);
  await sleep(1.2 + hold);
};
const top = async hold => { await page.evaluate(() => window.scrollTo({ top: 0, behavior: "smooth" })); await sleep(hold); };
const slide = async (n, text = "", hold = 4) => {
  await page.goto(pathToFileURL(join(DOCS, "deck", `slide-${String(n).padStart(2, "0")}.png`)).href);
  await page.evaluate(() => { document.body.style.cssText = "margin:0;background:#0b0d10;display:grid;place-items:center;height:100vh";
    document.querySelector("img").style.cssText = "width:100vw;height:auto"; });
  if (text) await cap(text);
  await sleep(hold);
};
const runDemo = async key => {
  await page.goto(BASE + "/"); await sleep(1);
  await page.locator(`form[action='/run/${key}'] button`).click();
  await page.waitForURL("**/reports/*");
};
const waitDone = async () => { await page.waitForSelector("#panel .verdict:not(.v-running)", { timeout: 240_000 }); await sleep(1); };
const shot = async name => { await cap(""); await sleep(0.5); await page.screenshot({ path: join(DOCS, "img", name), fullPage: true }); };

// 1. Problem
await slide(1, "", 4);
await slide(2, "Every report needs an expert to read it, and the attached PoC is untrusted code.", 7);
await slide(3, "Triage: models propose, sandboxes execute, fixed rules decide.", 7);

// 2. Home
await page.goto(BASE + "/");
await cap("Three reports arrive. Each one runs live, in brand-new sandboxes.", "", 5);

// 3. Report A: real
await runDemo("real");
await cap("Report A: a real, already-fixed DoS in sqlparse (CVE-2024-4340)", "", 4);
await cap("The agent extracts claims, finds the function in real source, runs the PoC, then writes its own test");
await waitDone();
await cap("Same test, two fresh sandboxes: VULNERABLE on 0.4.4, NOT_VULNERABLE on patched 0.5.0", "ok");
await scrollTo(".diff", 4, 420);
await shot("reproduced.png");
await cap("Every run records exit code, memory, runtime and output. Each container is destroyed afterwards.");
await scrollTo(".runs", 5);
await cap("Verdict: Reproduced, with proof that the patch removes it.", "ok");
await top(4);

// 4. Report B: fabricated
await runDemo("fabricated");
await cap("Report B: a polished CVSS 9.8 'remote code execution' report");
await waitDone();
await cap("Grounding searches the real sqlparse 0.4.4 source: eval_expression() never existed.");
await scrollTo(".grid", 5);
await top(0);
await cap("Rejected in seconds. Not a single line of submitted code ran.", "", 4);
await shot("rejected.png");

// 5. Report C: hostile
await runDemo("hostile");
await cap("Report C: a plausible formatting bug. The text hides a prompt injection.", "danger", 3);
await cap("Intake flags it. The model never controls sandbox settings, so it changes nothing.", "danger");
await waitDone();
await cap("The PoC read a planted fake credential and tried to send it out. No route: blocked.", "danger");
await scrollTo(".run-danger", 6);
await shot("hostile.png");
await cap("Three policy events. Container destroyed. Verdict: Hostile, contained.", "danger");
await top(4);

// 6. Inbox
await page.goto(BASE + "/");
await sleep(0.5);
await page.screenshot({ path: join(DOCS, "img", "home.png") });
await scrollTo(".inbox", 0, 300);
await cap("The inbox is ranked for the reviewer: reproduced first, hostile quarantined, fakes rejected.", "ok", 6);

// 7. Close
await slide(7, "Blast radius zero: every execution gets a new gVisor sandbox, destroyed afterwards.", 6);
await slide(8, "One Vultr VM is the control layer. Every LLM call goes to Vultr Serverless Inference.", 6);
await slide(10, "", 5);

const raw = await page.video().path();
await ctx.close();
await browser.close();
const webm = join(HERE, "triage-demo.webm");
copyFileSync(raw, webm);
rmSync(rawDir, { recursive: true, force: true });
console.log("wrote", webm);
try {
  const mp4 = join(HERE, "triage-demo.mp4");
  execFileSync("ffmpeg", ["-y", "-loglevel", "error", "-i", webm, "-c:v", "libx264", "-preset", "slow", "-crf", "22",
    "-pix_fmt", "yuv420p", "-movflags", "+faststart", mp4], { stdio: "pipe" });
  console.log("wrote", mp4);
} catch (e) {
  console.log("mp4 skipped (ffmpeg unavailable):", String(e.stderr || e.message).split("\n")[0]);
}
