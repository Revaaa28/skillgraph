"""SkillGraph HydraDB HTTP client (runs next to a self-hosted graph-node).

Auth: set HYDRA_TOKEN to your node's bearer token, or HYDRA_TOKEN_FILE to a
file containing it (default ~/.hydradb/auth-token, the node's own token file).
The token is only ever read at runtime — it is never stored in this repo.
"""
import json, os, urllib.request

TOKEN_FILE = os.environ.get(
    "HYDRA_TOKEN_FILE",
    os.environ.get("SG_TOKEN_FILE", os.path.expanduser("~/.hydradb/auth-token")))
URL = os.environ.get("SG_URL", "http://127.0.0.1:8443/v1/graphs/default/query")
NS = os.environ.get("SG_NS", "default")

def _token():
    tok = os.environ.get("HYDRA_TOKEN")
    if tok:
        return tok.strip()
    with open(TOKEN_FILE) as f:
        return f.read().strip()

def q(cypher, params=None):
    body = {"cell_id": "cell-0", "query": cypher}
    if params:
        body["parameters"] = params
    req = urllib.request.Request(
        URL,
        data=json.dumps(body).encode(),
        headers={
            "Authorization": "Bearer " + _token(),
            "X-Graph-Namespace": NS,
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())

def val(v):
    """Unwrap HydraDB typed values ({type, value}) to plain Python values."""
    if isinstance(v, dict) and "value" in v and "type" in v:
        return v["value"]
    return v

def rows(resp):
    cols = resp.get("columns", [])
    return [dict(zip(cols, [val(c) for c in row])) for row in resp.get("rows", [])]

def one(resp):
    rs = rows(resp)
    return rs[0] if rs else None
