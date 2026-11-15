"""SkillGraph — judge-facing live demo (stdlib only).

Serves a small web UI on port 8000 that talks to the REAL local HydraDB
node (HTTP API on 127.0.0.1:8443) through sg.py / demo.py. Every number
on every page comes from a live query issued while rendering that page;
the only fixed query set is the one below — visitors cannot run
arbitrary Cypher, and the node token never leaves the server.

Run (on the box, next to the node):
    HYDRA_TOKEN_FILE=<node token file> python3 webapp.py
"""
import html, json, os, sys, time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs, quote

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sg import q, rows
import demo

PORT = int(os.environ.get("SG_WEB_PORT", "8000"))
TASKS = demo.TASKS

KINDS = ("Skill", "Tool", "MCPServer", "TaskType", "Entity", "Verdict")
EDGE_TYPES = ("NEEDS_SKILL", "USES_TOOL", "ABOUT", "HAS_VERDICT",
              "SUPERSEDES", "EXPOSED_VIA")
KIND_COLOR = {
    "TaskType": "#a371f7", "Skill": "#58a6ff", "Tool": "#39c5cf",
    "MCPServer": "#f778ba", "Entity": "#3fb950", "Verdict": "#d29922",
}

CSS = """
:root{
 --bg:#0a0e13; --panel:#10161f; --line:#233041; --line2:#31445c;
 --txt:#e8eef5; --mut:#8fa1b3; --mut2:#64788d;
 --blue:#58a6ff; --green:#3fb950; --amber:#d29922; --red:#f85149;
}
*{box-sizing:border-box}
body{font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;margin:0;
 color:var(--txt);line-height:1.55;
 background:
  radial-gradient(900px 480px at 88% -80px,rgba(88,166,255,.13),transparent 60%),
  radial-gradient(720px 460px at -12% 260px,rgba(163,113,247,.10),transparent 60%),
  var(--bg)}
.wrap{max-width:1160px;margin:0 auto;padding:0 20px 84px}
a{color:var(--blue);text-decoration:none}
a:hover{text-decoration:underline}
.topbar{display:flex;align-items:center;gap:10px;padding:18px 0 4px}
.topbar .brand{display:flex;align-items:center;gap:10px;color:var(--txt);
 font-weight:750;font-size:17px;letter-spacing:-.01em}
.topbar .brand:hover{text-decoration:none}
.topbar nav{margin-left:auto;display:flex;gap:18px;font-size:14px}
.topbar nav a{color:var(--mut)}
.topbar nav a:hover{color:var(--txt);text-decoration:none}
.hero{padding:44px 0 6px}
.eyebrow{display:inline-flex;align-items:center;gap:8px;font-size:12px;
 letter-spacing:.14em;font-weight:650;color:var(--mut);text-transform:uppercase;
 border:1px solid var(--line);border-radius:999px;padding:5px 13px;background:rgba(16,22,31,.7)}
.dot-live{width:8px;height:8px;border-radius:50%;background:var(--green);
 box-shadow:0 0 0 4px rgba(63,185,80,.16)}
h1{font-size:46px;line-height:1.06;margin:20px 0 6px;letter-spacing:-.025em;font-weight:820}
.pitch{font-size:21px;color:var(--blue);margin:0 0 14px;font-weight:600;letter-spacing:-.01em}
.lead{color:var(--mut);font-size:16.5px;max-width:760px;margin:0}
.lead b{color:var(--txt)}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));
 gap:14px;margin:30px 0 10px}
.stat{background:linear-gradient(180deg,#121a25,#0f141d);border:1px solid var(--line);
 border-radius:16px;padding:20px 22px}
.stat .num{font-size:36px;font-weight:800;letter-spacing:-.02em;line-height:1.05}
.stat .lbl{font-size:12px;letter-spacing:.13em;color:var(--mut);
 text-transform:uppercase;font-weight:650;margin:5px 0 8px}
.stat .sub{font-size:13px;color:var(--mut);line-height:1.5}
.meta-line{color:var(--mut2);font-size:13px;margin:8px 2px 0}
section{margin-top:52px}
.sec-head h2{font-size:23px;margin:0 0 6px;letter-spacing:-.015em;font-weight:760}
.sec-head p{color:var(--mut);margin:0 0 18px;max-width:780px;font-size:15px}
.card{background:linear-gradient(180deg,#111824,#0f141d);border:1px solid var(--line);
 border-radius:16px;padding:22px}
.legend{display:flex;flex-wrap:wrap;gap:8px 18px;margin-bottom:8px;font-size:13.5px;color:var(--mut)}
.legend .li{display:inline-flex;align-items:center;gap:7px}
.legend .sw{width:11px;height:11px;border-radius:4px;display:inline-block}
.graph-scroll{overflow-x:auto;padding:6px 0 2px}
.graph-scroll svg{min-width:880px;width:100%;height:auto;display:block}
svg .edge{fill:none;stroke:#43536b;stroke-width:1.1;opacity:.5;transition:opacity .15s}
svg .edge.sup{stroke:var(--amber);stroke-dasharray:4 3;opacity:.7}
svg.focus .edge{opacity:.05}
svg.focus .edge.hl{opacity:1;stroke:#9db9dd;stroke-width:1.7}
svg.focus .edge.sup.hl{stroke:var(--amber)}
svg .node{transition:opacity .15s}
svg.focus .node{opacity:.2}
svg.focus .node.hl{opacity:1}
svg .node text{fill:#eaf1f8;font-size:11.5px;font-weight:550;pointer-events:none}
svg .node:hover rect{stroke-width:2.2}
.hint{color:var(--mut2);font-size:13px;margin:10px 2px 0}
.bars{display:flex;flex-direction:column;gap:13px}
.bar-row{display:grid;grid-template-columns:180px 1fr 168px;gap:14px;align-items:center}
.bar-row .bname{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;
 font-size:13.5px;text-align:right}
.bar-row .bname a{color:var(--txt)}
.bar-row .bname a:hover{color:var(--blue);text-decoration:none}
.track{height:17px;background:#1a232f;border-radius:9px;overflow:hidden}
.fill{height:100%;width:0;border-radius:9px;
 background:linear-gradient(90deg,#1f6feb,#39c5cf);transition:width 1.1s cubic-bezier(.2,.7,.2,1)}
.fill.preload{background:repeating-linear-gradient(45deg,#5a3a3a,#5a3a3a 7px,#6b4444 7px,#6b4444 14%)}
.fill.preload{width:100%}
.bval{font-size:13.5px;color:var(--mut);white-space:nowrap}
.bval b{color:var(--txt)}
.bar-row.pre .bname{color:var(--mut);font-family:inherit;font-weight:650}
.chips{display:flex;flex-wrap:wrap;gap:8px}
.chip{display:inline-block;border:1px solid var(--line2);border-radius:999px;
 padding:5px 14px;font-size:13.5px;color:var(--txt);background:#141c28}
.chip:hover{border-color:var(--blue);text-decoration:none;transform:translateY(-1px)}
.chip.on{border-color:var(--green);background:rgba(63,185,80,.12);color:#b7f0bf}
.timeline{position:relative;margin:6px 0 2px;padding-left:30px}
.timeline:before{content:"";position:absolute;left:9px;top:10px;bottom:10px;
 width:2px;background:linear-gradient(180deg,var(--line2),var(--green))}
.step{position:relative;padding:0 0 22px}
.step:last-child{padding-bottom:2px}
.step .dot{position:absolute;left:-30px;top:5px;width:20px;height:20px;border-radius:50%;
 background:#1a232f;border:2px solid var(--line2)}
.step.superseded .dot{background:#141a22}
.step.current .dot{background:var(--green);border-color:#7ee2a0;
 box-shadow:0 0 0 5px rgba(63,185,80,.18)}
.step-body{background:rgba(255,255,255,.015);border:1px solid transparent;border-radius:12px;padding:10px 14px}
.step.current .step-body{background:rgba(63,185,80,.06);border-color:rgba(63,185,80,.35)}
.step-head{display:flex;flex-wrap:wrap;align-items:center;gap:9px}
.step-head .ts{color:var(--mut);font-size:13px;font-variant-numeric:tabular-nums}
.step-detail{margin-top:5px;font-size:15px}
.step-prov{color:var(--mut2);font-size:12.5px;margin-top:3px}
.badge{display:inline-block;border-radius:999px;padding:1px 11px;font-size:12.5px;
 font-weight:700;letter-spacing:.02em}
.b-real{background:rgba(63,185,80,.15);color:#7ee2a0;border:1px solid rgba(63,185,80,.45)}
.b-pot{background:rgba(210,153,34,.14);color:#eec26a;border:1px solid rgba(210,153,34,.45)}
.b-ind{background:rgba(248,81,73,.13);color:#ff9d97;border:1px solid rgba(248,81,73,.45)}
.b-def{background:rgba(143,161,179,.13);color:var(--mut);border:1px solid var(--line2)}
.tag{font-size:11px;letter-spacing:.09em;font-weight:700;color:var(--mut2);text-transform:uppercase}
.tag-cur{color:#7ee2a0}
table{border-collapse:collapse;width:100%;margin:6px 0}
td,th{padding:9px 10px;text-align:left;vertical-align:top;border-bottom:1px solid var(--line)}
tr:last-child td{border-bottom:none}
th{color:var(--mut);font-size:12px;letter-spacing:.11em;text-transform:uppercase;font-weight:650}
pre{background:#0a0e14;border:1px solid var(--line);border-radius:12px;
 padding:14px;overflow:auto;font-size:12px;max-height:440px;line-height:1.45}
code{background:#182130;padding:1px 6px;border-radius:5px;font-size:.92em}
.small{color:var(--mut);font-size:13.5px}
.pill{display:inline-block;background:#16202e;border:1px solid var(--line2);
 border-radius:999px;padding:3px 12px;margin:2px 4px 2px 0;font-size:13px;color:var(--txt)}
.big-stat{font-size:40px;font-weight:800;letter-spacing:-.02em;line-height:1.1}
.backlink{font-size:14px;color:var(--mut)}
footer{margin-top:64px;border-top:1px solid var(--line);padding-top:18px;
 color:var(--mut2);font-size:13px;line-height:1.6}
footer a{color:var(--mut)}
@media (max-width:760px){
 h1{font-size:33px} .pitch{font-size:18px} .hero{padding-top:30px}
 .bar-row{grid-template-columns:1fr;gap:5px}
 .bar-row .bname{text-align:left}
 .card{padding:16px} .timeline{padding-left:24px}
 .step .dot{left:-24px}
}
"""

