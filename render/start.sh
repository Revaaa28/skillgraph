#!/usr/bin/env bash
# SkillGraph — Render start step.
#
# Boots the real HydraDB graph-node against the bundled store snapshot,
# waits for /readyz, then serves the judge webapp (repo-root webapp.py)
# on $PORT in the foreground. The node stays on loopback; only the
# webapp is public, and the node token never leaves the process tree.
#
# Required env (set in the Render dashboard, never committed):
#   HYDRA_TOKEN   any string >= 32 chars. A FRESH token is fine — the
#                 token is node config, not stored data (verified
#                 locally against this exact store snapshot).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
RT="$ROOT/.sg-runtime"
WORK=/tmp/sg-run
mkdir -p "$WORK/store" "$WORK/cache"

# Pristine judged dataset on every boot (Render's disk is ephemeral;
# re-extracting is ~2 s and guarantees the store matches the submission).
tar --no-same-owner -xzf "$ROOT/render/runtime/store.tar.gz" -C "$WORK/store"

printf '%s' "${HYDRA_TOKEN:?HYDRA_TOKEN env var is not set in the Render dashboard}" > "$WORK/auth-token"
chmod 600 "$WORK/auth-token"

export LD_LIBRARY_PATH="$RT/lib"
export CLOUD_PROVIDER=local LOCAL_PATH="$WORK/store/store"
export GRAPH_NAMESPACE=default GRAPH_ID=default GRAPH_CELL_ID=cell-0 GRAPH_CELLS=cell-0
export GRAPH_NODE_ID=node-0
export GRAPH_DATA_CACHE_DIR="$WORK/cache" GRAPH_DATA_CACHE_BYTES=67108864
export GRAPH_AUTH_TOKEN_FILE="$WORK/auth-token"
export GRAPH_ALLOW_PLAINTEXT=true
export GRAPH_BOLT_ADDR=127.0.0.1:17687 GRAPH_ADVERTISED_BOLT_ADDR=127.0.0.1:17687
export GRAPH_BOLT_NODE_ADDRESSES=node-0=127.0.0.1:17687
export GRAPH_HTTP_ADDR=127.0.0.1:18443 GRAPH_ADMIN_ADDR=127.0.0.1:19091
export RUST_MIN_STACK=33554432 RUST_LOG=info
export GRAPH_USAGE_REPORT_ENABLED=false

# Launch through the bundled glibc 2.39 loader: the binary requires
# GLIBC_2.38 and Render's native image ships an older glibc, so the
# system loader refuses to start it ("version `GLIBC_2.38' not found").
# --library-path replaces LD_LIBRARY_PATH for this process, so it must
# list both the bundled glibc dir and the GraphBLAS dir.
"$RT/glibc/ld-linux-x86-64.so.2" --library-path "$RT/glibc:$RT/lib" "$RT/graph-node" > "$WORK/node.log" 2>&1 &
NODE_PID=$!
for i in $(seq 1 60); do
  if python3 -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:19091/readyz', timeout=2)" 2>/dev/null; then
    break
  fi
  kill -0 "$NODE_PID" 2>/dev/null || { echo "graph-node died at boot:"; tail -20 "$WORK/node.log"; exit 1; }
  sleep 1
done
python3 -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:19091/readyz', timeout=2)"
echo "graph-node ready (pid $NODE_PID)"

export SG_URL=http://127.0.0.1:18443/v1/graphs/default/query
export HYDRA_TOKEN_FILE="$WORK/auth-token"
export SG_WEB_PORT="${PORT:-8000}"
exec python3 "$ROOT/webapp.py"
