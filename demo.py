"""SkillGraph demos: traversal, context bundles, staleness guard,
verdict time-travel, and a 200-query load sanity check."""
import json, os, sys, time
from datetime import datetime, timezone
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sg import q, rows
HERE = os.path.dirname(os.path.abspath(__file__))

TASKS = ["verify_free_mint", "hunt_bounty", "play_agent_cards",
         "build_demo_site", "backtest_strategy"]

LATEST_Q1 = ("MATCH (e {name: $entity})-[:HAS_VERDICT]->(v) "
             "RETURN v.id AS vid, v.label AS label, v.detail AS detail, "
             "v.ts AS ts, v.provenance AS provenance")
LATEST_Q2 = ("MATCH (e {name: $entity})-[:HAS_VERDICT]->(old)"
             "<-[:SUPERSEDES]-(newer) RETURN old.id AS vid")

def parse_ts(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))

def verdicts_of(entity):
    return rows(q(LATEST_Q1, {"entity": entity}))

def superseded_ids(entity):
    return {r["vid"] for r in rows(q(LATEST_Q2, {"entity": entity}))}

def current_verdict(entity):
    sup = superseded_ids(entity)
    cur = [v for v in verdicts_of(entity) if v["vid"] not in sup]
    return cur[0] if cur else None

def verdict_at(entity, when_iso):
    """Time travel: the verdict in force at `when_iso` = newest chain
    verdict with ts <= when, following the SUPERSEDES history."""
    when = parse_ts(when_iso)
    chain = [v for v in verdicts_of(entity) if parse_ts(v["ts"]) <= when]
    if not chain:
        return None
    return max(chain, key=lambda v: parse_ts(v["ts"]))

def skills_for(task):
    return rows(q("MATCH (t {name: $n})-[:NEEDS_SKILL]->(s) "
                  "RETURN s.id AS id, s.name AS name, s.purpose AS purpose",
                  {"n": task}))

def tools_for(task):
    out, seen = [], set()
    for r in rows(q("MATCH (t {name: $n})-[:NEEDS_SKILL]->(s)-[:USES_TOOL]->(tool) "
                    "RETURN tool.id AS id, tool.name AS name, tool.toolkind AS toolkind",
                    {"n": task})):
        if r["id"] not in seen:
            seen.add(r["id"]); out.append(r)
    return out

def entities_for(task):
    out, seen = [], set()
    for r in rows(q("MATCH (t {name: $n})-[:NEEDS_SKILL]->(s)-[:ABOUT]->(e) "
                    "RETURN e.id AS id, e.name AS name, e.entkind AS entkind, e.ref AS ref",
                    {"n": task})):
        if r["id"] not in seen:
            seen.add(r["id"]); out.append(r)
    return out

def assemble_bundle(task, stale_hours, now):
    bundle = {"task": task, "skills": skills_for(task), "tools": tools_for(task),
              "entities": []}
    stale = 0
    for e in entities_for(task):
        v = current_verdict(e["name"])
        ent = dict(e)
        if v is None:
            ent["verdict"] = None
        else:
            age_h = (now - parse_ts(v["ts"])).total_seconds() / 3600.0
            if age_h > stale_hours:
                stale += 1
                ent["verdict"] = None
                ent["verdict_excluded"] = (
                    f"STALE: verdict from {v['ts']} is {age_h:.1f}h old "
                    f"(threshold {stale_hours}h) - excluded, re-verify before use")
            else:
                ent["verdict"] = {k: v[k] for k in ("label", "detail", "ts", "provenance")}
        bundle["entities"].append(ent)
    return bundle, stale

def full_catalog():
    cat = {}
    cat["skills"] = rows(q("MATCH (n) WHERE n.kind = 'Skill' RETURN n.id AS id, n.name AS name, n.purpose AS purpose"))
    cat["tools"] = rows(q("MATCH (n) WHERE n.kind = 'Tool' RETURN n.id AS id, n.name AS name, n.toolkind AS toolkind"))
    cat["mcp_servers"] = rows(q("MATCH (n) WHERE n.kind = 'MCPServer' RETURN n.id AS id, n.name AS name, n.transport AS transport"))
    cat["task_types"] = rows(q("MATCH (n) WHERE n.kind = 'TaskType' RETURN n.id AS id, n.name AS name, n.description AS description"))
    cat["entities"] = rows(q("MATCH (n) WHERE n.kind = 'Entity' RETURN n.id AS id, n.name AS name, n.entkind AS entkind, n.ref AS ref"))
    cat["verdicts"] = rows(q("MATCH (n) WHERE n.kind = 'Verdict' RETURN n.id AS id, n.label AS label, n.detail AS detail, n.ts AS ts, n.provenance AS provenance"))
    return cat