SCRIPT = """
<script>
window.addEventListener('load',function(){
 document.querySelectorAll('.fill[data-w]').forEach(function(f){
  f.style.width=f.getAttribute('data-w')+'%';});
 var svg=document.getElementById('graph');
 if(!svg) return;
 var edges=[].slice.call(svg.querySelectorAll('.edge'));
 var nodes={};
 svg.querySelectorAll('.node').forEach(function(n){nodes[n.getAttribute('data-id')]=n;});
 var adj={};
 edges.forEach(function(e){
  var s=e.getAttribute('data-s'),t=e.getAttribute('data-t');
  (adj[s]=adj[s]||[]).push(t); (adj[t]=adj[t]||[]).push(s);});
 function setHl(id,on){
  var n=nodes[id]; if(!n) return;
  if(on){ svg.classList.add('focus'); n.classList.add('hl');
   (adj[id]||[]).forEach(function(m){ if(nodes[m]) nodes[m].classList.add('hl'); });
   edges.forEach(function(e){
    if(e.getAttribute('data-s')===id||e.getAttribute('data-t')===id) e.classList.add('hl'); });
  } else { svg.classList.remove('focus');
   svg.querySelectorAll('.hl').forEach(function(x){x.classList.remove('hl');}); }
 }
 Object.keys(nodes).forEach(function(id){
  var n=nodes[id];
  n.addEventListener('mouseenter',function(){setHl(id,true);});
  n.addEventListener('mouseleave',function(){setHl(id,false);});
  n.addEventListener('click',function(){setHl(id,true);});
 });
});
</script>
"""

