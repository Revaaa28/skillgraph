"""SkillGraph agent-consumer proof.

The sharpest objection to SkillGraph is: "there is no agent — a script
prints a bundle and nothing consumes it." This script closes that gap with
the smallest real consumer: an actual LLM, asked the same task question
twice — once bare, once with the SkillGraph bundle injected as its only
context — with both answers recorded verbatim in
docs/agent-consumer-transcript.md.

How it works:
  1. A small snippet runs on the box (boxd exec) and reuses demo.py's own
     assemble_bundle("verify_free_mint") against the live HydraDB graph,
     scoped to the one entity the question names (Ink Koi). demo.py itself
     is not modified. The bundle JSON travels back over stdout markers.
  2. The question is sent to the LLM twice via the Gemini connector helper
     (Run A: question only; Run B: question + bundle). Answers are recorded
     verbatim — one run, no re-rolls (a single retry only on a hard API
     error, i.e. no answer at all).

Token safety: the HydraDB token never leaves the box. The snippet reads it
there via sg.py's normal runtime path; nothing in this script, its output,
or the transcript contains it. The Gemini key likewise stays inside the
connector helper.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

BOX = "true-hare"
MODEL = "gemini-3.5-flash-lite"
GEMINI_HELPER = Path.home() / "workspace/custom-connectors/custom.gemini/bin/gemini.py"
QUESTION = ("Can I still mint Ink Koi for free right now? How many free "
            "slots are left, and if I proceed, what exactly should I check "
            "before signing anything?")
ENTITY_HINT = "Ink Koi"
TASK = "verify_free_mint"

# The 3-line reading of the recorded answers (provenance/freshness, not
# model IQ). Written after inspecting the single recorded run below and
# kept identical in agent_consumer.py and docs/agent-consumer-transcript.md.
READING = [
    "Same model, same question, one run each — the only difference is the bundle.",
    "Run A has no source for today's mint state, so it cannot state the free-slot count; Run B's answer traces to a verdict timestamped 2026-11-14T04:26:46.175Z from an on-chain autocheck.",
    "The bundle buys provenance and freshness, not IQ: a sourced, current fact the agent can cite, plus the verification skills' checks to apply before signing.",
]

# Box-side snippet: reuses demo.py's bundle assembly, scoped to the entity.
SNIPPET = '''
import sys, json
sys.path.insert(0, "/home/boxd/skillgraph")
from datetime import datetime, timezone
import demo

now = datetime.now(timezone.utc)
full, _stale = demo.assemble_bundle("verify_free_mint", stale_hours=24.0, now=now)
focused = dict(full)
focused["entities"] = [e for e in full["entities"]
                       if e["name"].startswith("Ink Koi")]
sys.stdout.write("BUNDLE_JSON_BEGIN\\n")
sys.stdout.write(json.dumps({"focused": focused, "full": full}))
sys.stdout.write("\\nBUNDLE_JSON_END\\n")
'''


def boxd_bin():
    p = shutil.which("boxd")
    if p:
        return p
    cand = Path.home() / ".local" / "bin" / "boxd"
    if cand.exists():
        return str(cand)
    raise SystemExit("boxd CLI not found")


def bsize(obj):
    """demo.py's byte-size convention: compact, key-sorted JSON."""
    return len(json.dumps(obj, separators=(",", ":"), sort_keys=True).encode())


def fetch_bundles():
    """Run the snippet on the box; return (focused_bundle, full_bundle)."""
    boxd = boxd_bin()
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
        f.write(SNIPPET)
        local_snippet = f.name
    try:
        subprocess.run([boxd, "machine", "cp", local_snippet,
                        f"{BOX}:/tmp/sg_consumer_snippet.py"],
                       check=True, capture_output=True, text=True, timeout=180)
        out = subprocess.run([boxd, "machine", "exec", BOX,
                              "python3 /tmp/sg_consumer_snippet.py"],
                             check=True, capture_output=True, text=True,
                             timeout=300)
    finally:
        os.unlink(local_snippet)
    m = re.search(r"BUNDLE_JSON_BEGIN\n(.*)\nBUNDLE_JSON_END", out.stdout, re.S)
    if not m:
        raise SystemExit("bundle markers not found in box output:\n"
                         + out.stdout[-2000:])
    data = json.loads(m.group(1))
    return data["focused"], data["full"]


