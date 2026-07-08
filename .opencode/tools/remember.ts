import { tool } from "@opencode-ai/plugin"
import { addKnowledge, countKnowledge } from "./knowledge-db"

export default tool({
  description:
    "Store a fact, decision, preference, or pattern into cross-session memory. " +
    "Saved knowledge is FTS5-indexed and searchable via recall().",
  args: {
    fact: tool.schema.string().describe("The knowledge to remember"),
    type: tool.schema
      .enum(["fact", "decision", "preference", "pattern"])
      .default("fact")
      .describe("Type of knowledge"),
  },
  execute(args) {
    addKnowledge(args.type, args.fact)
    const total = countKnowledge().total
    return `✓ Saved (${args.type}). Total: ${total} entries.`
  },
})