LOGO = ("<svg width='26' height='26' viewBox='0 0 26 26' fill='none'>"
        "<circle cx='6' cy='6' r='3.4' fill='#a371f7'/>"
        "<circle cx='20' cy='9' r='3.4' fill='#58a6ff'/>"
        "<circle cx='11' cy='20' r='3.4' fill='#3fb950'/>"
        "<path d='M8.5 7.5 16.8 8.6M7.2 9.2 9.6 17M18.6 11.8 13.2 17.6' "
        "stroke='#43536b' stroke-width='1.6'/></svg>")

def esc(x):
    return html.escape(str(x))

def fmt_ts(ts):
    try:
        return demo.parse_ts(ts).strftime("%Y-%m-%d · %H:%M UTC")
    except Exception:
        return str(ts)

def live_counts():
    kinds = {}
    for kind in KINDS:
        kinds[kind] = len(rows(q(
            "MATCH (n) WHERE n.kind = '%s' RETURN n.id AS id" % kind)))
    edges = {}
    for et in EDGE_TYPES:
        edges[et] = len(rows(q(
            "MATCH (a)-[r:%s]->(b) RETURN a.id AS id" % et)))
    return kinds, edges

def entity_names():
    return [r["name"] for r in rows(q(
        "MATCH (n) WHERE n.kind = 'Entity' RETURN n.name AS name"))]

