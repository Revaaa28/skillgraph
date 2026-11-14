# Narration texts. Scenes 1-7 and 9 (close) are VERBATIM from
# docs/demo-script.md (judge-audited wording — do not edit).
# Scene 8 is new (agent-consumer proof, docs/agent-consumer-transcript.md).
VO = {
 "s1": "Every agent session starts the same way: by loading everything the agent has ever learned. SkillGraph takes the opposite approach. Pull, don't preload.",
 "s2": "Here's the problem. A working agent accumulates skills, tool definitions, MCP servers, and facts about the world. Preload all of it, and every prompt carries the full catalog \u2014 in our demo, eleven thousand bytes \u2014 whether the task needs it or not. That means higher token cost, slower starts, and stale facts smuggled in as truth.",
 "s3": "SkillGraph stores that working memory in HydraDB, as a graph. When a task arrives \u2014 say, verify a free mint \u2014 the agent traverses only what the task needs: two skills, three tools, and, for the entity in question, Ink Koi, the one verdict that is currently in force.",
 "s4": "And this is no custom hackjob API. The same traversals run over MCP, through the stock HydraDB MCP server, unmodified. A client connects, lists its tools, and pulls the context over the protocol an agent would use.",
 "s5": "The result is a context bundle sized to the task. A narrow task like backtesting needs 255 bytes \u2014 a 97.7 percent saving against the full preload. Even the widest task still saves, because history and unrelated skills stay in the graph, not in the prompt.",
 "s6": "The graph also remembers. Ink Koi's free pool was draining on November 11th, nearly gone by the 13th, and closed today. Ask what the verdict was at any moment, and SkillGraph walks the supersedes chain to answer. A vector store can't do that \u2014 both texts look the same to an embedding.",
 "s7": "A loopback sanity run: two hundred traversals, zero errors, seventeen milliseconds on average \u2014 on a debug build. And a staleness guard drops any verdict that's too old, so the agent re-verifies instead of trusting yesterday's facts.",
 "s8": "The bundle is consumed, too. Same model, same question, one run each. Without it, the model admits it cannot verify the mint, and falls back to a generic checklist. With a one-thousand-sixty-six-byte bundle, it answers from the verdict: free lane closed, zero slots left \u2014 plus the checks to run before signing.",
 "s9": "SkillGraph: the context layer your agent actually needs \u2014 nothing more. Pull, don't preload.",
}
ORDER = ["s1","s2","s3","s4","s5","s6","s7","s8","s9"]
