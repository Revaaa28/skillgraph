"""Seed the SkillGraph into HydraDB via the HTTP query API.

Engine dialect notes (probed live, see BUILD-LOG.md):
- nodes are created with an integer `id` property; class is carried in `kind`
- CREATE of an existing edge DUPLICATES it -> this script resets its own id
  ranges first (DETACH DELETE per id), so every run seeds exactly once
- all string values go through bound parameters
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sg import q, rows
HERE = os.path.dirname(os.path.abspath(__file__))

SKILLS = [
    # id, name, purpose
    (100, "bsc_free_mint_verification", "Verify a BSC free-mint claim on-chain before minting: contract, price, supply, transfer rules"),
    (101, "bsc_contract_call_construction", "Build BSC contract calls in code and verify every decoded field before broadcast"),
    (102, "agentic_bug_hunter", "Bug-bounty master workflow: impact-first hunting, A-to-B chaining, 7-question reporting gate"),
    (103, "agent_cards", "Play Agent Cards: daily quests, wheel spins, ladder and season-pool strategy"),
    (104, "binance_agentic_wallet", "Operate the Binance Agentic Wallet via baw: balances, market orders, sends under strict safety rails"),
    (105, "boltbook_pod_collab", "Play Boltbook Pod collab rounds end to end within the user's current scope"),
    (106, "hack_skills", "Yaklang hack-skills router: web/API security, auth, business logic, race conditions"),
    (107, "siwe", "Sign-In with Ethereum (EIP-4361): implementation patterns and security pitfalls"),
    (108, "mitmproxy", "Intercept, inspect and replay HTTP traffic with mitmproxy for API testing"),
    (109, "playwright_cli", "Browser automation with playwright-cli for recon and replay harnesses"),
    (110, "designing_beautiful_websites", "Design clear, distinctive, production-grade web interfaces"),
    (111, "backtesting_trading_strategies", "Backtest trading strategies on historical data before risking capital"),
]
TOOLS = [
    (200, "baw", "CLI - Binance Agentic Wallet"),
    (201, "kart", "CLI - Agent Cards game client"),
    (202, "boxd", "CLI - cloud VM control (builds, heavy jobs)"),
    (203, "browser", "Browser automation / page reading"),
    (204, "hydradb-mcp", "MCP server - HydraDB Cypher over MCP stdio"),
    (205, "git", "CLI - version control"),
    (206, "foundry", "CLI - cast/forge EVM toolkit"),
]
MCPS = [
    (300, "hydradb-mcp", "stdio"),
    (301, "playwright-mcp", "stdio"),
]
TASKS = [
    (400, "verify_free_mint", "Decide whether a listed free mint is really free on-chain right now"),
    (401, "hunt_bounty", "Hunt a bug-bounty target on the installed playbooks, impact-first"),
    (402, "play_agent_cards", "Run the daily Agent Cards routine: quests, wheel, ladder push"),
    (403, "build_demo_site", "Design and build a demo web page and verify it in a browser"),
    (404, "backtest_strategy", "Backtest a trading strategy and report the results"),
]
USES_TOOL = {
    100: [206, 200, 204], 101: [206], 102: [203, 205], 103: [201, 200],
    104: [200], 105: [203], 106: [203], 107: [206, 205], 108: [203],
    109: [203], 110: [203], 111: [205],
}
NEEDS_SKILL = {
    400: [100, 101], 401: [102, 106, 108, 109, 107],
    402: [103, 104], 403: [110, 109], 404: [111],
}
EXPOSED_VIA = {204: 300, 203: 301}

PROV_LIVE = "Mint RedCeh autocheck - on-chain verification, board.json (BSC chain 56)"

def main():
    entities = json.load(open(os.path.join(HERE, "entities.json")))
    ent_id = {e["id"]: 500 + i for i, e in enumerate(entities)}

    # ---- reset our id ranges (idempotent reseed; edges duplicate on CREATE)
    ranges = list(range(100, 112)) + list(range(200, 207)) + list(range(300, 302)) \
        + list(range(400, 405)) + list(range(500, 500 + len(entities))) + list(range(600, 700))
    for nid in ranges:
        q("MATCH (n {id: $id}) DETACH DELETE n", {"id": nid})

    # ---- nodes
    for nid, name, purpose in SKILLS:
        q("CREATE (n {id: $id, kind: 'Skill', name: $name, purpose: $purpose})",
          {"id": nid, "name": name, "purpose": purpose})
    for nid, name, kind in TOOLS:
        q("CREATE (n {id: $id, kind: 'Tool', name: $name, toolkind: $tk})",
          {"id": nid, "name": name, "tk": kind})
    for nid, name, transport in MCPS:
        q("CREATE (n {id: $id, kind: 'MCPServer', name: $name, transport: $tr})",
          {"id": nid, "name": name, "tr": transport})
    for nid, name, desc in TASKS:
        q("CREATE (n {id: $id, kind: 'TaskType', name: $name, description: $d})",
          {"id": nid, "name": name, "d": desc})
    for e in entities:
        ref = e.get("contract") or e.get("site") or ""
        q("CREATE (n {id: $id, kind: 'Entity', name: $name, entkind: $ek, ref: $ref})",
          {"id": ent_id[e["id"]], "name": e["name"], "ek": e.get("kind", ""), "ref": ref})

    # ---- verdicts: one live verdict per entity
    vid = 600
    verdict_of = {}
    for e in entities:
        sup = ""
        if e.get("supplyNow"):
            sup = f" | supply {e['supplyNow']}/{e.get('supplyMax') or '?'} on-chain"
        detail = f"{e['headline']} | {e['mintPrice']}{sup}"
        q("CREATE (n {id: $id, kind: 'Verdict', label: $label, detail: $detail, ts: $ts, provenance: $prov})",
          {"id": vid, "label": e["bucket"], "detail": detail,
           "ts": e["checkedAt"], "prov": PROV_LIVE})
        q("CREATE (a {id: $a})-[:HAS_VERDICT]->(b {id: $b})", {"a": ent_id[e["id"]], "b": vid})
        verdict_of[e["id"]] = vid
        vid += 1

    # ---- Ink Koi: REAL verdict history (documented Mint RedCeh board record)
    ink = ent_id["ink-koi"]
    ink_hist = [
        (620, "berpotensi",
         "First koi free for Agent ID holders | free pool draining - 243 of 2,777 free slots left (freeMinted 2,534/2,777)",
         "2026-11-11T12:00:00Z",
         "Mint RedCeh board history (documented on-chain checks, 2026-11-11)"),
        (621, "berpotensi",
         "First koi free for Agent ID holders | free pool nearly gone - 135 of 2,777 free slots left (freeMinted 2,642/2,777)",
         "2026-11-12T18:26:00Z",
         "Mint RedCeh autocheck on-chain check, 2026-11-13 02:26 WITA cycle (documented)"),
    ]
    for v_id, label, detail, ts, prov in ink_hist:
        q("CREATE (n {id: $id, kind: 'Verdict', label: $label, detail: $detail, ts: $ts, provenance: $prov})",
          {"id": v_id, "label": label, "detail": detail, "ts": ts, "prov": prov})
        q("CREATE (a {id: $a})-[:HAS_VERDICT]->(b {id: $b})", {"a": ink, "b": v_id})
    cur_ink = verdict_of["ink-koi"]
    q("CREATE (a {id: $a})-[:SUPERSEDES]->(b {id: $b})", {"a": cur_ink, "b": 621})
    q("CREATE (a {id: $a})-[:SUPERSEDES]->(b {id: $b})", {"a": 621, "b": 620})

    # ---- Floppy Agents: MODELED history (marked) + live current verdict
    flo = ent_id["floppy-agents"]
    flo_hist = [
        (630, "real",
         "MODELED: free mint open for .ai Agent ID holders, 1 per wallet, supply filling",
         "2026-11-12T00:00:00Z",
         "MODELED history - pattern after the documented Ink Koi case; NOT live data"),
        (631, "indikasi",
         "MODELED: supply at the 3,333 cap approaching; free window effectively closing",
         "2026-11-13T12:00:00Z",
         "MODELED history - pattern after the documented Ink Koi case; NOT live data"),
    ]
    for v_id, label, detail, ts, prov in flo_hist:
        q("CREATE (n {id: $id, kind: 'Verdict', label: $label, detail: $detail, ts: $ts, provenance: $prov})",
          {"id": v_id, "label": label, "detail": detail, "ts": ts, "prov": prov})
        q("CREATE (a {id: $a})-[:HAS_VERDICT]->(b {id: $b})", {"a": flo, "b": v_id})
    cur_flo = verdict_of["floppy-agents"]
    q("CREATE (a {id: $a})-[:SUPERSEDES]->(b {id: $b})", {"a": cur_flo, "b": 631})
    q("CREATE (a {id: $a})-[:SUPERSEDES]->(b {id: $b})", {"a": 631, "b": 630})

    # ---- edges
    for task, skills in NEEDS_SKILL.items():
        for s in skills:
            q("CREATE (a {id: $a})-[:NEEDS_SKILL]->(b {id: $b})", {"a": task, "b": s})
    for s, tools in USES_TOOL.items():
        for t in tools:
            q("CREATE (a {id: $a})-[:USES_TOOL]->(b {id: $b})", {"a": s, "b": t})
    for t, m in EXPOSED_VIA.items():
        q("CREATE (a {id: $a})-[:EXPOSED_VIA]->(b {id: $b})", {"a": t, "b": m})
    # ABOUT: the mint-verification skills operate on every board entity;
    # contract-construction + agent_cards are about the Agent Cards contract
    for e in entities:
        q("CREATE (a {id: $a})-[:ABOUT]->(b {id: $b})", {"a": 100, "b": ent_id[e["id"]]})
    ac = ent_id["agent-cards"]
    q("CREATE (a {id: $a})-[:ABOUT]->(b {id: $b})", {"a": 101, "b": ac})
    q("CREATE (a {id: $a})-[:ABOUT]->(b {id: $b})", {"a": 103, "b": ac})

    print("seed complete")

if __name__ == "__main__":
    main()
