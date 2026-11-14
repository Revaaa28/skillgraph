# SkillGraph — demo video script

Format: ~2.5 min, 1920×1080. Terminal scenes are rendered from the real
captured output of `demo.py` / `mcp_test.py` running against the live
self-hosted HydraDB node on boxd `true-hare` (the same runs whose output
is committed as `demo-output.txt` and `docs/mcp-exchange.log`). Narration:
TTS, voice Helio (`avocado_v2:MAI_03`), exported separately as
`docs/demo-narration.mp3`.

**v2 — animated rebuild.** The shipped `docs/demo.mp4` is the animated
version: a deterministic HTML deck rendered frame-by-frame (the NEAR
demo-v4 recipe), with kinetic type, counting numbers, a graph that
builds itself, and the real captured output carried as framed terminal
inserts inside the animated scenes. Narration was regenerated per scene
with the same voice and the same text (Scenes 1–7, 9), plus one added
scene (Scene 8, the agent-consumer proof). Build sources and recipe:
`tools/video/` (`gen_vo.py` → `build.py` → `render.mjs` →
`assemble.py`).

## Scene 1 — Title (card)

On screen: **SkillGraph** — *Pull, don't preload.* The agent context
layer on HydraDB.

> Every agent session starts the same way: by loading everything the
> agent has ever learned. SkillGraph takes the opposite approach. Pull,
> don't preload.

## Scene 2 — The problem (card)

On screen: Preload everything = **11,113 bytes** — 12 skills · 7 tools ·
16 entities · 20 verdicts — into every prompt, needed or not.

> Here's the problem. A working agent accumulates skills, tool
> definitions, MCP servers, and facts about the world. Preload all of
> it, and every prompt carries the full catalog — in our demo, eleven
> thousand bytes — whether the task needs it or not. That means higher
> token cost, slower starts, and stale facts smuggled in as truth.

## Scene 3 — A task arrives (terminal: `demo.py`, Demo A)

On screen: real traversal output — task `verify_free_mint` pulls skills
`bsc_free_mint_verification` + `bsc_contract_call_construction`, tools
`baw`, `hydradb-mcp`, `foundry`, and Ink Koi's current verdict:
`indikasi` — free lane CLOSED, freeMinted 2,777/2,777 on-chain.

> SkillGraph stores that working memory in HydraDB, as a graph. When a
> task arrives — say, verify a free mint — the agent traverses only what
> the task needs: two skills, three tools, and, for the entity in
> question, Ink Koi, the one verdict that is currently in force.

## Scene 4 — Over MCP, stock server (terminal: `mcp_test.py`)

On screen: real MCP client output — `initialize` → hydradb-mcp 0.1.0,
`tools/list` → `execute_query`, seed writes ok, multi-hop traversal
returning `bsc_free_mint_verification` / `foundry`.

> And this is no custom hackjob API. The same traversals run over MCP,
> through the stock HydraDB MCP server, unmodified. A client
> connects, lists its tools, and pulls the context over the protocol
> an agent would use.

## Scene 5 — Bundles vs preload (terminal: `demo.py`, Demo C)

On screen: real bundle table — full catalog preload 11,113 bytes;
bundles 7,856 / 883 / 836 / 373 / 255 bytes (29.3%–97.7% saved).

> The result is a context bundle sized to the task. A narrow task like
> backtesting needs 255 bytes — a 97.7 percent saving against the full
> preload. Even the widest task still saves, because history and
> unrelated skills stay in the graph, not in the prompt.

## Scene 6 — Verdict time-travel (terminal: `demo.py`, Demo B)

On screen: Ink Koi at three timestamps — 2026-11-11 `berpotensi`
(243 of 2,777 free slots left) → 2026-11-13 `berpotensi` (135 left) →
today `indikasi` (free lane CLOSED).

> The graph also remembers. Ink Koi's free pool was draining on
> November 11th, nearly gone by the 13th, and closed today. Ask what
> the verdict was at any moment, and SkillGraph walks the supersedes
> chain to answer. A vector store can't do that — both texts look the
> same to an embedding.

## Scene 7 — Load + staleness (card)

On screen: "Loopback sanity run" — 200 traversal queries — **0
errors · avg 17.27 ms · max 38.29 ms** (measured, debug build,
`METRICS.md`). Staleness guard: verdicts past their threshold are
excluded, with the reason printed.

> A loopback sanity run: two hundred traversals, zero errors,
> seventeen milliseconds on average — on a debug build. And a
> staleness guard drops any verdict that's too old, so the agent
> re-verifies instead of trusting yesterday's facts.

## Scene 8 — The bundle, consumed (animated split comparison)

On screen: the question asked of gemini-3.5-flash-lite, verbatim. Left
pane (no bundle): Run A's answer types in — "I do not have access to
real-time blockchain data, so I cannot verify …" — falls back to a
generic safety checklist. Right pane (with the bundle, 1,066 B): "No —
the free lane is CLOSED." · 0 slots left (2,777 / 2,777 claimed
on-chain) · paid lane 0.0004 BNB, max 5 per wallet · contract
0xbd4b…200a9, cited from the bundle itself · pre-signing checks from
the bundle's own skills. Footer: verbatim answers in
`docs/agent-consumer-transcript.md` — the bundle buys provenance and
freshness, not IQ.

> The bundle is consumed, too. Same model, same question, one run
> each. Without it, the model admits it cannot verify the mint, and
> falls back to a generic checklist. With a one-thousand-sixty-six-byte
> bundle, it answers from the verdict: free lane closed, zero slots
> left — plus the checks to run before signing.

## Scene 9 — Close (card)

On screen: **Pull, don't preload.** — github.com/Revaaa28/skillgraph ·
Built on HydraDB · HydraDB Hackathon 2026, Track 2.

> SkillGraph: the context layer your agent actually needs — nothing
> more. Pull, don't preload.
