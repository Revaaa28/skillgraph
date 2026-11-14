# SkillGraph build log (Track 2 — agent context layer, HydraDB Hackathon)
- Box: true-hare (8 vCPU / 32 GiB), repo /home/boxd/hydradb-oss @ 9166374
- graph-node: verified UP via http://127.0.0.1:9090/readyz (READY_OK) before seeding
- HTTP query API: http://127.0.0.1:8443/v1/graphs/default/query, namespace "default", cell "cell-0"
- Auth token read at runtime from /home/boxd/hydradb-oss/.hydradb/auth-token (never logged)
## MCP build started (cargo build -p hydradb-mcp) — log: skillgraph/mcp-build.log

## Cypher dialect probes (probe.py / probe2.py / probe3.py)
- FAIL first contact: CREATE of a standalone node requires an integer id;
  MATCH..CREATE..CREATE chains are rejected ("write query is not executable
  by the mutation engine"); WHERE NOT EXISTS { } does not parse; WHERE only
  supports boolean combinations of property comparisons.
- WORKS: single-statement CREATE path patterns with integer ids + props,
  bound parameters everywhere, labels in MATCH, count(*), collect(),
  ORDER BY/LIMIT, DETACH DELETE by id predicate, multi-hop patterns incl.
  reverse direction, OPTIONAL MATCH.
- GOTCHA: repeating a CREATE edge duplicates the edge (verified: 2 rows).
  seed.py therefore resets its own id ranges before creating.
- GOTCHA: count(binding) errors; use count(*).

## Seed (seed.py, ~2.1 s over HTTP)
- 12 Skills (the agent's real playbooks), 7 Tools, 2 MCPServers,
  5 TaskTypes, 16 Entities from the LIVE Mint RedCeh board
  (~/workspace/mint-redceh/app/data/board.json on the VM, autocheck
  2026-11-14 04:26 UTC) with one live verdict each.
- Ink Koi: 3-verdict SUPERSEDES chain from documented board history
  (2026-11-11 berpotensi/243 left -> 2026-11-12T18:26Z berpotensi/135 left
  -> 2026-11-14 indikasi/free lane CLOSED, live).
- Floppy Agents: current verdict live (indikasi, 3333/3333 sold out);
  2 older verdicts explicitly MODELED (provenance says so).
- Verified counts: Skill 12, Tool 7, MCPServer 2, TaskType 5, Entity 16,
  Verdict 20 | NEEDS_SKILL 12, USES_TOOL 17, ABOUT 18, HAS_VERDICT 20,
  SUPERSEDES 4, EXPOSED_VIA 2. (Probe leftovers 9001/9002/9020 deleted.)

## Demos (demo.py -> demo-output.txt, metrics.json, METRICS.md)
- A: verify_free_mint traversal -> skills [bsc_free_mint_verification,
  bsc_contract_call_construction], tools [baw, hydradb-mcp, foundry],
  Ink Koi current verdict = indikasi (free lane CLOSED).
- B: time travel - Ink Koi at 2026-11-11T13Z berpotensi (243 left),
  at 2026-11-13T00Z berpotensi (135 left), now indikasi (exhausted);
  Floppy modeled chain marked as modeled.
- C: bundles vs 11,113-byte full preload: verify_free_mint 7,856 B
  (29.3% saved), hunt_bounty 883 B (92.1%), play_agent_cards 836 B
  (92.5%), build_demo_site 373 B (96.6%), backtest_strategy 255 B (97.7%).
- D: staleness guard - at 24 h threshold 0 excluded; at 0.05 h threshold
  all 16 current verdicts excluded with STALE lines printed.
- E: load - 200 traversal queries, 3.45 s total, avg 17.27 ms,
  min 8.72 ms, max 38.29 ms, 0 errors.

## MCP build + end-to-end proof (mcp_test.py -> mcp-exchange.log)
- First build attempt died instantly: nohup could not find `cargo`
  (boxd exec shells do not put ~/.cargo/bin on PATH). Restarted with
  PATH exported: `cargo build --locked -p hydradb-mcp --bin hydradb-mcp`
  Finished in 27.30 s. Binary: target/debug/hydradb-mcp (107 MB).
- STOCK server, zero code changes. Env used: TURBOLAY_HTTP_URL=
  http://127.0.0.1:8443, GRAPH_AUTH_TOKEN_FILE=<node token file>,
  GRAPH_NAMESPACE=default, GRAPH_ID=default, GRAPH_CELL_ID=cell-0.
- Exchange (55 log lines): initialize -> serverInfo hydradb-mcp 0.1.0;
  tools/list -> [execute_query]; 10 reset deletes + 12 provisioning
  writes (TaskType/Skill/Tool/Entity/2 Verdicts + 6 edges, ids 7000-7005)
  all ok; then 3 traversals over MCP:
  * TaskType->Skill->Tool => bsc_free_mint_verification / foundry
  * Entity->HAS_VERDICT => verdicts 7004 (berpotensi) + 7005 (indikasi)
  * superseded ids => [7004] => current verdict 7005 derivable via MCP
- ADAPTATION (documented, no code change): the stock server scopes every
  query under <namespace>/<tenant>/<subtenant>, a different keyspace from
  the plain "default" namespace the HTTP seed lives in. The MCP demo
  slice is therefore provisioned THROUGH the MCP tool itself into
  tenant=skillgraph/subtenant=demo. Same schema, same dialect.

## Files
- schema.md, seed.py, demo.py, mcp_test.py, sg.py, probe*.py,
  entities.json, metrics.json, demo-output.txt, mcp-exchange.log,
  METRICS.md, README.md - all in /home/boxd/skillgraph/
