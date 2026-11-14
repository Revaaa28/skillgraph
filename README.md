# SkillGraph — the agent context layer on HydraDB

**Pitch.** AI agents drown in their own toolbox: every session starts by
preloading every skill, tool definition and known fact into the prompt,
whether the task needs them or not. SkillGraph stores that working memory
in HydraDB as a graph — skills, tools, MCP servers, entities and
timestamped verified facts (verdicts) — and, given a task, traverses only
the subgraph that task needs and assembles a minimal context bundle. In
our measured demo the bundle is 255–7,856 bytes against 11,113 bytes for
preloading the whole catalog (29–98% saved), every fact in it is current
by construction, and its history stays one traversal away instead of
cluttering the prompt.

Built for the **HydraDB Hackathon (Nov 14–16, 2026), Track 2 — the agent
context layer**, on the open-source HydraDB server
([hydra-db/hydradb](https://github.com/hydra-db/hydradb)), self-hosted.

## Architecture

Node classes (carried in a `kind` property; this HydraDB build keys nodes
by integer `id`): `Skill`, `Tool`, `MCPServer`, `Entity`, `Verdict`,
`TaskType`. Edges: `TaskType-[:NEEDS_SKILL]->Skill`,
`Skill-[:USES_TOOL]->Tool`, `Skill-[:ABOUT]->Entity`,
`Entity-[:HAS_VERDICT]->Verdict`, `Verdict-[:SUPERSEDES]->Verdict`,
`Tool-[:EXPOSED_VIA]->MCPServer`. Full model in `schema.md`.

A task becomes a bundle by traversal, not by search:

1. `TaskType → NEEDS_SKILL → Skill` — the capabilities this task needs.
2. `Skill → USES_TOOL → Tool` — only the tools those skills drive.
3. `Skill → ABOUT → Entity`, then for each entity its **current**
   verdict: all `HAS_VERDICT` verdicts minus the ones a newer verdict
   `SUPERSEDES` (this engine has no `NOT EXISTS`, so current-ness is two
   traversals and a set difference — the exact Cypher is in `demo.py`).
4. A staleness guard drops any current verdict older than a configurable
   threshold and says so in the bundle output, so the agent re-verifies
   instead of trusting a stale "fact".

The graph is served two ways, both proven live: the HTTP query API, and
the stock `hydradb-mcp` server over MCP stdio — an agent client
initialized, listed tools, provisioned a SkillGraph slice through
`execute_query` and ran the same multi-hop traversals back over MCP
(full raw exchange: `docs/mcp-exchange.log`). One honest adaptation: the stock
MCP server scopes queries under `<namespace>/<tenant>/<subtenant>`, so
the MCP-served slice lives in its own tenant scope and is provisioned
through the MCP tool itself; no server code was changed.

Seed data is real, not lorem ipsum: the agent's actual 12 skill
playbooks, its 7 tools, and 16 NFT-project entities whose verdicts are
the Mint RedCeh board's live on-chain checks (2026-11-14). Ink Koi
carries a 3-verdict SUPERSEDES chain from its documented board history
(free pool draining 243 → 135 → exhausted); Floppy Agents carries a
second chain whose older verdicts are explicitly marked MODELED.

## Why a graph, not a vector store

1. **"Current" is a graph property, not a similarity score.** The right
   verdict for Ink Koi today is `indikasi — free lane CLOSED`; yesterday
   it was `berpotensi — 135 free slots left`. Both texts are near-identical
   embeddings. Only the SUPERSEDES chain knows which one is in force —
   and the demo's time-travel query ("verdict at time T vs now") is a
   chain walk a vector store cannot express at all.
2. **Context assembly is multi-hop by nature.** Task → skills → tools →
   entities → current verdicts is a 4-hop traversal with exact semantics.
   Vector retrieval returns textually similar chunks, not the closure of
   what a task needs — it would happily return the bug-hunting skill for
   a mint-verification task because both mention "verification".
3. **Staleness and provenance are first-class.** Every verdict carries
   `ts` and `provenance` as data on a node, so the assembler can exclude
   facts older than a threshold and cite where each fact came from. In a
   vector store, a stale chunk and a fresh chunk are indistinguishable
   rows of text.

## Who pays, for what

Agent builders and agentic-workflow operators pay for tokens and for
wrong-context failures. SkillGraph is the context service they call
before a run: per-seat/per-call pricing for hosted traversal + bundle
assembly, sold on two measured savings — prompt tokens cut by up to ~98%
on narrow tasks, and stale-fact incidents removed by the
provenance/staleness layer. The same store doubles as the agent's audit
trail: every verdict it ever acted on, with provenance, is queryable
after the fact — something compliance-minded teams (finance, security
tooling) already budget for.

## Run it yourself

You need a running HydraDB node from the open-source server:

```sh
# 1. Build & start HydraDB (follow the upstream README for details —
#    Rust toolchain + its documented system dependencies):
git clone https://github.com/hydra-db/hydradb
cd hydradb
cargo build --locked --features server-runtime --bin graph-node
# start graph-node; it serves the HTTP query API on :8443 and writes
# its bearer token to .hydradb/auth-token

# 2. Point these scripts at your node (token is read at runtime only):
export HYDRA_TOKEN_FILE=/path/to/.hydradb/auth-token
#    …or simply: export HYDRA_TOKEN=<your node token>

# 3. Seed the graph and run the demos:
cd skillgraph
python3 seed.py     # (re)seeds the graph via the HTTP API — idempotent
python3 demo.py     # traversal, bundles, staleness guard, time-travel,
                    # 200-query load check; writes metrics.json
HYDRA_MCP_BIN=/path/to/hydradb-mcp python3 mcp_test.py
                    # stock hydradb-mcp over stdio; writes mcp-exchange.log
```

`sg.py` is the tiny HTTP client shared by the scripts. Measured numbers
from our reference run: `METRICS.md`; sample output: `demo-output.txt`;
how the reference node was built and probed: `docs/BUILD-LOG.md`.

## Repo layout

```
README.md            this file — pitch, architecture, GTM
METRICS.md           measured results of the reference run
schema.md            node/edge model
sg.py                minimal HydraDB HTTP client (env-based auth)
seed.py              graph seed: skills, tools, task types, entities
entities.json        the 16 real board entities + their verdict history
demo.py              demos: traversal, bundles, staleness, time-travel, load
demo-output.txt      captured output of the reference demo run
metrics.json         machine-readable metrics from the reference run
mcp_test.py          MCP stdio client driving the stock hydradb-mcp server
docs/mcp-exchange.log  full raw MCP exchange from the reference run
docs/BUILD-LOG.md    build/probe log of the reference deployment
LICENSE              MIT
```

## License

MIT — see `LICENSE`.
