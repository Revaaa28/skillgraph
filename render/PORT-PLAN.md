# SkillGraph → Render port plan

Goal: run the same judge demo that now serves from boxd
(`https://skillgraph.true-hare.boxd.sh`) on Render's free tier, so the
boxd machine can go back to sleep. The boxd setup is untouched and
remains the fallback until every check below passes on Render.

Everything in this folder was proven end-to-end on a local VM first
(Ubuntu 24.04, glibc 2.39 — same lineage as both boxd and Render):
the copied binary opened the copied store, `/readyz` answered, and
the demo reproduced the exact judged numbers (see "Verification").

## What ships, and why it looks like this

| Artifact | Raw size | In repo | Notes |
|---|---|---|---|
| graph-node binary | 667,644,112 B debug build | `render/runtime/graph-node.gz` — 20,354,425 B | Stripped to 74,607,272 B (debug info was ~89% of the file), then gzipped. Stripped binary re-verified: boots, serves, identical query results. |
| libgraphblas.so.7.4.0 | 182,795,592 B | `render/runtime/libgraphblas.so.7.4.0.gz` — 72,066,709 B | The binary's ONLY non-system dependency (its other libs — libgomp, libgcc_s, libm, libc — are in every Ubuntu image). Raw .so exceeds GitHub's 100 MB/file limit, hence the .gz. Ubuntu noble package, already stripped upstream. |
| HydraDB store | 79 MB / 18,777 files | `render/runtime/store.tar.gz` — 3,512,217 B | Tarball of the box's `.hydradb/store` taken 2026-11-15 ~14:06 WITA (board state 2026-11-15T06:26Z). Compresses 22× because the SST files are mostly empty space. Extracted fresh on every boot by `start.sh`. |

Total added to the repo: ~96 MB across 3 files, each under GitHub's
100 MB single-file limit. No Git LFS, no external artifact host.

Provenance: binary built on boxd from the official OSS repo
`hydra-db/hydradb` @ `9166374` (v0.4.0) with
`cargo build --locked --features server-runtime --bin graph-node`;
LAGraph 1.0.2 was linked statically, libcypher is the crate's own
ANTLR parser — neither appears in `ldd`. The webapp is the repo's
current `webapp.py` (sha256 `e118e71a…`, the redesigned judge UI from
commits `ea77099` + `900f6b4`, including the `/graph.json` endpoint) —
`start.sh` runs it straight from the repo root, nothing is copied or
patched for Render.

## Dashboard steps (parent)

1. **Publish the branch.** This package sits on the local branch
   `render-port` (unpushed). Either push that branch and deploy from
   it, or merge it into `main` first. For blueprint auto-detect, also
   copy `render/render.yaml` to the repo root as `./render.yaml`.
   (Manual creation below works without the blueprint.)
2. **Create the service.** Render dashboard → *New* → *Web Service* →
   connect `Revaaa28/skillgraph` → pick the branch from step 1.
   - Runtime / Environment: **Python 3**
   - Region: **Singapore**
   - Instance type: **Free**
   - Build Command: `bash render/build.sh`
   - Start Command: `bash render/start.sh`
   - Health Check Path: `/healthz`
3. **Set one env var.** `HYDRA_TOKEN` = any random string of 32+
   characters (generate one on the spot). It does NOT need to be the
   box node's token — the token is node config read from a file at
   boot, not data stored in the graph; a fresh token was verified
   against this exact store snapshot. Never commit it anywhere.
4. **Deploy** and watch the logs: expect `skillgraph build ok`, then
   `graph-node ready (pid …)`, then the webapp listening on the
   assigned `$PORT`.
5. **Verify** (next section). Only after all five checks pass, swap
   the judge-facing link from the boxd URL to the Render URL
   (`https://skillgraph.onrender.com` or the assigned subdomain).

## Verification checklist (post-deploy)

- [ ] `GET /healthz` → `ok`
- [ ] Home page loads with live counts from the real node
      (62 nodes / 73 edges; per-kind counts 12 Skill, 7 Tool,
      2 MCPServer, 5 TaskType, 16 Entity, 20 Verdict)
- [ ] `GET /bundle?task=verify_free_mint` → bundle **7,856 B**, 29.3%
      smaller than the 11,113 B full-catalog preload
- [ ] `GET /bundle?task=backtest_strategy` → bundle **255 B**, 97.7%
- [ ] `GET /chain?entity=Ink Koi (INKOI)` → SUPERSEDES chain derives
      the current verdict **indikasi** (free lane closed, refreshed
      2026-11-15). Note the exact entity name includes the ticker;
      plain `Ink Koi` returns "not found".
- [ ] `GET /graph.json` → returns the graph as JSON (redesign endpoint)

These are the same numbers the box serves today; anything else means
the deploy is not equivalent and boxd stays the judge link.

## Known risks / behaviours

- **RAM (main risk).** Free tier = 512 MB. Measured on boxd:
  graph-node RSS ~294 MB, webapp ~25 MB. `start.sh` caps the node's
  data cache at 64 MB. Expected to fit; if Render OOM-kills the
  service it will crash-loop in the logs — in that case abandon the
  port and keep boxd (sleep-wake) as the judge host.
- **Cold starts.** Free services sleep after ~15 min idle. First hit
  then costs Render's spin-up (~30–60 s) + store extract (~2 s) +
  node boot (~5 s). If Rev wants it warm during judging, point the
  existing keep-warm ping pattern at the Render URL.
- **Ephemeral disk.** Every restart re-extracts the pristine bundled
  store (by design — the demo is read-only for judges; any writes a
  traversal might make do not persist, same as a fresh seed).
- **Node exposure.** graph-node binds loopback only; Bolt/HTTP/admin
  ports are not published. Only the webapp faces the internet, and it
  only runs its fixed query set.
- **Telemetry.** The node's anonymous usage reporting is disabled in
  `start.sh` (`GRAPH_USAGE_REPORT_ENABLED=false`).
