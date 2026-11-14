"""SkillGraph synthetic scale test for HydraDB.

The real demo graph is small (62 nodes / 73 edges) on purpose - it is real
data. This script answers the separate question the judges ask: does the
same traversal shape hold up at scale and under concurrent load?

Method:
- Generates ~5,000 nodes / ~10,000 edges in the SkillGraph schema shape
  (TaskType / Skill / Tool / MCPServer / Entity / Verdict + the six edge
  types) with deterministic wiring (random.Random(20261114)).
- Synthetic data lives ONLY in the id range >= 1_000_000 and every name is
  prefixed `synth_`, strictly separate from the real demo graph (ids < 700).
- Benchmarks, over HTTP against the node on localhost:
  (a) 200 sequential runs of each traversal shape used by demo.py:
      TaskType -> Skill -> Tool, and Entity -> latest Verdict
      (two traversals + set difference, the engine has no NOT EXISTS);
  (b) concurrent load: 8 parallel clients x 125 traversals = 1,000 ops,
      alternating the two shapes; result correctness is checked inline.
- `clean` DETACH DELETEs the whole synthetic id range and the caller
  re-verifies the real graph counts (62 nodes / 73 edges).

Usage: python3 scale_gen.py counts|load|bench|clean
Auth: same as sg.py (HYDRA_TOKEN / HYDRA_TOKEN_FILE).
"""
import json, os, random, sys, time
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sg import q, rows

SEED = 20261114
BASE = 1_000_000

# ---- synthetic population (totals: 5,000 nodes, 10,000 edges) ----------
N_TASK, N_SKILL, N_TOOL, N_MCP = 40, 300, 240, 60
N_ENT, N_VERD = 1_800, 2_560
TASK0 = BASE
SKILL0 = BASE + 1_000
TOOL0 = BASE + 2_000
MCP0 = BASE + 3_000
ENT0 = BASE + 4_000
VERD0 = BASE + 6_000
CHAINED_ENTS = 760  # first 760 entities carry a 2-verdict SUPERSEDES chain

TASK_IDS = list(range(TASK0, TASK0 + N_TASK))
SKILL_IDS = list(range(SKILL0, SKILL0 + N_SKILL))
TOOL_IDS = list(range(TOOL0, TOOL0 + N_TOOL))
MCP_IDS = list(range(MCP0, MCP0 + N_MCP))
ENT_IDS = list(range(ENT0, ENT0 + N_ENT))
VERD_IDS = list(range(VERD0, VERD0 + N_VERD))
ALL_IDS = TASK_IDS + SKILL_IDS + TOOL_IDS + MCP_IDS + ENT_IDS + VERD_IDS

LABELS = ["real", "indikasi", "berpotensi", "staged"]


def gen():
    """Deterministic (nodes, edges) as (cypher, params) statement lists."""
    rng = random.Random(SEED)
    nodes, edges = [], []

    for i, nid in enumerate(TASK_IDS):
        nodes.append(("CREATE (n {id: $id, kind: 'TaskType', name: $name, description: $d})",
                      {"id": nid, "name": f"synth_task_{i:03d}",
                       "d": "SYNTHETIC scale-test task type"}))
    for i, nid in enumerate(SKILL_IDS):
        nodes.append(("CREATE (n {id: $id, kind: 'Skill', name: $name, purpose: $p})",
                      {"id": nid, "name": f"synth_skill_{i:03d}",
                       "p": "SYNTHETIC scale-test skill"}))
    for i, nid in enumerate(TOOL_IDS):
        nodes.append(("CREATE (n {id: $id, kind: 'Tool', name: $name, toolkind: $tk})",
                      {"id": nid, "name": f"synth_tool_{i:03d}", "tk": "CLI - synthetic"}))
    for i, nid in enumerate(MCP_IDS):
        nodes.append(("CREATE (n {id: $id, kind: 'MCPServer', name: $name, transport: $tr})",
                      {"id": nid, "name": f"synth_mcp_{i:03d}", "tr": "stdio"}))
    for i, nid in enumerate(ENT_IDS):
        nodes.append(("CREATE (n {id: $id, kind: 'Entity', name: $name, entkind: $ek, ref: $ref})",
                      {"id": nid, "name": f"synth_entity_{i:04d}",
                       "ek": "nft-project", "ref": f"0x{i:040x}"}))

    # verdicts: one per entity, then a second (newer) verdict for the first
    # CHAINED_ENTS entities -> SUPERSEDES chains of length 2
    verdict_of = {}
    for i, eid in enumerate(ENT_IDS):
        verdict_of.setdefault(eid, []).append(VERD_IDS[i])
    for j in range(CHAINED_ENTS):
        verdict_of[ENT_IDS[j]].append(VERD_IDS[N_ENT + j])
    for i, vid in enumerate(VERD_IDS):
        day = 1 + (i % 13)
        nodes.append(("CREATE (n {id: $id, kind: 'Verdict', label: $label, detail: $detail, ts: $ts, provenance: $prov})",
                      {"id": vid, "label": LABELS[i % len(LABELS)],
                       "detail": "SYNTHETIC scale-test verdict",
                       "ts": f"2026-11-{day:02d}T00:00:00Z",
                       "prov": "SYNTHETIC scale test (scale_gen.py) - not real data"}))

    def edge(a, t, b):
        edges.append((f"CREATE (a {{id: $a}})-[:{t}]->(b {{id: $b}})", {"a": a, "b": b}))

    for t in TASK_IDS:                                   # NEEDS_SKILL: 200
        for s in rng.sample(SKILL_IDS, 5):
            edge(t, "NEEDS_SKILL", s)
    for s in SKILL_IDS:                                  # USES_TOOL: 900
        for t in rng.sample(TOOL_IDS, 3):
            edge(s, "USES_TOOL", t)
    for _ in range(150):                                 # USES_TOOL: +150
        edge(rng.choice(SKILL_IDS), "USES_TOOL", rng.choice(TOOL_IDS))
    for t in TOOL_IDS:                                   # EXPOSED_VIA: 240
        edge(t, "EXPOSED_VIA", rng.choice(MCP_IDS))
    for s in SKILL_IDS:                                  # ABOUT: 5,100
        for e in rng.sample(ENT_IDS, 17):
            edge(s, "ABOUT", e)
    for _ in range(90):                                  # ABOUT: +90
        edge(rng.choice(SKILL_IDS), "ABOUT", rng.choice(ENT_IDS))
    for eid, vids in verdict_of.items():                 # HAS_VERDICT: 2,560
        for v in vids:
            edge(eid, "HAS_VERDICT", v)
        if len(vids) == 2:                               # SUPERSEDES: 760
            edge(vids[1], "SUPERSEDES", vids[0])
    return nodes, edges, verdict_of