def all_edges():
    out = []
    for et in EDGE_TYPES:
        for r in rows(q("MATCH (a)-[r:%s]->(b) RETURN a.id AS src, b.id AS dst" % et)):
            out.append({"src": r["src"], "dst": r["dst"], "type": et})
    return out

def graph_nodes(fc):
    """Node list for the diagram, built from demo.full_catalog() rows."""
    nodes = []
    for kind, key in (("TaskType", "task_types"), ("Skill", "skills"),
                      ("Tool", "tools"), ("MCPServer", "mcp_servers"),
                      ("Entity", "entities")):
        for r in fc[key]:
            nodes.append({"id": r["id"], "kind": kind, "name": r["name"]})
    for r in fc["verdicts"]:
        nodes.append({"id": r["id"], "kind": "Verdict", "name": r["label"],
                      "detail": r["detail"], "ts": r["ts"]})
    return nodes

# ---- SVG graph layout: layered columns by kind, barycenter ordering ----
COL_X = {"TaskType": 130, "Skill": 375, "Tool": 605, "MCPServer": 605,
         "Entity": 845, "Verdict": 1095}
PILL_W = {"TaskType": 200, "Skill": 260, "Tool": 160, "MCPServer": 160,
          "Entity": 220, "Verdict": 130}
MAX_CH = {"TaskType": 27, "Skill": 36, "Tool": 21, "MCPServer": 21,
          "Entity": 30, "Verdict": 16}
FLOW = ("TaskType", "Skill", "Tool", "MCPServer", "Entity", "Verdict")
PITCH, TOP_PAD, SVG_W = 44, 26, 1240

def _truncate(s, n):
    s = str(s)
    return s if len(s) <= n else s[:n - 1] + "…"

def layout(nodes, edges):
    by_kind = {k: sorted([n for n in nodes if n["kind"] == k],
                         key=lambda n: n["id"]) for k in FLOW}
    pred, succ = {}, {}
    for n in nodes:
        pred[n["id"]], succ[n["id"]] = [], []
    for e in edges:
        succ[e["src"]].append(e["dst"])
        pred[e["dst"]].append(e["src"])
    pos = {}
    for k in FLOW:
        for i, n in enumerate(by_kind[k]):
            pos[n["id"]] = i

    def reorder(kind, nbrs):
        lst = by_kind[kind]
        def key(n):
            ns = [pos[m] for m in nbrs[n["id"]] if m in pos]
            return sum(ns) / len(ns) if ns else pos[n["id"]]
        lst.sort(key=key)
        for i, n in enumerate(lst):
            pos[n["id"]] = i

    for _ in range(2):
        for k in FLOW[1:]:
            reorder(k, pred)
        for k in reversed(FLOW[:-1]):
            reorder(k, succ)
    # verdicts: regroup tightly under their entity, newest first in-group
    ent_of = {}
    for e in edges:
        if e["type"] == "HAS_VERDICT":
            ent_of[e["dst"]] = e["src"]
    by_kind["Verdict"].sort(key=lambda n: (pos.get(ent_of.get(n["id"]), 0),
                                           _ts_key(n)))
    height = TOP_PAD * 2 + PITCH * max(len(v) for v in by_kind.values())
    for k in FLOW:
        lst = by_kind[k]
        y0 = (height - len(lst) * PITCH) / 2
        for i, n in enumerate(lst):
            n["x"] = COL_X[k]
            n["y"] = y0 + PITCH * i + PITCH / 2
    return height

def _ts_key(n):
    # descending timestamp (newest first) as an ascending sort key
    ts = str(n.get("ts", ""))
    return tuple(-ord(c) for c in ts)

