#!/usr/bin/env python3
"""Generate per-scene VO clips with Helio TTS and build the scene timeline.

Timeline model (NEAR v4 style): each scene window = HEAD + vo + TAIL.
Scene i starts where scene i-1 ends; crossfades are handled in the deck.
"""
import json, subprocess, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vo_texts import VO, ORDER

HERE = os.path.dirname(os.path.abspath(__file__))
VO_DIR = os.path.join(HERE, "vo")
os.makedirs(VO_DIR, exist_ok=True)
HEAD, TAIL = 0.30, 0.55

def dur(path):
    out = subprocess.run(["ffprobe","-v","error","-show_entries","format=duration",
                          "-of","csv=p=0",path], capture_output=True, text=True)
    return float(out.stdout.strip())

timing = {}
t = 0.0
for key in ORDER:
    mp3 = os.path.join(VO_DIR, key + ".mp3")
    if not (os.path.exists(mp3) and os.path.getsize(mp3) > 1000):
        print("TTS", key, flush=True)
        r = subprocess.run(["/opt/hatch/bin/tts","speak","--text",VO[key],
                            "--voice","avocado_v2:MAI_03","--output",mp3],
                           capture_output=True, text=True, timeout=300)
        if r.returncode != 0:
            print("TTS FAIL", key, r.stdout, r.stderr); sys.exit(1)
    d = dur(mp3)
    timing[key] = {"start": round(t,3), "vo_start": round(t+HEAD,3), "vo_dur": round(d,3),
                   "end": round(t+HEAD+d+TAIL,3)}
    t += HEAD + d + TAIL
    print(key, "vo", round(d,2), "window", round(HEAD+d+TAIL,2), "start", timing[key]["start"], flush=True)

timing["_total"] = round(t,3)
with open(os.path.join(HERE,"timing.json"),"w") as f:
    json.dump(timing,f,indent=1)
print("TOTAL", t)
