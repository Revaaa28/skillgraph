"""End-to-end MCP proof: a minimal JSON-RPC stdio client drives the stock
hydradb-mcp server against the running graph-node.

The stock server scopes every query under <namespace>/tenant/subtenant, so
this client first provisions a compact SkillGraph slice THROUGH the MCP tool
itself (writes create the scope), then runs real traversals back over MCP.
The full raw exchange is logged to mcp-exchange.log.
"""
import json, os, queue, subprocess, sys, threading

HERE = os.path.dirname(os.path.abspath(__file__))
BIN = os.environ.get("HYDRA_MCP_BIN", "hydradb-mcp")
LOG = open(os.path.join(HERE, "mcp-exchange.log"), "w")

env = dict(os.environ)
env.update({
    "TURBOLAY_HTTP_URL": "http://127.0.0.1:8443",
    "GRAPH_AUTH_TOKEN_FILE": os.environ.get(
        "HYDRA_TOKEN_FILE", os.path.expanduser("~/.hydradb/auth-token")),
    "GRAPH_NAMESPACE": "default",
    "GRAPH_ID": "default",
    "GRAPH_CELL_ID": "cell-0",
    "RUST_MIN_STACK": "33554432",
})

proc = subprocess.Popen([BIN], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE, env=env, text=True, bufsize=1)
incoming = queue.Queue()
def pump():
    for line in proc.stdout:
        incoming.put(line.rstrip("\n"))
threading.Thread(target=pump, daemon=True).start()

_id = [0]
def send(obj):
    line = json.dumps(obj)
    LOG.write(">>> " + line + "\n"); LOG.flush()
    proc.stdin.write(line + "\n"); proc.stdin.flush()

def request(method, params=None):
    _id[0] += 1
    rid = _id[0]
    msg = {"jsonrpc": "2.0", "id": rid, "method": method}
    if params is not None:
        msg["params"] = params
    send(msg)
    while True:
        line = incoming.get(timeout=60)
        LOG.write("<<< " + line + "\n"); LOG.flush()
        try:
            obj = json.loads(line)
        except Exception:
            continue
        if obj.get("id") == rid:
            return obj

def call_query(cypher, params=None):
    args = {"query": cypher, "tenant": "skillgraph", "subtenant": "demo",
            "parameters": params or {}}
    resp = request("tools/call", {"name": "execute_query", "arguments": args})
    result = resp.get("result", {})
    texts = [c.get("text", "") for c in result.get("content", [])]
    return result.get("isError", False), "\n".join(texts)

def main():
    init = request("initialize", {
        "protocolVersion": "2024-11-05",
        "capabilities": {},
        "clientInfo": {"name": "skillgraph-mcp-test", "version": "0.1.0"}})
    print("initialize ->", json.dumps(init.get("result", {}).get("serverInfo", {})))
    send({"jsonrpc": "2.0", "method": "notifications/initialized"})

    tools = request("tools/list", {})
    names = [t["name"] for t in tools.get("result", {}).get("tools", [])]
    print("tools/list ->", names)

    # reset the demo scope slice (idempotent)
    for nid in range(7000, 7010):
        call_query("MATCH (n {id: $id}) DETACH DELETE n", {"id": nid})

    seed = [
        ("CREATE (n {id: 7000, kind: 'TaskType', name: 'verify_free_mint', description: 'Decide whether a listed free mint is really free on-chain right now'})", None),
        ("CREATE (n {id: 7001, kind: 'Skill', name: 'bsc_free_mint_verification', purpose: 'Verify a BSC free-mint claim on-chain before minting'})", None),
        ("CREATE (n {id: 7002, kind: 'Tool', name: 'foundry', toolkind: 'CLI - cast/forge EVM toolkit'})", None),
        ("CREATE (n {id: 7003, kind: 'Entity', name: 'Ink Koi (INKOI)', entkind: 'NFT - koi', ref: 'inkkoi.ink'})", None),
        ("CREATE (n {id: 7004, kind: 'Verdict', label: 'berpotensi', detail: 'First koi free; free pool nearly gone - 135 of 2,777 free slots left', ts: '2026-11-12T18:26:00Z', provenance: 'Mint RedCeh autocheck (documented)'})", None),
        ("CREATE (n {id: 7005, kind: 'Verdict', label: 'indikasi', detail: 'Free lane CLOSED - freeMinted 2,777/2,777 on-chain; paid mints 0.0004 BNB', ts: '2026-11-14T04:26:46.175Z', provenance: 'Mint RedCeh autocheck - on-chain verification, board.json'})", None),
        ("CREATE (a {id: 7000})-[:NEEDS_SKILL]->(b {id: 7001})", None),
        ("CREATE (a {id: 7001})-[:USES_TOOL]->(b {id: 7002})", None),
        ("CREATE (a {id: 7001})-[:ABOUT]->(b {id: 7003})", None),
        ("CREATE (a {id: 7003})-[:HAS_VERDICT]->(b {id: 7004})", None),
        ("CREATE (a {id: 7003})-[:HAS_VERDICT]->(b {id: 7005})", None),
        ("CREATE (a {id: 7005})-[:SUPERSEDES]->(b {id: 7004})", None),
    ]
    for cy, params in seed:
        err, text = call_query(cy, params)
        print("seed write", "ERROR" if err else "ok", "-", cy[:60])
        if err:
            print("   ", text[:300])

    print()
    print("MCP traversal 1 - TaskType -> Skill -> Tool (multi-hop):")
    err, text = call_query(
        "MATCH (t {name: 'verify_free_mint'})-[:NEEDS_SKILL]->(s)-[:USES_TOOL]->(tool) "
        "RETURN s.name AS skill, tool.name AS tool")
    print("  isError:", err); print(" ", text)

    print()
    print("MCP traversal 2 - Entity -> all verdicts:")
    err, text = call_query(
        "MATCH (e {name: 'Ink Koi (INKOI)'})-[:HAS_VERDICT]->(v) "
        "RETURN v.id AS vid, v.label AS label, v.ts AS ts")
    print("  isError:", err); print(" ", text)

    print()
    print("MCP traversal 3 - superseded verdict ids (latest = all minus these):")
    err, text = call_query(
        "MATCH (e {name: 'Ink Koi (INKOI)'})-[:HAS_VERDICT]->(old)<-[:SUPERSEDES]-(newer) "
        "RETURN old.id AS vid")
    print("  isError:", err); print(" ", text)

    proc.stdin.close()
    proc.terminate()
    LOG.close()
    print("\nfull raw exchange logged to mcp-exchange.log")

if __name__ == "__main__":
    main()