# ---- counting ------------------------------------------------------------
def count(cypher, params=None):
    r = rows(q(cypher, params))
    return list(r[0].values())[0] if r else 0

def counts():
    # Engine quirk: bare scans (MATCH (n) RETURN count(*)) are rejected -
    # every count needs a WHERE property filter, so totals are summed from
    # per-kind / per-type parts, split at the synthetic id boundary BASE.
    kinds = ("Skill", "Tool", "MCPServer", "TaskType", "Entity", "Verdict")
    types = ("NEEDS_SKILL", "USES_TOOL", "ABOUT", "HAS_VERDICT",
             "SUPERSEDES", "EXPOSED_VIA")
    out = {"nodes_by_kind": {}, "nodes_real_by_kind": {},
           "nodes_synth_by_kind": {}, "edges_by_type": {},
           "edges_synth_by_type": {}}
    for kind in kinds:
        out["nodes_by_kind"][kind] = count(
            "MATCH (n) WHERE n.kind = $k RETURN count(*) AS c", {"k": kind})
        out["nodes_real_by_kind"][kind] = count(
            "MATCH (n) WHERE n.kind = $k AND n.id < $hi RETURN count(*) AS c",
            {"k": kind, "hi": BASE})
        out["nodes_synth_by_kind"][kind] = count(
            "MATCH (n) WHERE n.kind = $k AND n.id >= $lo RETURN count(*) AS c",
            {"k": kind, "lo": BASE})
    for t in types:
        out["edges_by_type"][t] = count(
            f"MATCH ()-[r:{t}]->() RETURN count(*) AS c")
        out["edges_synth_by_type"][t] = count(
            f"MATCH (a)-[r:{t}]->(b) WHERE a.id >= $lo RETURN count(*) AS c",
            {"lo": BASE})
    out["nodes_total"] = sum(out["nodes_by_kind"].values())
    out["nodes_real"] = sum(out["nodes_real_by_kind"].values())
    out["nodes_synth"] = sum(out["nodes_synth_by_kind"].values())
    out["edges_total"] = sum(out["edges_by_type"].values())
    out["edges_synth"] = sum(out["edges_synth_by_type"].values())
    out["edges_real"] = out["edges_total"] - out["edges_synth"]
    return out


# ---- load / clean ----------------------------------------------------------
def run_parallel(stmts, workers=16):
    errs = []
    def one(stmt):
        try:
            q(stmt[0], stmt[1])
        except Exception as e:  # noqa: BLE001 - collected and reported
            errs.append(str(e)[:200])
    with ThreadPoolExecutor(max_workers=workers) as ex:
        list(ex.map(one, stmts))
    return errs

def do_load():
    wipe = [("MATCH (n {id: $id}) DETACH DELETE n", {"id": nid}) for nid in ALL_IDS]
    errs = run_parallel(wipe)
    print(f"reset synthetic range: {len(wipe)} deletes, {len(errs)} errors")
    nodes, edges, _ = gen()
    t0 = time.perf_counter()
    errs = run_parallel(nodes)
    print(f"nodes: {len(nodes)} created in {time.perf_counter()-t0:.1f}s, {len(errs)} errors")
    if errs:
        print("first node errors:", errs[:3])
    t0 = time.perf_counter()
    errs = run_parallel(edges)
    print(f"edges: {len(edges)} created in {time.perf_counter()-t0:.1f}s, {len(errs)} errors")
    if errs:
        print("first edge errors:", errs[:3])