def svg_graph(nodes, edges):
    height = layout(nodes, edges)
    by_id = {n["id"]: n for n in nodes}
    parts = [f"<svg id='graph' viewBox='0 0 {SVG_W} {height}' "
             f"role='img' aria-label='SkillGraph network diagram'>"
             "<defs><marker id='arr' viewBox='0 0 10 10' refX='9' refY='5' "
             "markerWidth='6.5' markerHeight='6.5' orient='auto-start-reverse'>"
             "<path d='M0,0 L10,5 L0,10 z' fill='#54677f'/></marker></defs>"]
    for e in edges:
        a, b = by_id[e["src"]], by_id[e["dst"]]
        wa, wb = PILL_W[a["kind"]] / 2, PILL_W[b["kind"]] / 2
        cls = "edge sup" if e["type"] == "SUPERSEDES" else "edge"
        if a["kind"] == b["kind"] and e["type"] == "SUPERSEDES":
            x = a["x"] + wa
            d = (f"M {x:.0f},{a['y']:.0f} C {x + 36:.0f},{a['y']:.0f} "
                 f"{x + 36:.0f},{b['y']:.0f} {x:.0f},{b['y']:.0f}")
        elif a["kind"] == b["kind"]:
            x = a["x"] - wa
            d = (f"M {x:.0f},{a['y']:.0f} C {x - 28:.0f},{a['y']:.0f} "
                 f"{x - 28:.0f},{b['y']:.0f} {x:.0f},{b['y']:.0f}")
        else:
            x1, x2 = a["x"] + wa, b["x"] - wb
            d = (f"M {x1:.0f},{a['y']:.0f} C {x1 + 34:.0f},{a['y']:.0f} "
                 f"{x2 - 34:.0f},{b['y']:.0f} {x2:.0f},{b['y']:.0f}")
        parts.append(f"<path class='{cls}' data-s='{a['id']}' data-t='{b['id']}' "
                     f"d='{d}' marker-end='url(#arr)'/>")
    for n in nodes:
        col = KIND_COLOR[n["kind"]]
        w = PILL_W[n["kind"]]
        label = _truncate(n["name"], MAX_CH[n["kind"]])
        title = n.get("detail") or n["name"]
        g = (f"<g class='node' data-id='{n['id']}' data-kind='{n['kind']}' "
             f"transform='translate({n['x']:.0f},{n['y']:.0f})'>"
             f"<title>{esc(n['kind'])}: {esc(title)}</title>"
             f"<rect x='{-w / 2:.0f}' y='-12' width='{w}' height='24' rx='12' "
             f"fill='{col}' fill-opacity='0.13' stroke='{col}' stroke-width='1.2'/>"
             f"<text text-anchor='middle' dy='0.36em'>{esc(label)}</text></g>")
        if n["kind"] == "TaskType":
            g = f"<a href='/bundle?task={quote(str(n['name']))}'>{g}</a>"
        elif n["kind"] == "Entity":
            g = f"<a href='/chain?entity={quote(str(n['name']))}'>{g}</a>"
        elif n["kind"] == "Verdict":
            ent = next((by_id[e["src"]]["name"] for e in edges
                        if e["type"] == "HAS_VERDICT" and e["dst"] == n["id"]), None)
            if ent:
                g = f"<a href='/chain?entity={quote(str(ent))}'>{g}</a>"
        parts.append(g)
    parts.append("</svg>")
    return "".join(parts)

def label_badge(label):
    cls = {"real": "b-real", "berpotensi": "b-pot",
           "indikasi": "b-ind"}.get(label, "b-def")
    return f"<span class='badge {cls}'>{esc(label)}</span>"

def timeline_html(entity):
    vs = demo.verdicts_of(entity)
    sup = demo.superseded_ids(entity)
    cur = demo.current_verdict(entity)
    steps = ""
    for v in sorted(vs, key=lambda v: v["ts"]):
        is_cur = bool(cur) and v["vid"] == cur["vid"]
        state = "current" if is_cur else ("superseded" if v["vid"] in sup else "open")
        tag = ("<span class='tag tag-cur'>Current — nobody supersedes it</span>"
               if is_cur else
               "<span class='tag'>Superseded</span>" if state == "superseded" else "")
        steps += f"""
<div class='step {state}'><div class='dot'></div><div class='step-body'>
<div class='step-head'>{label_badge(v['label'])}
<span class='ts'>{esc(fmt_ts(v['ts']))}</span>{tag}</div>
<div class='step-detail'>{esc(v['detail'])}</div>
<div class='step-prov'>{esc(v['provenance'])}</div>
</div></div>"""
    return f"<div class='timeline'>{steps}</div>"

def chips_html(names, current=None):
    out = ""
    for n in names:
        cls = "chip on" if n == current else "chip"
        out += f"<a class='{cls}' href='/chain?entity={quote(n)}'>{esc(n)}</a>"
    return f"<div class='chips'>{out}</div>"

