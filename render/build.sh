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
#   glibc/                     Ubuntu noble glibc 2.39 (from the libc6,
#                              libgomp1 and libgcc-s1 .debs): the loader
#                              plus every libc-family library the binary
#                              and GraphBLAS need. The binary requires
#                              GLIBC_2.38 but Render's native image ships
#                              an older glibc, so start.sh launches the
#                              node through this bundled loader with an
#                              explicit --library-path. ~2.2 MB in git.
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
mkdir -p "$RT/glibc"
cp "$ROOT/render/runtime/glibc/"* "$RT/glibc/"
gzip -dc "$RT/glibc/libc.so.6.gz" > "$RT/glibc/libc.so.6"
gzip -dc "$RT/glibc/libm.so.6.gz" > "$RT/glibc/libm.so.6"
rm "$RT/glibc/libc.so.6.gz" "$RT/glibc/libm.so.6.gz"
chmod +x "$RT/glibc/ld-linux-x86-64.so.2"
ls -la "$RT" "$RT/lib" "$RT/glibc"
echo "skillgraph build ok"
