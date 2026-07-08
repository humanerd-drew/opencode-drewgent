import { tool } from "@opencode-ai/plugin"
import { getDb, countKnowledge } from "./knowledge-db"

export default tool({
  description:
    "Show statistics about stored cross-session memory. " +
    "Total entries, breakdown by type, recent activity.",
  args: {},
  execute() {
    const s = countKnowledge()
    if (s.total === 0) return "📊 Memory: empty."

    const db = getDb()
    const recent7 = (db.query(
      "SELECT COUNT(*) as c FROM knowledge WHERE created_at >= datetime('now', '-7 days')"
    ).get() as any)?.c || 0

    const topTypes = Object.entries(s.by_type)
      .sort(([, a], [, b]) => b - a)
      .map(([t, c]) => `  • ${t}: ${c}`)
      .join("\n")

    return (
      "📊 Memory Stats\n" +
      `Total entries: ${s.total}\n` +
      `Last 7 days: ${recent7}\n` +
      "By type:\n" + topTypes
    )
  },
})