def page(title, body, script=""):
    return ("<!DOCTYPE html><html><head><meta charset='utf-8'>"
            "<meta name='viewport' content='width=device-width,initial-scale=1'>"
            "<meta name='description' content='SkillGraph — the agent context "
            "layer on HydraDB. Live demo: real graph traversals, context "
            "bundles and verdict chains, queried live.'>"
            f"<title>{esc(title)}</title><style>{CSS}</style></head>"
            f"<body><div class='wrap'>"
            "<div class='topbar'>"
            f"<a class='brand' href='/'>{LOGO}SkillGraph</a>"
            "<nav><a href='/'>Live demo</a>"
            "<a href='https://github.com/Revaaa28/skillgraph'>GitHub</a></nav>"
            f"</div>{body}"
            "<footer>Data: skills &amp; tools are the agent's real playbooks; "
            "entities &amp; verdicts are the live Mint RedCeh free-mint board "
            "(on-chain verification, BSC). Engine: self-hosted open-source "
            "HydraDB (<a href='https://github.com/hydra-db/hydradb'>hydra-db/hydradb</a>) "
            "running next to this page — every number above is a fresh query "
            "against it, nothing is cached or staged.</footer>"
            f"</div>{script}</body></html>")

def home():
    t0 = time.perf_counter()
    fc = demo.full_catalog()
    preload = demo.bsize(fc)
    edges = all_edges()
    nodes = graph_nodes(fc)
    kind_count = {"Skill": len(fc["skills"]), "Tool": len(fc["tools"]),
                  "MCPServer": len(fc["mcp_servers"]),
                  "TaskType": len(fc["task_types"]),
                  "Entity": len(fc["entities"]), "Verdict": len(fc["verdicts"])}
    edge_count = {et: sum(1 for e in edges if e["type"] == et)
                  for et in EDGE_TYPES}
    now = datetime.now(timezone.utc)
    bundles = []
    for t in TASKS:
        b_obj, _stale = demo.assemble_bundle(t, stale_hours=24.0, now=now)
        b = demo.bsize(b_obj)
        bundles.append((t, b, 100.0 * (1 - b / preload)))
    avg_saved = sum(s for _t, _b, s in bundles) / len(bundles)
    min_bundle = min(b for _t, b, _s in bundles)
    graph_svg = svg_graph(nodes, edges)
    names = entity_names()
    ink = "Ink Koi (INKOI)"
    ink_timeline = timeline_html(ink)
    ms = (time.perf_counter() - t0) * 1000

    legend = "".join(
        f"<span class='li'><span class='sw' style='background:{KIND_COLOR[k]}'>"
        f"</span>{k} · {kind_count[k]}</span>" for k in
        ("TaskType", "Skill", "Tool", "MCPServer", "Entity", "Verdict"))
    bars = f"""
<div class='bar-row pre'><div class='bname'>Preload — full catalog</div>
<div class='track'><div class='fill preload'></div></div>
<div class='bval'><b>{preload:,}</b> bytes · baseline</div></div>"""
    for t, b, saved in bundles:
        w = max(2.0, 100.0 * b / preload)
        bars += f"""
<div class='bar-row'><div class='bname'><a href='/bundle?task={quote(t)}'>{esc(t)}</a></div>
<div class='track'><div class='fill' data-w='{w:.1f}'></div></div>
<div class='bval'><b>{b:,}</b> bytes · <b>−{saved:.1f}%</b></div></div>"""

    body = f"""
<div class='hero'>
<span class='eyebrow'><span class='dot-live'></span>Live demo · self-hosted HydraDB</span>
<h1>SkillGraph</h1>
<p class='pitch'>The agent context layer on HydraDB.</p>
<p class='lead'>An AI agent's skills, tools, MCP servers, the entities it
works on and <b>verified verdicts about those entities</b> live in one
HydraDB graph. For a task, the agent traverses only the subgraph it needs
and assembles a minimal context bundle — instead of preloading the whole
catalog into every prompt.</p>
<div class='stats'>
<div class='stat'><div class='num'>{sum(kind_count.values())}</div>
<div class='lbl'>Graph nodes</div>
<div class='sub'>{" · ".join(f"{k} {v}" for k, v in kind_count.items())}</div></div>
<div class='stat'><div class='num'>{len(edges)}</div>
<div class='lbl'>Graph edges</div>
<div class='sub'>{" · ".join(f"{k} {v}" for k, v in edge_count.items())}</div></div>
<div class='stat'><div class='num'>−{avg_saved:.0f}%</div>
<div class='lbl'>Avg. context saved</div>
<div class='sub'>Average live bundle vs the {preload:,}-byte preload across
the {len(bundles)} task types — smallest bundle {min_bundle:,} bytes</div></div>
</div>
<p class='meta-line'>Counted live from the graph just now — this page took
{ms:.0f} ms of query time to render. Nothing here is cached or staged.</p>
</div>

<section><div class='sec-head'><h2>The graph, live</h2>
<p>Every node and edge below was just read from the running HydraDB node.
Tasks flow into skills, skills into tools, MCP servers and entities, and
entities into their verdict chains.</p></div>
<div class='card'><div class='legend'>{legend}</div>
<div class='graph-scroll'>{graph_svg}</div>
<p class='hint'>Hover any node to trace its connections. Task pills open
their live context bundle; entity and verdict pills open the verdict
chain. Amber dashed arcs are SUPERSEDES — newer verdicts replacing older
ones without erasing them.</p></div></section>

<section><div class='sec-head'><h2>The baseline this beats</h2>
<p>Preloading the entire catalog — every skill, tool, MCP server, task
type, entity and <i>all</i> verdicts including history — serializes to
{preload:,} bytes, and still goes stale the moment any verdict changes.
A SkillGraph bundle is assembled by traversal, per task, right now:</p></div>
<div class='card'><div class='bars'>{bars}</div>
<p class='hint'>Click a task name to see its exact live bundle — skills,
tools, current entity verdicts and the JSON handed to the agent.</p></div></section>

<section><div class='sec-head'><h2>Verdicts that learn: SUPERSEDES chains</h2>
<p>Verdicts accumulate with timestamps. A newer verdict
<code>SUPERSEDES</code> the older one; the current verdict is derived by
traversal — the chain vertex nobody supersedes — never by overwriting.
History stays in the graph, so the agent can also answer what it believed
last week, and why it changed.</p></div>
<div class='card'><p style='margin-top:0' class='small'>Pick an entity to
inspect its full chain, including time travel:</p>
{chips_html(names)}
<p class='small' style='margin:18px 0 4px'>Shown: <b>{esc(ink)}</b> — real
verdicts from the Mint RedCeh board's on-chain autocheck. The free mint
went from “243 slots left” to “free lane CLOSED”, and the graph's current
answer tracked it:</p>
{ink_timeline}</div></section>
"""
    return page("SkillGraph — the agent context layer on HydraDB", body, SCRIPT)