def ask_gemini(prompt):
    """One generation via the connector helper; one retry on hard error."""
    last_err = None
    for _attempt in range(2):
        try:
            r = subprocess.run(
                ["python3", str(GEMINI_HELPER), "generate", MODEL, prompt],
                capture_output=True, text=True, timeout=300)
            if r.returncode != 0:
                raise RuntimeError(f"exit {r.returncode}: {r.stderr.strip()}")
            return json.loads(r.stdout)["text"]
        except Exception as e:  # hard API/transport error -> single retry
            last_err = e
    raise SystemExit(f"gemini call failed after one retry: {last_err}")


def main():
    focused, full = fetch_bundles()
    focused_bytes = bsize(focused)
    full_bytes = bsize(full)
    bundle_json = json.dumps(focused, separators=(",", ":"), sort_keys=True)

    prompt_a = QUESTION
    prompt_b = ("The following context bundle was assembled for this task by "
                "SkillGraph from a live knowledge graph (skills to apply, "
                "tools available, and entities with their latest verified "
                "verdicts):\n\n" + bundle_json + "\n\nQuestion: " + QUESTION)

    answer_a = ask_gemini(prompt_a)
    answer_b = ask_gemini(prompt_b)

    ran_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    ent = focused["entities"][0] if focused["entities"] else {}
    verdict = ent.get("verdict") or {}

    lines = []
    lines.append("# Agent-consumer proof: an LLM answers with vs without a SkillGraph bundle")
    lines.append("")
    lines.append("**The objection this closes:** \"there is no agent — a script "
                 "prints a bundle and nothing consumes it.\" Here the bundle is "
                 "consumed by a real LLM, asked the same question twice: once "
                 "bare, once with the bundle as its only context. Both answers "
                 "below are verbatim from a single run of `agent_consumer.py` "
                 "(no re-rolls; the script retries only on a hard API error).")
    lines.append("")
    lines.append(f"- Run (UTC): {ran_at}")
    lines.append(f"- Model: {MODEL} (via the Gemini API connector helper)")
    lines.append(f"- Task type: {TASK} · Entity in question: {ent.get('name', ENTITY_HINT)}")
    lines.append(f"- Bundle fed to Run B: **{focused_bytes} bytes** (compact JSON) — "
                 f"demo.py's `assemble_bundle(\"{TASK}\")` output scoped to the "
                 f"entity the question names: the task's skills + tools, plus "
                 f"{ent.get('name', ENTITY_HINT)} with its current verdict "
                 f"(label `{verdict.get('label')}`, ts {verdict.get('ts')}, "
                 f"provenance: {verdict.get('provenance')}).")
    lines.append(f"- For scale: the unscoped {TASK} bundle (all entities) is "
                 f"{full_bytes} bytes; preloading the entire graph catalog is "
                 f"11,113 bytes (see METRICS.md).")
    lines.append("")
    lines.append("## The question")
    lines.append("")
    lines.append("> " + QUESTION)
    lines.append("")
    lines.append("## Run A — no bundle (the question alone)")
    lines.append("")
    lines.append(answer_a)
    lines.append("")
    lines.append("## Run B — with the SkillGraph bundle as context")
    lines.append("")
    lines.append("Prompt = a one-line framing, the bundle JSON "
                 f"({focused_bytes} bytes), then the same question.")
    lines.append("")
    lines.append(answer_b)
    lines.append("")
    lines.append("## Reading")
    lines.append("")
    for line in READING:
        lines.append(line)
    lines.append("")

    out_path = Path(__file__).parent / "docs" / "agent-consumer-transcript.md"
    out_path.write_text("\n".join(lines))
    print(f"focused bundle: {focused_bytes} bytes | full {TASK} bundle: {full_bytes} bytes")
    print(f"transcript written to {out_path}")
    print("\n--- RUN A ---\n" + answer_a)
    print("\n--- RUN B ---\n" + answer_b)


if __name__ == "__main__":
    main()
