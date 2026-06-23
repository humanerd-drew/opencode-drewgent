import { tool } from "@opencode-ai/plugin"

const PROFILE_MODELS: Record<string, string> = {
  explorer: "opencode-go/deepseek-v4-flash",
  implementer: "opencode-go/kimi-k2.7-code",
  tester: "opencode-go/deepseek-v4-flash",
  reviewer: "opencode-go/deepseek-v4-pro",
  "reviewer-critical": "opencode-go/qwen3.7-plus",
  "security-reviewer": "opencode-go/minimax-m3",
  planner: "opencode-go/qwen3.7-max",
  orchestrator: "opencode-go/qwen3.7-max",
  designer: "opencode-go/deepseek-v4-flash",
  sre: "opencode-go/deepseek-v4-flash",
  analyst: "opencode-go/deepseek-v4-flash",
  "content-manager": "opencode-go/deepseek-v4-pro",
  editor: "opencode-go/glm-5.2",
  archiver: "opencode-go/deepseek-v4-flash",
}

const AGENTS = Object.keys(PROFILE_MODELS)

export default tool({
  description: "Delegate to subagent with its assigned model. Spawns a new session so the subagent uses its profile model (e.g. kimi-k2.7-code for implementer). Returns the subagent's full response. Use this when you need the subagent's specific model instead of inheriting the parent model.",
  args: {
    name: tool.schema.enum(AGENTS).describe("Subagent profile name"),
    prompt: tool.schema.string().describe("Full task for the subagent. Include file paths, context, and expected output format."),
  },
  async execute(args, context) {
    const model = PROFILE_MODELS[args.name]
    const serverUrl = `http://localhost:8642`
    const result = await Bun.$`opencode run --agent ${args.name} --model ${model} --attach ${serverUrl} ${args.prompt}`.text()
    return result.trim()
  },
})