def bundle_page(task):
    if task not in TASKS:
        return None
    t0 = time.perf_counter()
    now = datetime.now(timezone.utc)
    bundle, stale = demo.assemble_bundle(task, stale_hours=24.0, now=now)
    full = demo.full_catalog()
    preload = demo.bsize(full)
    b = demo.bsize(bundle)
    ms = (time.perf_counter() - t0) * 1000
    saved = 100.0 * (1 - b / preload)
    skills = "".join(
        f"<tr><td><code>{esc(s['name'])}</code></td><td>{esc(s['purpose'])}</td></tr>"
        for s in bundle["skills"])
    tools = " ".join(f"<span class='pill'>{esc(t['name'])}</span>"
                     for t in bundle["tools"])
    ents = ""
    for e in bundle["entities"]:
        v = e.get("verdict")
        if v:
            vt = (f"{label_badge(v['label'])} {esc(v['detail'])}<br>"
                  f"<span class='small'>verdict ts {esc(v['ts'])} · "
                  f"{esc(v['provenance'])}</span>")
        elif "verdict_excluded" in e:
            vt = esc(e["verdict_excluded"])
        else:
            vt = "<i>no current verdict</i>"
        ents += (f"<tr><td><a href='/chain?entity={quote(e['name'])}'>"
                 f"{esc(e['name'])}</a></td><td>{vt}</td></tr>")
    ent_section = (
        f"<section><div class='sec-head'><h2>Entities + current verdicts</h2>"
        f"<p>Derived via SUPERSEDES traversal at render time.</p></div>"
        f"<div class='card'><table><tr><th>Entity</th><th>Current verdict</th>"
        f"</tr>{ents}</table></div></section>" if bundle["entities"] else "")
    body = f"""
<p style='margin-top:26px'><a class='backlink' href='/'>← all tasks</a></p>
<div class='hero' style='padding-top:10px'>
<span class='eyebrow'><span class='dot-live'></span>Live bundle · assembled by traversal</span>
<h1 style='font-size:36px'>{esc(task)}</h1>
<div class='stats' style='grid-template-columns:repeat(auto-fit,minmax(200px,1fr))'>
<div class='stat'><div class='num'>{b:,}</div><div class='lbl'>Bundle bytes</div>
<div class='sub'>Handed to the agent for this task</div></div>
<div class='stat'><div class='num'>−{saved:.1f}%</div><div class='lbl'>Vs preload</div>
<div class='sub'>Baseline full-catalog preload is {preload:,} bytes</div></div>
<div class='stat'><div class='num'>{ms:.0f} ms</div><div class='lbl'>Assembly time</div>
<div class='sub'>Live traversal · stale verdicts excluded by the 24 h guard: {stale}</div></div>
</div></div>

<section><div class='sec-head'><h2>Skills</h2>
<p>Reached via TaskType → NEEDS_SKILL.</p></div>
<div class='card'><table><tr><th>Skill</th><th>Purpose</th></tr>{skills}</table></div></section>

<section><div class='sec-head'><h2>Tools</h2>
<p>Reached via Skill → USES_TOOL.</p></div>
<div class='card'><p style='margin:2px 0'>{tools}</p></div></section>
{ent_section}
<section><div class='sec-head'><h2>The exact bundle JSON</h2>
<p>Precisely what the agent receives — nothing more, nothing stale.</p></div>
<pre>{esc(json.dumps(bundle, indent=1, sort_keys=True))}</pre></section>
"""
    return page(f"SkillGraph bundle — {task}", body)

