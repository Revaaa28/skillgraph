#!/usr/bin/env bash
# SkillGraph — Render build step.
#
# Unpacks the prebuilt HydraDB runtime committed under render/runtime/:
#   graph-node.gz              the OSS graph-node binary (hydra-db/hydradb
#                              @ 9166374, v0.4.0), built on Ubuntu 24.04 and
#                              stripped: 667,644,112 B -> 74,607,272 B,
#                              gzipped to ~20 MB for git.
#   libgraphblas.so.7.4.0.gz   Ubuntu noble's SuiteSparse GraphBLAS 7.4.0,
#                              the binary's only non-system library. Raw it
#                              is 182,795,592 B (over GitHub's 100 MB file
#                              limit), gzipped it is ~72 MB.
# Output goes to .sg-runtime/ at the repo root (gitignored, regenerated
# on every build).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
RT="$ROOT/.sg-runtime"
mkdir -p "$RT/lib"
gzip -dc "$ROOT/render/runtime/graph-node.gz" > "$RT/graph-node"
chmod +x "$RT/graph-node"
gzip -dc "$ROOT/render/runtime/libgraphblas.so.7.4.0.gz" > "$RT/lib/libgraphblas.so.7.4.0"
ln -sf libgraphblas.so.7.4.0 "$RT/lib/libgraphblas.so.7"
ls -la "$RT" "$RT/lib"
echo "skillgraph build ok"