def bsize(obj):
    return len(json.dumps(obj, separators=(",", ":"), sort_keys=True).encode())

def main():
    now = datetime.now(timezone.utc)
    metrics = {"generated_at": now.isoformat(), "bundles": {}}
    print("=" * 72)
    print("DEMO A - 'verify free mint' traversal for entity: Ink Koi (INKOI)")
    print("=" * 72)
    print("skills:", [s["name"] for s in skills_for("verify_free_mint")])
    print("tools :", [t["name"] for t in tools_for("verify_free_mint")])
    v = current_verdict("Ink Koi (INKOI)")
    print("CURRENT verdict (latest in SUPERSEDES chain):")
    print(json.dumps(v, indent=1))

    print()
    print("=" * 72)
    print("DEMO B - verdict TIME TRAVEL (what a vector store cannot do)")
    print("=" * 72)
    for when in ("2026-11-11T13:00:00Z", "2026-11-13T00:00:00Z", now.isoformat()):
        tv = verdict_at("Ink Koi (INKOI)", when)
        print(f"Ink Koi @ {when}: [{tv['label']}] {tv['detail']}")
        print(f"    (verdict ts {tv['ts']}, provenance: {tv['provenance']})")
    print()
    for when in ("2026-11-12T06:00:00Z", now.isoformat()):
        tv = verdict_at("Floppy Agents", when)
        print(f"Floppy Agents @ {when}: [{tv['label']}] {tv['detail']}")
        print(f"    (verdict ts {tv['ts']}, provenance: {tv['provenance']})")

    print()
    print("=" * 72)
    print("DEMO C - context bundles vs preloading the ENTIRE graph catalog")
    print("=" * 72)
    full = full_catalog()
    full_bytes = bsize(full)
    metrics["full_preload_bytes"] = full_bytes
    print(f"full catalog preload: {full_bytes} bytes "
          f"({len(full['skills'])} skills, {len(full['tools'])} tools, "
          f"{len(full['entities'])} entities, {len(full['verdicts'])} verdicts incl. history)")
    for task in TASKS:
        bundle, stale = assemble_bundle(task, stale_hours=24.0, now=now)
        b = bsize(bundle)
        saved = 100.0 * (1 - b / full_bytes)
        metrics["bundles"][task] = {"bytes": b, "pct_saved": round(saved, 1),
                                    "stale_excluded": stale}
        print(f"{task:20s} bundle {b:6d} bytes | saved {saved:5.1f}% | stale excluded: {stale}")

    print()
    print("=" * 72)
    print("DEMO D - staleness guard firing (threshold tightened to 0.05h = 3 min)")
    print("=" * 72)
    bundle, stale = assemble_bundle("verify_free_mint", stale_hours=0.05, now=now)
    print(f"{stale} stale verdict(s) excluded at threshold 0.05h")
    for e in bundle["entities"][:3]:
        if "verdict_excluded" in e:
            print(f"  {e['name']}: {e['verdict_excluded']}")
    metrics["staleness_demo"] = {"threshold_hours": 0.05, "stale_excluded": stale}

    print()
    print("=" * 72)
    print("DEMO E - load sanity: 200 traversal queries (task -> skills -> tools)")
    print("=" * 72)
    lat, errors = [], 0
    t0 = time.perf_counter()
    for i in range(200):
        task = TASKS[i % len(TASKS)]
        s = time.perf_counter()
        try:
            rows(q("MATCH (t {name: $n})-[:NEEDS_SKILL]->(s)-[:USES_TOOL]->(tool) "
                   "RETURN s.name AS skill, tool.name AS tool", {"n": task}))
        except Exception:
            errors += 1
        lat.append((time.perf_counter() - s) * 1000.0)
    total = time.perf_counter() - t0
    metrics["load_test"] = {
        "queries": 200, "errors": errors, "total_s": round(total, 2),
        "avg_ms": round(sum(lat) / len(lat), 2), "max_ms": round(max(lat), 2),
        "min_ms": round(min(lat), 2)}
    print(f"200 queries in {total:.2f}s | avg {metrics['load_test']['avg_ms']} ms | "
          f"max {metrics['load_test']['max_ms']} ms | errors {errors}")

    with open(os.path.join(HERE, "metrics.json"), "w") as f:
        json.dump(metrics, f, indent=1)
    print("\nmetrics written to metrics.json")

if __name__ == "__main__":
    main()
