# Model Routing

## Default

| Role | Model |
|------|-------|
| Main session | opencode-go/deepseek-v4-flash |
| Complex review | opencode-go/deepseek-v4-pro |
| Planning | qwen3.7-max |
| Internal tasks | groq openai/gpt-oss-20b ($0) |

## Agent Profiles

| Profile | Default Model | Note |
|---------|--------------|------|
| implementer | flash | task(subagent_type="general") |
| reviewer | pro | Code review |
| planner | max | Architecture planning |
| explorer | flash | Codebase discovery |
