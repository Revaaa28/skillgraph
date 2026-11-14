# SkillGraph schema

HydraDB as the live context store for an AI agent. Instead of preloading every
skill, tool and entity into the prompt, the agent traverses only the subgraph a
task needs and assembles a minimal context bundle.

## Nodes
- (:Skill   {name, purpose})                    — a reusable agent capability (SKILL.md playbooks)
- (:Tool    {name, kind})                       — a CLI / API the agent can call
- (:MCPServer {name, transport})                — an MCP endpoint exposing tools
- (:Entity  {name, kind, ref})                  — a project / contract / wallet the agent knows about
- (:Verdict {label, detail, ts, provenance})    — a timestamped verified fact about an entity
- (:TaskType {name, description})               — a class of task the agent can be given

## Edges
- (TaskType)-[:NEEDS_SKILL]->(Skill)           — skills required to attempt the task
- (Skill)-[:USES_TOOL]->(Tool)                 — tools a skill drives
- (Skill)-[:ABOUT]->(Entity)                   — entities a skill operates on
- (Entity)-[:HAS_VERDICT]->(Verdict)           — fact history of an entity
- (Verdict)-[:SUPERSEDES]->(Verdict)           — newer verdict -> the verdict it replaces
- (Tool)-[:EXPOSED_VIA]->(MCPServer)           — tool reachable through an MCP server

## Current-verdict rule
The current verdict of an entity is the HAS_VERDICT target that no other
verdict supersedes. This engine build has no `NOT EXISTS`, so the rule is
computed as a set difference of two queries (this is exactly what
`demo.py` runs):

    -- all verdicts of the entity
    MATCH (e {name: $name})-[:HAS_VERDICT]->(v)
    RETURN v.id AS vid, v.label AS label, v.detail AS detail, v.ts AS ts,
           v.provenance AS provenance

    -- verdicts that have been superseded
    MATCH (e {name: $name})-[:HAS_VERDICT]->(old)<-[:SUPERSEDES]-(newer)
    RETURN old.id AS vid

    -- current verdict = first set minus second set

## Context bundle for a task
    MATCH (t:TaskType {name: $task})-[:NEEDS_SKILL]->(s:Skill)
    OPTIONAL MATCH (s)-[:USES_TOOL]->(tool:Tool)
    OPTIONAL MATCH (s)-[:ABOUT]->(e:Entity)
    ... plus each entity's current verdict only (history stays in the graph,
    out of the prompt).

## Engine dialect notes (probed live against this build, 2026-11-14)
- Nodes are created with an integer `id` property; the class is carried in
  the `kind` property (labels also work in MATCH, but `id`+`kind` is the
  portable form here).
- CREATE of an edge that already exists DUPLICATES it - seed scripts must
  reset their id ranges first (seed.py does DETACH DELETE per id).
- No `NOT EXISTS { }` subqueries and WHERE only compares properties, so
  "current verdict" = HAS_VERDICT set minus SUPERSEDES targets (two
  traversals + set difference, see demo.py).
- RETURN projects properties only (`var.prop` or count(*)); no whole-node
  returns, no count(binding).