def do_clean():
    wipe = [("MATCH (n {id: $id}) DETACH DELETE n", {"id": nid}) for nid in ALL_IDS]
    t0 = time.perf_counter()
    errs = run_parallel(wipe)
    print(f"cleanup: {len(wipe)} DETACH DELETEs in {time.perf_counter()-t0:.1f}s, {len(errs)} errors")


# ---- benchmarks ------------------------------------------------------------
TASK_TOOLS_Q = ("MATCH (t {name: $n})-[:NEEDS_SKILL]->(s)-[:USES_TOOL]->(tool) "
                "RETURN s.name AS skill, tool.name AS tool")
LATEST_Q1 = ("MATCH (e {name: $entity})-[:HAS_VERDICT]->(v) "
             "RETURN v.id AS vid, v.label AS label, v.detail AS detail, "
             "v.ts AS ts, v.provenance AS provenance")
LATEST_Q2 = ("MATCH (e {name: $entity})-[:HAS_VERDICT]->(old)"
             "<-[:SUPERSEDES]-(newer) RETURN old.id AS vid")

def trav_task_tool(i):
    return rows(q(TASK_TOOLS_Q, {"n": f"synth_task_{i % N_TASK:03d}"}))

def trav_latest_verdict(i, verdict_of):
    """Latest-verdict lookup as a (rows, expected_current_id) pair.
    Cycles the CHAINED_ENTS entities (2-verdict chains) and plain ones."""
    if i % 2 == 0:
        ei = (i // 2) % CHAINED_ENTS
    else:
        ei = CHAINED_ENTS + ((i // 2) % (N_ENT - CHAINED_ENTS))
    name = f"synth_entity_{ei:04d}"
    allv = rows(q(LATEST_Q1, {"entity": name}))
    sup = {r["vid"] for r in rows(q(LATEST_Q2, {"entity": name}))}
    cur = [v for v in allv if v["vid"] not in sup]
    expected = verdict_of[ENT_IDS[ei]][-1]
    return cur, expected

def stats(lat):
    return {"n": len(lat), "avg_ms": round(sum(lat) / len(lat), 2),
            "min_ms": round(min(lat), 2), "max_ms": round(max(lat), 2)}

def do_bench():
    _, _, verdict_of = gen()
    results = {}
    # (a1) sequential TaskType->Skill->Tool, 200 runs
    lat, errors, wrong = [], 0, 0
    for i in range(200):
        s = time.perf_counter()
        try:
            r = trav_task_tool(i)
            if not r:
                wrong += 1
        except Exception:  # noqa: BLE001
            errors += 1
        lat.append((time.perf_counter() - s) * 1000.0)
    results["seq_task_skill_tool"] = {**stats(lat), "errors": errors, "wrong": wrong}
    print("seq TaskType->Skill->Tool:", results["seq_task_skill_tool"])
    # (a2) sequential Entity->latest Verdict (2 queries + set difference), 200 runs
    lat, errors, wrong = [], 0, 0
    for i in range(200):
        s = time.perf_counter()
        try:
            cur, expected = trav_latest_verdict(i, verdict_of)
            if len(cur) != 1 or cur[0]["vid"] != expected:
                wrong += 1
        except Exception:  # noqa: BLE001
            errors += 1
        lat.append((time.perf_counter() - s) * 1000.0)
    results["seq_latest_verdict"] = {**stats(lat), "errors": errors, "wrong": wrong}
    print("seq Entity->latest-Verdict:", results["seq_latest_verdict"])
    # (b) concurrency: 8 clients x 125 traversals, alternating shapes
    def worker(w):
        lat, errors, wrong = [], 0, 0
        for j in range(125):
            i = w * 125 + j
            s = time.perf_counter()
            try:
                if j % 2 == 0:
                    if not trav_task_tool(i):
                        wrong += 1
                else:
                    cur, expected = trav_latest_verdict(i, verdict_of)
                    if len(cur) != 1 or cur[0]["vid"] != expected:
                        wrong += 1
            except Exception:  # noqa: BLE001
                errors += 1
            lat.append((time.perf_counter() - s) * 1000.0)
        return lat, errors, wrong
    t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=8) as ex:
        parts = list(ex.map(worker, range(8)))
    wall = time.perf_counter() - t0
    lat = [x for p in parts for x in p[0]]
    results["concurrent_8x125"] = {**stats(lat),
                                   "errors": sum(p[1] for p in parts),
                                   "wrong": sum(p[2] for p in parts),
                                   "wall_s": round(wall, 2),
                                   "ops_per_s": round(len(lat) / wall, 1)}
    print("concurrent 8x125:", results["concurrent_8x125"])
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "scale-results.json"), "w") as f:
        json.dump(results, f, indent=1)
    print("results written to scale-results.json")


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "counts"
    if mode == "counts":
        print(json.dumps(counts(), indent=1))
    elif mode == "load":
        do_load()
        print(json.dumps(counts(), indent=1))
    elif mode == "bench":
        do_bench()
    elif mode == "clean":
        do_clean()
        print(json.dumps(counts(), indent=1))
    else:
        sys.exit(f"unknown mode {mode}")
