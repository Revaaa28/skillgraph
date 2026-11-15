# SkillGraph — baseline, improvement, and the live demo

**Live demo (queries the real graph, in your browser):**
https://skillgraph.true-hare.boxd.sh — pick a task type and watch the
traversal assemble its context bundle live; pick an entity and inspect
its SUPERSEDES verdict chain. (The machine's main address,
`true-hare.boxd.sh`, shows boxd's one-click human check first; the
subdomain above is direct.) Served by `webapp.py` in this repo against
the self-hosted HydraDB node on the same machine — no cached numbers:
every figure on those pages is a live query result.

All measurements below were taken on boxd `true-hare` (8 vCPU / 32 GiB)
against the self-hosted open-source HydraDB node. Raw data:
`metrics.json`, `demo-output.txt`, `METRICS.md`.

## The baseline

**Preload everything.** The agent's whole catalog — 12 skills, 7 tools,
2 MCP servers, 5 task types, 16 entities and *all* verdicts, history
included — serialized into the prompt: **11,113 bytes** (a
current-state-only preload, without verdict history, is 10,095 B;
method in `METRICS.md`).

The byte cost is the smaller problem. A preload is a snapshot, and
snapshots go silently wrong: a catalog preloaded on 2026-11-11 would
still tell the agent that Ink Koi's free mint is *berpotensi* with
243 of 2,777 free slots left — while on-chain the free lane has been
exhausted (2,777/2,777) since 2026-11-14. Nothing in a flat preload
marks that fact as dead.

## What SkillGraph measures instead

Per task, traverse only the needed subgraph and assemble the bundle
(re-measured 2026-11-15 after a fresh re-seed; identical to the
2026-11-14 run):

| task type | bundle | vs full preload (11,113 B) |
|---|---|---|
| verify_free_mint | 7,856 B | 29.3% saved |
| hunt_bounty | 883 B | 92.1% saved |
| play_agent_cards | 836 B | 92.5% saved |
| build_demo_site | 373 B | 96.6% saved |
| backtest_strategy | 255 B | 97.7% saved |

Traversal latency, 200 sequential multi-hop queries over HTTP, same
box: avg **17.27 ms**, max 38.29 ms, **0 errors** (2026-11-14, warm).
Re-run 2026-11-15 on the just-woken machine: avg 25.84 ms and 28.02 ms
across two runs, max 75.19 ms, 0 errors.

Graph after the 2026-11-15 re-seed (verified counts): **62 nodes /
73 edges** — Skill 12, Tool 7, MCPServer 2, TaskType 5, Entity 16,
Verdict 20 · NEEDS_SKILL 12, USES_TOOL 17, ABOUT 18, HAS_VERDICT 20,
SUPERSEDES 4, EXPOSED_VIA 2.

## The continual element: the graph learns, the answer improves

Verdicts are never overwritten. Each new on-chain verification lands as
a new timestamped Verdict; a SUPERSEDES edge points it at the one it
replaces, and the *current* verdict is derived at query time — the
chain vertex nobody supersedes. One real entity, Ink Koi (INKOI),
tracked by the Mint RedCeh board's autocheck:

| when (UTC) | verdict in force | source |
|---|---|---|
| 2026-11-11 12:00 | berpotensi — 243 free slots left (2,534/2,777) | documented board history |
| 2026-11-12 18:26 | berpotensi — 135 free slots left (2,642/2,777) | documented autocheck cycle |
| 2026-11-14 04:26 | **indikasi — free lane CLOSED (2,777/2,777)** | live autocheck |
| 2026-11-15 06:26 | indikasi — refreshed (supply 2,786/5,555) | live autocheck, re-seeded same day |

The improvement over the baseline is concrete: at every moment above,
a SkillGraph bundle answered with the verdict actually in force,
while any preload taken earlier kept answering with a dead one. On
2026-11-15 the graph was re-seeded from that morning's autocheck
(board state 06:26 UTC) with no schema or code change — verdict
timestamps advanced ~26 h and the derived current answers were correct
immediately. Time-travel queries (`demo.py` Demo B) still return what
was believed on Nov 11 and Nov 12, and why it changed — the history a
flat store deletes.

A staleness guard completes the loop: bundle assembly excludes current
verdicts older than a configurable threshold and reports them. At the
working threshold (24 h) the fresh data excludes none; tightening it
to 0.05 h excludes all 16 with explicit STALE lines (re-verified
2026-11-15).
