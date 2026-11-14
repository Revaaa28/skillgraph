# SkillGraph — measured results

All numbers measured live on boxd `true-hare` (8 vCPU / 32 GiB) against the
self-hosted HydraDB node, 2026-11-14 ~04:35 UTC. Raw data: `metrics.json`,
`demo-output.txt`, `docs/mcp-exchange.log` in this repo.

## Graph size (verified counts)

| kind | count | | edge type | count |
|---|---|---|---|---|
| Skill | 12 | | NEEDS_SKILL | 12 |
| Tool | 7 | | USES_TOOL | 17 |
| MCPServer | 2 | | ABOUT | 18 |
| TaskType | 5 | | HAS_VERDICT | 20 |
| Entity | 16 | | SUPERSEDES | 4 |
| Verdict | 20 | | EXPOSED_VIA | 2 |
| **nodes** | **62** | | **edges** | **73** |

Entities and current verdicts are real: the Mint RedCeh board's live
listings (on-chain autocheck, 2026-11-14 04:26 UTC). Ink Koi's older
verdicts are its documented board history; Floppy Agents' older verdicts
are explicitly marked MODELED in their provenance.

## Context bundles vs preloading the entire catalog

Full preload = every skill, tool, MCP server, task type, entity and ALL
verdicts (history included), serialized: **11,113 bytes**.

| task type | bundle bytes | saved vs preload |
|---|---|---|
| verify_free_mint | 7,856 | 29.3% |
| hunt_bounty | 883 | 92.1% |
| play_agent_cards | 836 | 92.5% |
| build_demo_site | 373 | 96.6% |
| backtest_strategy | 255 | 97.7% |

`verify_free_mint` is the heavy bundle on purpose: its skill is ABOUT all
16 board entities, so the bundle carries all 16 current verdicts — and
still beats preload, because preload also drags in the other 10 skills,
their tools, every task type and the full verdict history.

## Traversal latency (load sanity)

200 multi-hop traversal queries (TaskType → Skill → Tool, cycling all 5
task types), sequential over HTTP from the same box:

- total 3.45 s, **avg 17.27 ms, min 8.72 ms, max 38.29 ms, errors 0**

## Staleness guard

Bundle assembly excludes current verdicts older than a configurable
threshold and reports them. At the working threshold (24 h) nothing was
excluded (board verdicts were ~9 minutes old). Tightening the threshold
to 0.05 h fired the guard on all 16 current verdicts:

```
16 stale verdict(s) excluded at threshold 0.05h
  Agent Cards: STALE: verdict from 2026-11-14T04:26:21.329Z is 0.1h old
  (threshold 0.05h) - excluded, re-verify before use
```

## MCP end-to-end (stock hydradb-mcp, no code changes)

Full raw stdio exchange in `docs/mcp-exchange.log` (55 lines): `initialize`
(serverInfo hydradb-mcp 0.1.0) → `tools/list` (`execute_query`) → 12
provisioning writes → 3 traversals, all successful:

- TaskType → Skill → Tool returned `bsc_free_mint_verification / foundry`
- Entity → HAS_VERDICT returned both Ink Koi verdicts
- superseded-id query returned 7004, so the current verdict (7005,
  `indikasi`) is derivable over MCP alone