def chain_page(entity):
    names = entity_names()
    if entity not in names:
        return None
    t0 = time.perf_counter()
    vs = demo.verdicts_of(entity)
    cur = demo.current_verdict(entity)
    ms = (time.perf_counter() - t0) * 1000
    vs_sorted = sorted(vs, key=lambda v: v["ts"])
    tt = ""
    for v in vs_sorted:
        at = demo.verdict_at(entity, v["ts"])
        if at:
            tt += (f"<tr><td>{esc(fmt_ts(v['ts']))}</td>"
                   f"<td>{label_badge(at['label'])} {esc(at['detail'])}</td></tr>")
    if cur:
        tt += (f"<tr><td>now</td><td>{label_badge(cur['label'])} "
               f"{esc(cur['detail'])}</td></tr>")
    cur_line = (f"{label_badge(cur['label'])} {esc(cur['detail'])}"
                if cur else "<i>no current verdict</i>")
    body = f"""
<p style='margin-top:26px'><a class='backlink' href='/'>← home</a></p>
<div class='hero' style='padding-top:10px'>
<span class='eyebrow'><span class='dot-live'></span>Verdict chain · queried live in {ms:.0f} ms</span>
<h1 style='font-size:36px'>{esc(entity)}</h1>
<p class='lead'>Current verdict: {cur_line}</p>
<p class='small'>Derivation rule: the current verdict is the HAS_VERDICT
vertex that no other verdict SUPERSEDES. History is never overwritten —
it stays traversable.</p>
<div style='margin-top:16px'>{chips_html(names, current=entity)}</div>
</div>

<section><div class='sec-head'><h2>The chain</h2>
<p>Oldest first — each step is a real verdict vertex in the graph.</p></div>
<div class='card'>{timeline_html(entity)}</div></section>

<section><div class='sec-head'><h2>Time travel</h2>
<p>The verdict in force at each moment. A flat key-value store can only
return the latest write; the chain is what lets the agent answer “what
did we believe on Nov 11 — and why did it change?”</p></div>
<div class='card'><table><tr><th>At</th><th>Verdict then</th></tr>{tt}</table></div></section>
"""
    return page(f"SkillGraph chain — {entity}", body)

class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, body, code=200, ctype="text/html; charset=utf-8"):
        data = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        u = urlparse(self.path)
        qs = parse_qs(u.query)
        try:
            if u.path == "/healthz":
                self._send("ok")
            elif u.path == "/graph.json":
                fc = demo.full_catalog()
                self._send(json.dumps({"nodes": graph_nodes(fc),
                                       "edges": all_edges()}),
                           ctype="application/json")
            elif u.path == "/":
                self._send(home())
            elif u.path == "/bundle":
                p = bundle_page((qs.get("task") or [""])[0])
                self._send(p if p else page("not found", "<h1>Unknown task</h1>"), 200 if p else 404)
            elif u.path == "/chain":
                p = chain_page((qs.get("entity") or [""])[0])
                self._send(p if p else page("not found", "<h1>Unknown entity</h1>"), 200 if p else 404)
            else:
                self._send(page("not found", "<h1>404</h1>"), 404)
        except Exception as e:
            self._send(page("error", f"<h1>Live query failed</h1><pre>{esc(e)}</pre>"), 500)

if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", PORT), H).serve_forever()
