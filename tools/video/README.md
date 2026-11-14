# Demo video build (animated, v2)

The shipped `docs/demo.mp4` is built with the "rendered HTML deck"
recipe: a deterministic 1920x1080 HTML deck whose animation state is a
pure function of time (`window.__render(t)`), rendered frame-by-frame
with Playwright + Chromium headless shell, then assembled with ffmpeg.
All on-screen evidence (terminal inserts, MCP log lines, the
agent-consumer quote) is extracted programmatically from the committed
files by `build.py` — nothing is re-typed.

Pipeline (from this directory):

```
python3 gen_vo.py        # TTS per scene -> vo/*.mp3 + timing.json
                         # (voice: Helio avocado_v2:MAI_03 via /opt/hatch/bin/tts;
                         #  scene texts in vo_texts.py, verbatim from docs/demo-script.md)
python3 build.py         # deck_template.html + evidence -> deck.html
node render.mjs frames 0 4367   # 30 fps frames for the full runtime
                         # (needs: npm i playwright-core, a Chromium
                         #  headless-shell build; set CHROME in render.mjs)
python3 assemble.py      # frames -> video; narration placed per timing.json;
                         # synthesized pad bed; -> demo-v2.mp4 + narration-v2.mp3
node check.mjs deck.html 45 82 127   # single-frame spot checks (PNGs)
```

Then copy `demo-v2.mp4` to `docs/demo.mp4` and `narration-v2.mp3` to
`docs/demo-narration.mp3`.
