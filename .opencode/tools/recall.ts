import { tool } from "@opencode-ai/plugin"
import { searchKnowledge } from "./knowledge-db"

export default tool({
  description:
    "Search cross-session memory using full-text search (FTS5). " +
    "Supports stemming, ranking, and multi-word queries. " +
    "Finds facts, decisions, preferences, and patterns from past sessions.",
  args: {
    query: tool.schema.string().describe("Keywords, phrases, or topics to search for"),
    limit: tool.schema.number().default(10).describe("Maximum results"),
  },
  execute(args) {
    const results = searchKnowledge(args.query, args.limit)
    if (results.length === 0) return "Nothing found in memory."
    return (
      `📚 ${results.length} result(s) for "${args.query}":\n` +
      results.map((r, i) => `${i + 1}. [${r.type}] ${r.content}`).join("\n")
    )
  },
})
