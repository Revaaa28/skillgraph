#!/usr/bin/env bash
# Start the SkillGraph judge demo (port 8000) next to the graph-node.
# The node token is read from the node's own token file — never copied here.
set -e
cd "$(dirname "$0")"
export HYDRA_TOKEN_FILE="${HYDRA_TOKEN_FILE:-$HOME/hydradb-oss/.hydradb/auth-token}"
nohup python3 webapp.py > webapp.log 2>&1 &
echo $! > webapp.pid
echo "webapp pid $(cat webapp.pid), log: webapp.log"
