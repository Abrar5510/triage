"""Render the cover (PNG), deck (PDF) and slide PNGs with headless Chrome. Stdlib only.

    LIVE_URL=https://triage.example.com python docs/deck/render.py

Without LIVE_URL, lines that mention it are left out. CHROME overrides the browser path.
Slide PNGs need pdftoppm (poppler); they are skipped without it.
"""
import glob
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

D = Path(__file__).resolve().parent
CHROME = os.getenv("CHROME") or next(iter(
    glob.glob(os.path.expanduser("~/Library/Caches/ms-playwright/chromium-*/chrome-mac*/*.app/Contents/MacOS/*"))
    + [shutil.which(n) for n in ("google-chrome", "chromium", "chromium-browser") if shutil.which(n)]
    + ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"]))
url = os.getenv("LIVE_URL", "").rstrip("/")


def page(name):
    html = (D / name).read_text()
    html = html.replace("LIVE_URL", url) if url else "\n".join(l for l in html.splitlines() if "LIVE_URL" not in l)
    tmp = D / f".render-{name}"
    tmp.write_text(html)
    return tmp


def chrome(*args):
    with tempfile.TemporaryDirectory() as prof:
        subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", f"--user-data-dir={prof}",
                        "--virtual-time-budget=5000", *args], check=True, capture_output=True)


cover, slides = page("cover.html"), page("slides.html")
try:
    chrome("--window-size=1920,1080", f"--screenshot={D.parent / 'img' / 'cover.png'}", cover.as_uri())
    chrome("--no-pdf-header-footer", f"--print-to-pdf={D.parent / 'slides.pdf'}", slides.as_uri())
finally:
    cover.unlink(); slides.unlink()
if shutil.which("pdftoppm"):
    for old in D.glob("slide-*.png"):
        old.unlink()
    subprocess.run(["pdftoppm", "-png", "-r", "72", D.parent / "slides.pdf", D / "slide"], check=True)
print("ok")
