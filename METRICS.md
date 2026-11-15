# SkillGraph — measured results

All numbers measured live on boxd `true-hare` (8 vCPU / 32 GiB) against the
self-hosted HydraDB node, 2026-11-14 ~04:35 UTC. Raw data: `metrics.json`,
`demo-output.txt`, `docs/mcp-exchange.log` in this repo.

**Re-verified 2026-11-15** after a fresh re-seed from that morning's
Mint RedCeh autocheck (board state 2026-11-15T06:26 UTC): graph counts
identical (62 nodes / 73 edges), full preload identical (11,113 B),
bundle sizes identical for all 5 task types, staleness demo identical
(16 excluded at 0.05 h). Load re-runs on the just-woken machine: 200
traversals, avg 25.84 ms and 28.02 ms, max 75.19 ms, 0 errors.
`metrics.json` and `demo-output.txt` now hold the 2026-11-15 run;
baseline-vs-improvement summary in `RESULTS.md`.

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

## Context bundles vs two preload baselines

Preload is the right baseline for the failure mode this targets —
sessions that inject the whole registry; the vs-vector-store argument
is separate and lives in the README.

Two ways to preload this catalog (33 items), both serialized with
`demo.py`'s serializer:

- **Full preload** — every skill, tool, MCP server, task type, entity
  and ALL verdicts (history included): **11,113 bytes**
- **Current-state preload** — the same catalog carrying only the
  verdicts currently in force (16 of 20; the 4 superseded verdicts,
  ids 620/621/630/631, dropped): **10,095 bytes**

| task type | bundle bytes | saved vs full preload | saved vs current-state preload |
|---|---|---|---|
| verify_free_mint | 7,856 | 29.3% | 22.2% |
| hunt_bounty | 883 | 92.1% | 91.3% |
| play_agent_cards | 836 | 92.5% | 91.7% |
| build_demo_site | 373 | 96.6% | 96.3% |
| backtest_strategy | 255 | 97.7% | 97.5% |

(The current-state baseline was computed with the same code path:
`full_catalog()` minus the SUPERSEDES targets — the set `demo.py`
already derives per entity — and the bundle bytes re-verified against
this table.)

`verify_free_mint` is the heavy bundle on purpose: its skill is ABOUT all
16 board entities, so the bundle carries all 16 current verdicts — and
still beats both preloads, because preload also drags in the other 10
skills, their tools and every task type.

## Traversal latency (loopback sanity check, debug build)

Client and server on the same box (8 vCPU / 32 GiB), sequential,
against the 62-node reference graph, server running a debug build.
Read these as engine-overhead numbers, not networked production
latency; no concurrency is claimed for this run.

200 multi-hop traversal queries (TaskType → Skill → Tool, cycling all 5
task types), sequential over HTTP from the same box:

- total 3.45 s, **avg 17.27 ms, min 8.72 ms, max 38.29 ms, errors 0**

## Scale & concurrency (synthetic)

The graph above is real data and small by design. For the "holds up under
load" criterion, `scale_gen.py` generated a **synthetic** graph in the same
schema shape — **5,000 nodes** (40 TaskType / 300 Skill / 240 Tool /
60 MCPServer / 1,800 Entity / 2,560 Verdict) and **10,000 edges**
(200 NEEDS_SKILL / 1,050 USES_TOOL / 5,190 ABOUT / 2,560 HAS_VERDICT /
760 SUPERSEDES / 240 EXPOSED_VIA; 760 entities carry 2-verdict SUPERSEDES
chains) — with deterministic wiring (seed 20261114). It was loaded into a
separate id range (ids ≥ 1,000,000, names prefixed `synth_`) alongside the
real graph, measured, then deleted; afterwards the real graph was
re-verified at exactly 62 nodes / 73 edges and `demo.py` re-ran clean
(bundle sizes byte-identical to the section above).

Method, honestly: every measurement is an HTTP query issued from the same
box (true-hare, 8 vCPU / 32 GiB) to the node on localhost, against
synthetic wiring — these numbers measure the engine and the traversal
shape at scale, not real-world data patterns.

Sequential, 200 runs each, store holding 5,062 nodes / 10,073 edges:

- TaskType → Skill → Tool: **avg 52.66 ms, min 43.97 ms, max 72.53 ms,
  errors 0**
- Entity → latest Verdict (two traversals + set difference): **avg
  23.31 ms, min 17.00 ms, max 55.23 ms, errors 0** — and every run
  returned the correct current verdict, checked against the generator's
  wiring

Concurrent load — 8 parallel clients × 125 traversals (alternating the
two shapes), 1,000 ops total:

- **wall 5.07 s (~197 ops/s), avg op latency 38.7 ms, max 95.83 ms,
  errors 0, wrong results 0**

## Staleness guard (behavior at two thresholds)

Bundle assembly excludes current verdicts older than a configurable
threshold and reports them. At the production threshold (24 h) nothing
was excluded — the board data was 9 minutes old. The 0.05 h run below
exists to show the exclusion output shape, not to simulate a real
staleness event. Tightening the threshold to 0.05 h fired the guard on
all 16 current verdicts:

```
16 stale verdict(s) excluded at threshold 0.05h
  Agent Cards: STALE: verdict from 2026-11-14T04:26:21.329Z is 0.1h old
  (threshold 0.05h) - excluded, re-verify before use
```

## MCP end-to-end (stock hydradb-mcp, no code changes)

Full raw stdio exchange in `docs/mcp-exchange.log` (55 lines),
run against a 6-node slice (ids 7000–7005) in the MCP server's
tenant keyspace — see the scope note in README.md: `initialize`
(serverInfo hydradb-mcp 0.1.0) → `tools/list` (`execute_query`) → 12
provisioning writes → 3 traversals, all successful:

- TaskType → Skill → Tool returned `bsc_free_mint_verification / foundry`
- Entity → HAS_VERDICT returned both Ink Koi verdicts
- superseded-id query returned 7004, so the current verdict (7005,
  `indikasi`) is derivable over MCP alone
