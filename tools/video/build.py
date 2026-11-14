#!/usr/bin/env python3
"""Build deck.html for the SkillGraph animated demo (v2).

Evidence policy: every terminal line shown in the deck is extracted
PROGRAMMATICALLY from the committed evidence files in the repo
(demo-output.txt, docs/mcp-exchange.log, docs/agent-consumer-transcript.md).
Nothing is re-typed. Excerpts are line selections of the real files.
"""
import json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
# In-repo layout: tools/video/ -> repo root is two levels up (evidence files
# live at the repo root / docs/). Fallback: the standalone build workspace.
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
if not os.path.exists(os.path.join(REPO, "demo-output.txt")):
    REPO = os.path.expanduser("~/workspace/skillgraph-repo")

def read(p):
    with open(p, encoding="utf-8") as f: return f.read()

demo = read(os.path.join(REPO, "demo-output.txt")).splitlines()
mcplog = read(os.path.join(REPO, "docs", "mcp-exchange.log")).splitlines()
transcript = read(os.path.join(REPO, "docs", "agent-consumer-transcript.md"))

# --- Demo A: header + skills/tools lines + verdict JSON fields (verbatim lines)
demoA = []
for ln in demo:
    if ln.startswith("DEMO A") or ln.startswith("skills:") or ln.startswith("tools :") \
       or ln.startswith("CURRENT verdict") or re.match(r'\s"(vid|label|detail|ts|provenance)"', ln):
        demoA.append(ln)
    if len(demoA) >= 9: break
assert len(demoA) == 9, demoA

# --- Demo B: the three Ink Koi verdict lines (provenance lines live in Demo A's insert)
demoB = [ln for ln in demo if ln.startswith("Ink Koi @")]
assert len(demoB) == 3, demoB

# --- Demo C: full-preload line + the five bundle lines
demoC = [ln for ln in demo if ln.startswith("full catalog preload:") or
         re.match(r"^(verify_free_mint|hunt_bounty|play_agent_cards|build_demo_site|backtest_strategy)\s+bundle", ln)]
assert len(demoC) == 6, demoC

# --- Demos D + E: two STALE lines + the load line
demoDE = [ln for ln in demo if ln.startswith("16 stale verdict(s)")]
demoDE += [ln for ln in demo if "STALE: verdict from" in ln][:1]
demoDE += [ln for ln in demo if ln.startswith("200 queries in")]
assert len(demoDE) == 3, demoDE

# --- MCP log: initialize req, tools/list req, traversal req/resp, supersede resp
def pick(pred, what):
    for ln in mcplog:
        if pred(ln): return ln
    raise SystemExit("MCP line not found: " + what)
mcp = [
    pick(lambda l: '"id": 1, "method": "initialize"' in l, "initialize req"),
    pick(lambda l: '"id": 2, "method": "tools/list"' in l, "tools/list req"),
    pick(lambda l: '"id": 25, "method": "tools/call"' in l, "traversal req"),
    pick(lambda l: '"id":25,"result"' in l, "traversal resp"),
    pick(lambda l: '"id":27,"result"' in l, "supersede resp"),
]
# safety: no credential-shaped strings in what we show
for ln in mcp + demoA + demoB + demoC + demoDE:
    assert "Bearer" not in ln and "auth-token" not in ln and "Authorization" not in ln, ln[:80]

# --- Run A first paragraph (verbatim from the transcript)
m = re.search(r"## Run A[^\n]*\n\n(.+?)\n\n", transcript, re.S)
runA = " ".join(m.group(1).split())
assert runA.startswith("I do not have access to real-time blockchain data"), runA[:60]

timing = json.load(open(os.path.join(HERE, "timing.json")))
timing.pop("_total", None)

ev = {"demoA": demoA, "demoB": demoB, "demoC": demoC, "demoDE": demoDE,
      "mcp": mcp, "runA": runA}

tpl = read(os.path.join(HERE, "deck_template.html"))
html = tpl.replace("__TIMING_JSON__", json.dumps(timing)) \
          .replace("__EVIDENCE_JSON__", json.dumps(ev))
assert "__TIMING_JSON__" not in html and "__EVIDENCE_JSON__" not in html
with open(os.path.join(HERE, "deck.html"), "w", encoding="utf-8") as f:
    f.write(html)
print("deck.html written:", len(html), "bytes; evidence lines:",
      {k: (len(v) if isinstance(v, list) else 1) for k, v in ev.items()})
