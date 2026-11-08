# Review

## Creative calls
- Built storyline 1, "Three reports walk in" (see STORYLINES.md). Not built: "Follow the canary" (result first, one take) and "Proof, not prose" (kinetic type on the beat).
- Every product screen is Triage's real markup and stylesheet (assets/app.css is a copy of triage/static/style.css), filled with the real data of runs #1–#3 from the local instance. Rows are a selection of the real timeline events, in order.
- The left column carries the story in large type, while the panel on the right shows the evidence. UI is rendered at 1.6x zoom.
- Honesty: the recorded runs used hardened Docker (runc) on a Mac, and the run card says `runc`. gVisor only appears as the deploy flag `--runtime runsc  # gVisor on the Vultr VM`. The Vultr lines describe the deployment target.
- Length 110 s, 1920x1080, 30 fps.

## Measured vs looked at
- `hyperframes check`: no errors. Inspected review sheets for all 8 scenes and all 7 seams, plus spot frames at 1.2, 5.6, 7.9, 11.8, 13.2, 13.95, 23.6, 41.8, 51.5, 59.5, 73.6, 79.5, 87, 93.2, 99.5 and 109.75 s.
- Sound: bundled HyperFrames SFX only (whoosh, pop, click, key, error, glitch, riser into one impact on the Hostile verdict). There is no music bed, because no music source exists on this machine (no HeyGen sign-in, no MusicGen). The sound was measured, not heard.

## Warnings kept on purpose
- `text_below_floor`: product UI text is about 21–24 px at 1.6x zoom, under the 28 px phone floor. The large left-column lines carry the story, and the UI is evidence. Judges watch on desktop.
- `contrast_aa_failure`: Triage's own dim/muted greys (#5e6679, #8b93a7). These are the product's palette, left as is.
- `line_unread` on long report text and the demo-button descriptions: these are context, and the highlighted part is what is read.
- `negative_z_index` on the desk highlight bars: they render correctly behind single-line text.

## Weakest shot, and what I'd change with more time
- The mark scene (15–22 s) is a plain lockup and headline on the dark ground. It could enter through the flooded code block instead of a fresh dark frame.
- The Vultr architecture line is text only. With a live Vultr deploy, a real `/healthz` showing `runsc` would prove it.
- Adding a music bed: drop a track into assets/ and add an `<audio id="bgm">` at about 0.15 volume in index.html.
