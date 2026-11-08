# SPEC: Triage demo film

GOAL:    a judge understands in 2 minutes that Triage reproduces real reports, rejects fabricated ones and contains hostile PoCs, using real runs.
OUTPUT:  HyperFrames, 1920 x 1080, 30 fps
TIME:    126 s x 30 = 3780 frames. No music (no source on this machine); SFX on visible actions.
LOOK:    product world = Triage's own UI: ground #0b0d10, panel #141821, line #222836, ink #e7eaf0, muted #8b93a7,
         ok #3ddc97, danger #ff5c6c, warn #ffb547, info #7aa7ff. Inter Tight 400-700 (variable woff2), JetBrains Mono.
         UI rendered at zoom 1.75 (15 px body -> 26 px). Desk world = #e9ecf1 ground, white sheets, shadow 0 30px 60px rgba(11,13,16,.18).
         End card = flood to #3ddc97 with #04130c ink. Accent rationed: one word per line.
OBJECTS: report sheets (white paper, real markdown text in mono, title bold); the Triage panel (real markup and class names
         from triage/templates/_panel.html); the docker command (real flags from triage/sandbox.py); the shield mark (from docs/deck/cover.html).
MOTION:  enter expo.out 0.5-0.7 s; camera power2.inOut 0.6-0.8 s; exits power3.in 0.25-0.35 s; titles per-word blur 6px->0, 0.07 s stagger.
         Lines hold 0.5 s + 0.3 s/word. UI rows arrive with 0.25 s expo.out, 12 px rise max.
SHOTS:
  s1 desk     0-15    sheets whip in, highlights, "One is real / invented / an attack" roll, push into C's PoC, code block floods the frame
  s2 mark     15-22   shield stroke draws, wordmark wipes, product line (verbatim hero copy)
  s3 report A 22-50   cursor clicks "Real CVE" on the real try panel, zoom through, stepper + timeline stream, diff strip carried to centre, verdict
  s4 report B 50-64   ground fails, steps strike through, grounding card isolated, "24 s. Nothing ran."
  s5 report C 64-96   injection quote flagged, run card with 3 policy events, Network unreachable, Hostile verdict (payoff, riser+impact)
  s6 inbox    96-106  ranked inbox rows + stats from the real home page
  s7 sandbox  106-118 docker run flags typed in a terminal, "Models propose. Sandboxes execute. Rules decide.", Vultr line
  s8 end      118-126 green flood, mark, Triage, repo URL, hackathon line
BANNED:  dark void with floating small things (UI is shown at 1.75x and fills >= 55% of frame); glow and particles beyond the product's own run-danger shadow;
         three cards in a row; title over dimmed screenshot; logo docked in a corner; every element fade+slide-up; titles drifting after landing;
         invented UI (every panel uses real class names, labels and values); claims not in the source (runs used hardened Docker locally: never say gVisor ran them).
QA:      t=1, 9, 14.5, 17, 21, 30, 44, 48, 57, 62, 70, 82, 92, 100, 112, 124.
