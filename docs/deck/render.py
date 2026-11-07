"""Render the cover (PNG) and deck (PDF). Usage: uv run --with playwright python docs/deck/render.py"""
from pathlib import Path
from playwright.sync_api import sync_playwright

D = Path(__file__).resolve().parent
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1920, "height": 1080})
    pg.goto((D / "cover.html").as_uri()); pg.wait_for_load_state("networkidle")
    pg.screenshot(path=str(D.parent / "img" / "cover.png"))
    pg.goto((D / "slides.html").as_uri()); pg.wait_for_load_state("networkidle")
    pg.pdf(path=str(D.parent / "slides.pdf"), width="1920px", height="1080px", print_background=True)
    for i, s in enumerate(pg.query_selector_all("section.s"), 1):
        s.screenshot(path=str(D / f"slide-{i:02d}.png"))
    b.close()
print("ok")
