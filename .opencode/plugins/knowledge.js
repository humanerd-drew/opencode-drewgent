import { tool } from "@opencode-ai/plugin"
import { spawnSync } from "node:child_process"

const PROJECT = process.env.PROJECT_HOME || process.cwd()
const PY = "python3"

function py(args) {
  const proc = spawnSync(PY, args, { cwd: PROJECT, maxBuffer: 10 * 1024 * 1024 })
  if (proc.error) return `error: ${proc.error.message}`
  if (proc.status !== 0) return `error: ${proc.stderr.toString().trim()}`
  return proc.stdout.toString().trim()
}

export const KnowledgePlugin = async () => {
  return {
    tool: {
      recall: tool({
        description: "Search cross-session memory using semantic + FTS5 search.",
        args: {
          query: tool.schema.string().describe("Search query"),
          limit: tool.schema.number().default(5).describe("Max results"),
        },
        async execute(args) {
          return py(["scripts/recall.py", args.query, "--limit", String(args.limit), "--json"])
        },
      }),

      remember: tool({
        description: "Store a fact, decision, preference, or pattern into knowledge.db with embedding.",
        args: {
          fact: tool.schema.string().describe("The knowledge to store"),
          type: tool.schema.string().default("fact").describe("Type: fact, decision, preference, pattern"),
        },
        async execute(args) {
          return py(["scripts/ingest_fact.py", "--json", JSON.stringify({ fact: args.fact, type: args.type })])
        },
      }),

      "memory-stats": tool({
        description: "Show statistics about the knowledge database.",
        args: {},
        async execute() {
          return py(["-c", `
import sqlite3, json
db = sqlite3.connect("${PROJECT}/.opencode/knowledge.db")
tables = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
result = {}
if "knowledge" in tables:
    rows = db.execute("SELECT type, COUNT(*) FROM knowledge GROUP BY type").fetchall()
    result["total"] = db.execute("SELECT COUNT(*) FROM knowledge").fetchone()[0]
    result["by_type"] = dict(rows)
if "embeddings" in tables:
    result["embeddings"] = db.execute("SELECT COUNT(*) FROM embeddings").fetchone()[0]
if "entities" in tables:
    result["entities"] = db.execute("SELECT COUNT(*) FROM entities").fetchone()[0]
    result["relations"] = db.execute("SELECT COUNT(*) FROM relations").fetchone()[0]
print(json.dumps(result, ensure_ascii=False))
`])
        },
      }),

      "entity-add": tool({
        description: "Add an entity to the ontology layer.",
        args: {
          label: tool.schema.string().describe("Entity display name"),
          type: tool.schema.string().describe("Entity type"),
          properties: tool.schema.string().default("{}").describe("JSON properties"),
        },
        async execute(args) {
          return py(["scripts/ontology_setup.py", "add-entity", args.label, args.type, args.properties])
        },
      }),

      "relation-add": tool({
        description: "Add a relation between two entities.",
        args: {
          source: tool.schema.number().describe("Source entity ID"),
          target: tool.schema.number().describe("Target entity ID"),
          type: tool.schema.string().describe("Relation type"),
          properties: tool.schema.string().default("{}").describe("JSON properties"),
        },
        async execute(args) {
          return py(["scripts/ontology_setup.py", "add-relation", String(args.source), String(args.target), args.type, args.properties])
        },
      }),

      "entity-query": tool({
        description: "Search entities by label, type, or both.",
        args: {
          label: tool.schema.string().default("").describe("Label search pattern"),
          type: tool.schema.string().default("").describe("Entity type filter"),
          limit: tool.schema.number().default(20).describe("Max results"),
        },
        async execute(args) {
          return py(["scripts/ontology_setup.py", "query", args.label || "", args.type || "", String(args.limit)])
        },
      }),

      "entity-traverse": tool({
        description: "Traverse relations from an entity (recursive).",
        args: {
          id: tool.schema.number().describe("Entity ID to start from"),
          relation: tool.schema.string().default("").describe("Relation type filter (optional)"),
          direction: tool.schema.string().default("out").describe("out or in"),
          depth: tool.schema.number().default(3).describe("Max traversal depth"),
        },
        async execute(args) {
          return py(["scripts/ontology_setup.py", "traverse", String(args.id), args.relation, args.direction, String(args.depth)])
        },
      }),

      "graph-explore": tool({
        description: "Explore entities related to a query.",
        args: {
          query: tool.schema.string().describe("Entity name or keyword to search"),
          depth: tool.schema.number().default(2).describe("Traversal depth"),
        },
        async execute(args) {
          return py(["scripts/graph_query.py", "--mode", "explore", "--depth", String(args.depth), "--json", args.query])
        },
      }),

      "graph-trace": tool({
        description: "Trace entity connections bidirectionally.",
        args: {
          query: tool.schema.string().describe("Entity name to trace from"),
          depth: tool.schema.number().default(3).describe("Traversal depth"),
        },
        async execute(args) {
          return py(["scripts/graph_query.py", "--mode", "trace", "--depth", String(args.depth), "--json", args.query])
        },
      }),

      "graph-rca": tool({
        description: "Generate RCA (Root Cause Analysis) report for an incident or pattern.",
        args: {
          query: tool.schema.string().describe("Incident or pattern to analyze"),
          depth: tool.schema.number().default(3).describe("Traversal depth"),
        },
        async execute(args) {
          return py(["scripts/rca_report.py", "--depth", String(args.depth), args.query])
        },
      }),
    },
  }
}
