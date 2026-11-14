#!/usr/bin/env python3
"""Assemble the SkillGraph animated demo (v2):
frames -> silent video; per-scene VO placed at timing.json offsets ->
narration track; quiet synthesized pad bed underneath; final mux.
Outputs: video-silent.mp4, narration-v2.mp3 (== the video's VO track),
demo-v2.mp4 in this dir.
"""
import json, os, subprocess, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
timing = json.load(open(os.path.join(HERE, "timing.json")))
TOTAL = timing.pop("_total")
SR = 44100

def run(cmd):
    print("+", " ".join(cmd[:3]), "...", flush=True)
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout[-2000:]); print(r.stderr[-3000:]); sys.exit(1)

# ---------- 1. silent video from frames ----------
silent = os.path.join(HERE, "video-silent.mp4")
run(["ffmpeg","-y","-framerate","30","-i",os.path.join(HERE,"frames","f%05d.jpg"),
     "-c:v","libx264","-pix_fmt","yuv420p","-crf","17","-preset","medium", silent])

# ---------- 2. music bed (synthesized pads, Am - F - C - G) ----------
bed_wav = os.path.join(HERE, "bed.wav")
if not os.path.exists(bed_wav):
    n = int(TOTAL * SR); t = np.arange(n) / SR
    chords = [  # (start_frac, [freqs])
        (0.00, [110.00, 164.81, 261.63]),   # Am
        (0.27, [ 87.31, 130.81, 220.00]),   # F
        (0.52, [130.81, 196.00, 329.63]),   # C
        (0.77, [ 98.00, 146.83, 246.94]),   # G
    ]
    y = np.zeros(n)
    bounds = [c[0] for c in chords] + [1.0]
    for i, (frac, freqs) in enumerate(chords):
        a, b = int(bounds[i]*n), int(bounds[i+1]*n)
        seg = np.zeros(b-a); tt = t[a:b]
        for f in freqs:
            seg += np.sin(2*np.pi*f*tt) + 0.35*np.sin(2*np.pi*2*f*tt) + 0.12*np.sin(2*np.pi*3*f*tt)
        seg /= len(freqs)
        env = np.ones(b-a)
        xf = int(3.0*SR)
        env[:xf] *= np.linspace(0,1,xf); env[-xf:] *= np.linspace(1,0,xf)
        y[a:b] += seg * env
    y *= 1 + 0.12*np.sin(2*np.pi*0.07*t)          # slow breathing
    fade_in = int(2.0*SR); fade_out = int(4.0*SR)
    y[:fade_in] *= np.linspace(0,1,fade_in); y[-fade_out:] *= np.linspace(1,0,fade_out)
    y = y / (np.max(np.abs(y)) + 1e-9) * 0.5
    import wave, struct
    with wave.open(bed_wav, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(struct.pack("<%dh" % n, *np.clip(y*32767, -32767, 32767).astype(np.int16)))
    print("bed.wav written")

# ---------- 3. narration track: VO clips at scene offsets ----------
order = ["s1","s2","s3","s4","s5","s6","s7","s8","s9"]
inputs, filters, labels = [], [], []
for i, k in enumerate(order):
    inputs += ["-i", os.path.join(HERE, "vo", k + ".mp3")]
    ms = int(timing[k]["vo_start"] * 1000)
    filters.append(f"[{i}:a]aresample=44100,adelay={ms}:all=1[a{i}]")
    labels.append(f"[a{i}]")
fc = ";".join(filters) + ";" + "".join(labels) + \
     f"amix=inputs={len(order)}:duration=longest:normalize=0,apad,atrim=0:{TOTAL}[na]"
narr_wav = os.path.join(HERE, "narration.wav")
run(["ffmpeg","-y"] + inputs + ["-filter_complex", fc, "-map", "[na]",
     "-c:a", "pcm_s16le", narr_wav])
# narration MP3 (the file that ships in docs/, in sync with the final cut)
run(["ffmpeg","-y","-i",narr_wav,"-c:a","libmp3lame","-q:a","2",
     os.path.join(HERE,"narration-v2.mp3")])

# ---------- 4. final mux: video + (narration over quiet bed) ----------
final = os.path.join(HERE, "demo-v2.mp4")
fc2 = (f"[1:a]volume=1.0[vo];[2:a]volume=0.11[bed];"
       f"[vo][bed]amix=inputs=2:duration=first:normalize=0[aout]")
run(["ffmpeg","-y","-i",silent,"-i",narr_wav,"-i",bed_wav,
     "-filter_complex", fc2, "-map","0:v","-map","[aout]",
     "-c:v","copy","-c:a","aac","-b:a","160k","-t",str(TOTAL),
     "-movflags","+faststart", final])
print("DONE", final)
