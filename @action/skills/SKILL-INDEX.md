---
title: Skill Index
type: skill
space: outcome
tags: [outcome]
created: 2026-05-10
updated: 2026-05-20
links:
  - "[[@identity/brain/rules]]"
  - "[[@action/gateway/drewgent-architecture-dataflow]]"
  - "[[@action/skills/agent-architecture/brain-signal-system/SKILL]]"
  - "[[@action/skills/agent-architecture/self-replicating-agent-tdd/SKILL]]"
  - "[[@action/skills/agent-protocol/goose-acp-integration/SKILL]]"
  - "[[@action/skills/apple/DESCRIPTION]]"
  - "[[@action/skills/autonomous-ai-agents/DESCRIPTION]]"
  - "[[@action/skills/brain-broken-link-fix/SKILL]]"
  - "[[@action/skills/brain-dashboard-system/SKILL]]"
  - "[[@action/skills/brain/DESCRIPTION]]"
  - "[[@action/skills/brain/harvester-memory-sync/SKILL]]"
  - "[[@action/skills/creative/DESCRIPTION]]"
  - "[[@action/skills/data-science/DESCRIPTION]]"
  - "[[@action/skills/devops/tool-integration-protocol/SKILL]]"
  - "[[@action/skills/devtools/DESCRIPTION]]"
  - "[[@action/skills/diagramming/DESCRIPTION]]"
  - "[[@action/skills/docs/DESCRIPTION]]"
  - "[[@action/skills/domain/DESCRIPTION]]"
  - "[[@action/skills/email/DESCRIPTION]]"
  - "[[@action/skills/feeds/DESCRIPTION]]"
  - "[[@memory/knowledge/NEURONFS_RULES]]"---


# Skill Index - Hugh Kim's Skills → Drewgent P3-sensors

## Category Mapping

| Hugh Category | Drewgent P3-sensors | Description |
|---------------|---------------------|-------------|
| QA | `skills/qa/` | Contract-first QA, scenario generation, functional testing |
| SECURITY | `skills/security/` | Vulnerability scanning, pentest checklists |
| DEV TOOLS | `skills/dev-tools/` | Code generation, git management, deployment |
| MEMORY | `skills/memory/` | Agent memory, context window management |
| DOCS | `skills/docs/` | Documentation generation, changelog |

## Hugh's Skill List → Drewgent Mapping

### QA Skills
| Hugh Skill | Drewgent Path | Status |
|------------|--------------|--------|
| qa-scenario-gen | `skills/qa/qa-scenario-gen/` | TODO |
| qa-cycle | `skills/qa/qa-cycle/` | TODO |
| qa-functional | `skills/qa/qa-functional/` | TODO |

### SECURITY Skills
| Hugh Skill | Drewgent Path | Status |
|------------|--------------|--------|
| security-best-practices | `skills/security/security-best-practices/` | TODO |
| vulnerability-scanner | `skills/security/vulnerability-scanner/` | TODO |
| pentest-checklist | `skills/security/pentest-checklist/` | TODO |

### DEV TOOLS Skills
| Hugh Skill | Drewgent Path | Status |
|------------|--------------|--------|
| git-commit | `skills/dev-tools/git-commit/` | TODO |
| dependency-updater | `skills/dev-tools/dependency-updater/` | TODO |
| changelog-gen | `skills/dev-tools/changelog-gen/` | TODO |

### MEMORY Skills
| Hugh Skill | Drewgent Path | Status |
|------------|--------------|--------|
| memory | `skills/memory/memory/` | Existing |
| remember-this | `skills/memory/remember-this/` | TODO |
| agent-memory | `skills/memory/agent-memory/` | TODO |
| context-window | `skills/memory/context-window/` | TODO |

### DOCS Skills
| Hugh Skill | Drewgent Path | Status |
|------------|--------------|--------|
| init-project | `skills/docs/init-project/` | TODO |
| prompt-engineering | `skills/docs/prompt-engineering/` | Existing |
| skill-creation | `skills/docs/skill-creation/` | TODO |

## Implementation Status

- [x] QA Evidence Manager (Phase 2) - `P2-hippocampus/qa-evidence/`
- [x] QA Skills directory created
- [ ] qa-scenario-gen skill
- [ ] qa-cycle skill
- [ ] qa-functional skill
- [ ] security-best-practices skill
- [ ] vulnerability-scanner skill
- [ ] pentest-checklist skill
- [x] memory/memory skill (verify existing)
- [x] harvester-memory-sync skill — `skills/brain/harvester-memory-sync/SKILL.md`
- [ ] remember-this skill
- [ ] init-project skill

## Category Reference

Each skill category directory contains a `DESCRIPTION.md` that describes the category's scope.

| Category | Description |
|----------|-------------|
| [[@action/skills/qa/DESCRIPTION]] | QA — Contract-first QA, scenario generation, functional testing |
| [[@action/skills/security/DESCRIPTION]] | SECURITY — Vulnerability scanning, pentest checklists |
| [[@action/skills/devtools/DESCRIPTION]] | DEV TOOLS — Code generation, git management, deployment |
| [[@action/skills/memory/DESCRIPTION]] | MEMORY — Agent memory, context window management |
| [[@action/skills/docs/DESCRIPTION]] | DOCS — Documentation generation, changelog |
| [[@action/skills/apple/DESCRIPTION]] | Apple/macOS — iMessage, Reminders, Notes, FindMy, automation |
| [[@action/skills/autonomous-ai-agents/DESCRIPTION]] | Autonomous AI Agents — Spawning and orchestrating autonomous agents |
| [[@action/skills/brain/DESCRIPTION]] | Brain — Drewgent brain signal system, governance, self-improvement |
| [[@action/skills/creative/DESCRIPTION]] | Creative — ASCII art, hand-drawn diagrams, Excalidraw, animation |
| [[@action/skills/data-science/DESCRIPTION]] | Data Science — Jupyter, data analysis, visualization |
| [[@action/skills/diagramming/DESCRIPTION]] | Diagramming — Excalidraw, technical diagrams |
| [[@action/skills/domain/DESCRIPTION]] | Domain — Academic research, paper discovery, market data |
| [[@action/skills/email/DESCRIPTION]] | Email — IMAP/SMTP via himalaya CLI |
| [[@action/skills/feeds/DESCRIPTION]] | Feeds — RSS/Atom monitoring, blog watching |
| [[@action/skills/gaming/DESCRIPTION]] | Gaming — Minecraft, Pokemon server automation |
| [[@action/skills/gifs/DESCRIPTION]] | GIFs — Tenor search, GIF generation |
| [[@action/skills/github/DESCRIPTION]] | GitHub — PR workflow, issues, repo management |
| [[@action/skills/inference-sh/DESCRIPTION]] | Inference.sh — GPU cloud for ML workloads |
| [[@action/skills/mcp/DESCRIPTION]] | MCP — Model Context Protocol servers and tools |
| [[@action/skills/media/DESCRIPTION]] | Media — YouTube, music generation, audio visualization |
| [[@action/skills/mlops/DESCRIPTION]] | MLOps — Training, fine-tuning, deployment |
| [[@action/skills/productivity/DESCRIPTION]] | Productivity — Documents, presentations, spreadsheets |
| [[skills/productivity/manyfast/SKILL]] | Manyfast — Product planning MCP integration, PRD/Features to kanban pipeline |

| [[@action/skills/research/DESCRIPTION]] | Research — Academic, RSS, literature review |
| [[@action/skills/smart-home/DESCRIPTION]] | Smart Home — Philips Hue, home automation |
| [[@action/skills/social-media/DESCRIPTION]] | Social Media — X/Twitter, posting and monitoring |
| [[@action/skills/software-development/DESCRIPTION]] | Software Development — TDD, debugging, code review |
| [[@action/skills/trend-harvester/DESCRIPTION]] | Trend Harvester — AI trend collection and analysis |

## Notes

- Hugh's skills are primarily slash commands in Claude Code
- Drewgent's skills are stored in `~/.drewgent/skills/` or `P3-sensors/skills/`
- Skills with `/` prefix in Hugh (e.g., `/team`, `/branch`) are Commands, not Skills
- Integration: QA Evidence Manager can be called by qa-* skills

## Auto Graph Index
- [[@action/skills/agent-architecture/brain-signal-system/SKILL]]
- [[@action/skills/agent-architecture/self-replicating-agent-tdd/SKILL]]
- [[@action/skills/agent-protocol/goose-acp-integration/SKILL]]
- [[@action/skills/apple/DESCRIPTION]]
- [[@action/skills/autonomous-ai-agents/DESCRIPTION]]
- [[@action/skills/brain-broken-link-fix/SKILL]]
- [[@action/skills/brain-dashboard-system/SKILL]]
- [[@action/skills/brain/harvester-memory-sync/SKILL]]
- [[@action/skills/creative/DESCRIPTION]]
- [[@action/skills/data-science/DESCRIPTION]]
- [[@action/skills/devops/tool-integration-protocol/SKILL]]
- [[@action/skills/diagramming/DESCRIPTION]]
- [[@action/skills/domain/DESCRIPTION]]
- [[@action/skills/email/DESCRIPTION]]
- [[@action/skills/feeds/DESCRIPTION]]
- [[@action/skills/gaming/DESCRIPTION]]
- [[@action/skills/gifs/DESCRIPTION]]
- [[@action/skills/github/DESCRIPTION]]
- [[@action/skills/harsh-critic/SKILL]]
- [[@action/skills/inference-sh/DESCRIPTION]]

- [[@action/skills/mcp/DESCRIPTION]]
- [[@action/skills/media/DESCRIPTION]]
- [[@action/skills/mlops/DESCRIPTION]]
- [[@action/skills/mlops/cloud/DESCRIPTION]]
- [[@action/skills/mlops/evaluation/DESCRIPTION]]
- [[@action/skills/mlops/inference/DESCRIPTION]]
- [[@action/skills/mlops/models/DESCRIPTION]]
- [[@action/skills/mlops/research/DESCRIPTION]]
- [[@action/skills/mlops/training/DESCRIPTION]]
- [[@action/skills/mlops/vector-databases/DESCRIPTION]]
- [[@action/skills/note-taking/DESCRIPTION]]
- [[@action/skills/productivity/DESCRIPTION]]
- [[@action/skills/productivity/ocr-and-documents/DESCRIPTION]]
- [[@action/skills/qa/qa-cycle/SKILL]]
- [[@action/skills/qa/qa-scenario-gen/SKILL]]
- [[@action/skills/research/DESCRIPTION]]
- [[@action/skills/semble-research/SKILL]]
- [[@action/skills/session-pattern-archiver/SKILL]]
- [[@action/skills/skill-gym/SKILL]]
- [[@action/skills/smart-home/DESCRIPTION]]
- [[@action/skills/social-media/DESCRIPTION]]
- [[@action/skills/trend-harvester/SKILL]]
- [[skills/apple/DESCRIPTION]]
- [[skills/apple/apple-notes/SKILL]]
- [[skills/apple/apple-reminders/SKILL]]
- [[skills/apple/findmy/SKILL]]
- [[skills/apple/imessage/SKILL]]
- [[skills/autonomous-ai-agents/DESCRIPTION]]
- [[skills/autonomous-ai-agents/claude-code/SKILL]]
- [[skills/autonomous-ai-agents/codex/SKILL]]
- [[skills/autonomous-ai-agents/drewgent-agent/SKILL]]
- [[skills/autonomous-ai-agents/drewgent-update-checker/SKILL]]
- [[skills/autonomous-ai-agents/opencode/SKILL]]
- [[skills/brain/pass-zero-secret-store/SKILL]]
- [[skills/creative/DESCRIPTION]]
- [[skills/creative/ascii-art/SKILL]]
- [[skills/creative/ascii-video/README]]
- [[skills/creative/ascii-video/SKILL]]
- [[skills/creative/ascii-video/references/architecture]]
- [[skills/creative/ascii-video/references/composition]]
- [[skills/creative/ascii-video/references/effects]]
- [[skills/creative/ascii-video/references/inputs]]
- [[skills/creative/ascii-video/references/optimization]]
- [[skills/creative/ascii-video/references/scenes]]
- [[skills/creative/ascii-video/references/shaders]]
- [[skills/creative/ascii-video/references/troubleshooting]]
- [[skills/creative/excalidraw/SKILL]]
- [[skills/creative/excalidraw/references/colors]]
- [[skills/creative/excalidraw/references/dark-mode]]
- [[skills/creative/excalidraw/references/examples]]
- [[skills/creative/manim-video/README]]
- [[skills/creative/manim-video/SKILL]]
- [[skills/creative/manim-video/references/animation-design-thinking]]
- [[skills/creative/manim-video/references/animations]]
- [[skills/creative/manim-video/references/camera-and-3d]]
- [[skills/creative/manim-video/references/decorations]]
- [[skills/creative/manim-video/references/equations]]
- [[skills/creative/manim-video/references/graphs-and-data]]
- [[skills/creative/manim-video/references/mobjects]]
- [[skills/creative/manim-video/references/paper-explainer]]
- [[skills/creative/manim-video/references/production-quality]]
- [[skills/creative/manim-video/references/rendering]]
- [[skills/creative/manim-video/references/scene-planning]]
- [[skills/creative/manim-video/references/troubleshooting]]
- [[skills/creative/manim-video/references/updaters-and-trackers]]
- [[skills/creative/manim-video/references/visual-design]]
- [[skills/creative/p5js/README]]
- [[skills/creative/p5js/SKILL]]
- [[skills/creative/p5js/references/animation]]
- [[skills/creative/p5js/references/color-systems]]
- [[skills/creative/p5js/references/core-api]]
- [[skills/creative/p5js/references/export-pipeline]]
- [[skills/creative/p5js/references/interaction]]
- [[skills/creative/p5js/references/shapes-and-geometry]]
- [[skills/creative/p5js/references/troubleshooting]]
- [[skills/creative/p5js/references/typography]]
- [[skills/creative/p5js/references/visual-effects]]
- [[skills/creative/p5js/references/webgl-and-3d]]
- [[skills/creative/popular-web-designs/SKILL]]
- [[skills/creative/popular-web-designs/templates/airbnb]]
- [[skills/creative/popular-web-designs/templates/airtable]]
- [[skills/creative/popular-web-designs/templates/apple]]
- [[skills/creative/popular-web-designs/templates/bmw]]
- [[skills/creative/popular-web-designs/templates/cal]]
- [[skills/creative/popular-web-designs/templates/claude]]
- [[skills/creative/popular-web-designs/templates/clay]]
- [[skills/creative/popular-web-designs/templates/clickhouse]]
- [[skills/creative/popular-web-designs/templates/cohere]]
- [[skills/creative/popular-web-designs/templates/coinbase]]
- [[skills/creative/popular-web-designs/templates/composio]]
- [[skills/creative/popular-web-designs/templates/cursor]]
- [[skills/creative/popular-web-designs/templates/elevenlabs]]
- [[skills/creative/popular-web-designs/templates/expo]]
- [[skills/creative/popular-web-designs/templates/figma]]
- [[skills/creative/popular-web-designs/templates/framer]]
- [[skills/creative/popular-web-designs/templates/hashicorp]]
- [[skills/creative/popular-web-designs/templates/ibm]]
- [[skills/creative/popular-web-designs/templates/intercom]]
- [[skills/creative/popular-web-designs/templates/kraken]]
- [[skills/creative/popular-web-designs/templates/linear.app]]
- [[skills/creative/popular-web-designs/templates/lovable]]
- [[skills/creative/popular-web-designs/templates/minimax]]
- [[skills/creative/popular-web-designs/templates/mintlify]]
- [[skills/creative/popular-web-designs/templates/miro]]
- [[skills/creative/popular-web-designs/templates/mistral.ai]]
- [[skills/creative/popular-web-designs/templates/mongodb]]
- [[skills/creative/popular-web-designs/templates/notion]]
- [[skills/creative/popular-web-designs/templates/nvidia]]
- [[skills/creative/popular-web-designs/templates/ollama]]
- [[skills/creative/popular-web-designs/templates/opencode.ai]]
- [[skills/creative/popular-web-designs/templates/pinterest]]
- [[skills/creative/popular-web-designs/templates/posthog]]
- [[skills/creative/popular-web-designs/templates/raycast]]
- [[skills/creative/popular-web-designs/templates/replicate]]
- [[skills/creative/popular-web-designs/templates/resend]]
- [[skills/creative/popular-web-designs/templates/revolut]]
- [[skills/creative/popular-web-designs/templates/runwayml]]
- [[skills/creative/popular-web-designs/templates/sanity]]
- [[skills/creative/popular-web-designs/templates/sentry]]
- [[skills/creative/popular-web-designs/templates/spacex]]
- [[skills/creative/popular-web-designs/templates/spotify]]
- [[skills/creative/popular-web-designs/templates/stripe]]
- [[skills/creative/popular-web-designs/templates/supabase]]
- [[skills/creative/popular-web-designs/templates/superhuman]]
- [[skills/creative/popular-web-designs/templates/together.ai]]
- [[skills/creative/popular-web-designs/templates/uber]]
- [[skills/creative/popular-web-designs/templates/vercel]]
- [[skills/creative/popular-web-designs/templates/voltagent]]
- [[skills/creative/popular-web-designs/templates/warp]]
- [[skills/creative/popular-web-designs/templates/webflow]]
- [[skills/creative/popular-web-designs/templates/wise]]
- [[skills/creative/popular-web-designs/templates/x.ai]]
- [[skills/creative/popular-web-designs/templates/zapier]]
- [[skills/creative/songwriting-and-ai-music/SKILL]]
- [[skills/data-science/DESCRIPTION]]
- [[skills/data-science/jupyter-live-kernel/SKILL]]
- [[skills/devops/webhook-subscriptions/SKILL]]
- [[skills/diagramming/DESCRIPTION]]
- [[skills/dogfood/SKILL]]
- [[skills/dogfood/references/issue-taxonomy]]
- [[skills/dogfood/templates/dogfood-report-template]]
- [[skills/domain/DESCRIPTION]]
- [[skills/email/DESCRIPTION]]
- [[skills/email/himalaya/SKILL]]
- [[skills/email/himalaya/references/configuration]]
- [[skills/email/himalaya/references/message-composition]]
- [[skills/feeds/DESCRIPTION]]
- [[skills/gaming/DESCRIPTION]]
- [[skills/gaming/minecraft-modpack-server/SKILL]]
- [[skills/gaming/pokemon-player/SKILL]]
- [[skills/gifs/DESCRIPTION]]
- [[skills/github/DESCRIPTION]]
- [[skills/github/codebase-inspection/SKILL]]
- [[skills/github/github-auth/SKILL]]
- [[skills/github/github-code-review/SKILL]]
- [[skills/github/github-code-review/references/review-output-template]]
- [[skills/github/github-issues/SKILL]]
- [[skills/github/github-issues/templates/bug-report]]
- [[skills/github/github-issues/templates/feature-request]]
- [[skills/github/github-pr-workflow/SKILL]]
- [[skills/github/github-pr-workflow/references/ci-troubleshooting]]
- [[skills/github/github-pr-workflow/references/conventional-commits]]
- [[skills/github/github-pr-workflow/templates/pr-body-bugfix]]
- [[skills/github/github-pr-workflow/templates/pr-body-feature]]
- [[skills/github/github-repo-management/SKILL]]
- [[skills/github/github-repo-management/references/github-api-cheatsheet]]
- [[skills/humanerd-site/SKILL]]
- [[skills/seo-audit/SKILL]]
- [[skills/inference-sh/DESCRIPTION]]
- [[skills/leisure/find-nearby/SKILL]]
- [[skills/mcp/DESCRIPTION]]
- [[skills/mcp/mcporter/SKILL]]
- [[skills/mcp/native-mcp/SKILL]]
- [[skills/media/DESCRIPTION]]
- [[skills/media/gif-search/SKILL]]
- [[skills/media/heartmula/SKILL]]
- [[skills/media/songsee/SKILL]]
- [[skills/media/youtube-content/SKILL]]
- [[skills/media/youtube-content/references/output-formats]]
- [[skills/mlops/DESCRIPTION]]
- [[skills/mlops/cloud/DESCRIPTION]]
- [[skills/mlops/cloud/modal/SKILL]]
- [[skills/mlops/cloud/modal/references/advanced-usage]]
- [[skills/mlops/cloud/modal/references/troubleshooting]]
- [[skills/mlops/evaluation/DESCRIPTION]]
- [[skills/mlops/evaluation/lm-evaluation-harness/SKILL]]
- [[skills/mlops/evaluation/lm-evaluation-harness/references/api-evaluation]]
- [[skills/mlops/evaluation/lm-evaluation-harness/references/benchmark-guide]]
- [[skills/mlops/evaluation/lm-evaluation-harness/references/custom-tasks]]
- [[skills/mlops/evaluation/lm-evaluation-harness/references/distributed-eval]]
- [[skills/mlops/evaluation/weights-and-biases/SKILL]]
- [[skills/mlops/evaluation/weights-and-biases/references/artifacts]]
- [[skills/mlops/evaluation/weights-and-biases/references/integrations]]
- [[skills/mlops/evaluation/weights-and-biases/references/sweeps]]
- [[skills/mlops/huggingface-hub/SKILL]]
- [[skills/mlops/inference/DESCRIPTION]]
- [[skills/mlops/inference/gguf/SKILL]]
- [[skills/mlops/inference/gguf/references/advanced-usage]]
- [[skills/mlops/inference/gguf/references/troubleshooting]]
- [[skills/mlops/inference/guidance/SKILL]]
- [[skills/mlops/inference/guidance/references/backends]]
- [[skills/mlops/inference/guidance/references/constraints]]
- [[skills/mlops/inference/guidance/references/examples]]
- [[skills/mlops/inference/llama-cpp/SKILL]]
- [[skills/mlops/inference/llama-cpp/references/optimization]]
- [[skills/mlops/inference/llama-cpp/references/quantization]]
- [[skills/mlops/inference/llama-cpp/references/server]]
- [[skills/mlops/inference/obliteratus/SKILL]]
- [[skills/mlops/inference/obliteratus/references/analysis-modules]]
- [[skills/mlops/inference/obliteratus/references/methods-guide]]
- [[skills/mlops/inference/outlines/SKILL]]
- [[skills/mlops/inference/outlines/references/backends]]
- [[skills/mlops/inference/outlines/references/examples]]
- [[skills/mlops/inference/outlines/references/json_generation]]
- [[skills/mlops/inference/vllm/SKILL]]
- [[skills/mlops/inference/vllm/references/optimization]]
- [[skills/mlops/inference/vllm/references/quantization]]
- [[skills/mlops/inference/vllm/references/server-deployment]]
- [[skills/mlops/inference/vllm/references/troubleshooting]]
- [[skills/mlops/models/DESCRIPTION]]
- [[skills/mlops/models/audiocraft/SKILL]]
- [[skills/mlops/models/audiocraft/references/advanced-usage]]
- [[skills/mlops/models/audiocraft/references/troubleshooting]]
- [[skills/mlops/models/clip/SKILL]]
- [[skills/mlops/models/clip/references/applications]]
- [[skills/mlops/models/segment-anything/SKILL]]
- [[skills/mlops/models/segment-anything/references/advanced-usage]]
- [[skills/mlops/models/segment-anything/references/troubleshooting]]
- [[skills/mlops/models/stable-diffusion/SKILL]]
- [[skills/mlops/models/stable-diffusion/references/advanced-usage]]
- [[skills/mlops/models/stable-diffusion/references/troubleshooting]]
- [[skills/mlops/models/whisper/SKILL]]
- [[skills/mlops/models/whisper/references/languages]]
- [[skills/mlops/research/DESCRIPTION]]
- [[skills/mlops/research/dspy/SKILL]]
- [[skills/mlops/research/dspy/references/examples]]
- [[skills/mlops/research/dspy/references/modules]]
- [[skills/mlops/research/dspy/references/optimizers]]
- [[skills/mlops/training/DESCRIPTION]]
- [[skills/mlops/training/axolotl/SKILL]]
- [[skills/mlops/training/axolotl/references/api]]
- [[skills/mlops/training/axolotl/references/dataset-formats]]
- [[skills/mlops/training/axolotl/references/index]]
- [[skills/mlops/training/axolotl/references/other]]
- [[skills/mlops/training/grpo-rl-training/README]]
- [[skills/mlops/training/grpo-rl-training/SKILL]]
- [[skills/mlops/training/peft/SKILL]]
- [[skills/mlops/training/peft/references/advanced-usage]]
- [[skills/mlops/training/peft/references/troubleshooting]]
- [[skills/mlops/training/pytorch-fsdp/SKILL]]
- [[skills/mlops/training/pytorch-fsdp/references/index]]
- [[skills/mlops/training/pytorch-fsdp/references/other]]
- [[skills/mlops/training/trl-fine-tuning/SKILL]]
- [[skills/mlops/training/trl-fine-tuning/references/dpo-variants]]
- [[skills/mlops/training/trl-fine-tuning/references/online-rl]]
- [[skills/mlops/training/trl-fine-tuning/references/reward-modeling]]
- [[skills/mlops/training/trl-fine-tuning/references/sft-training]]
- [[skills/mlops/training/unsloth/SKILL]]
- [[skills/mlops/training/unsloth/references/index]]
- [[skills/mlops/training/unsloth/references/llms-full]]
- [[skills/mlops/training/unsloth/references/llms-txt]]
- [[skills/mlops/training/unsloth/references/llms]]
- [[skills/mlops/vector-databases/DESCRIPTION]]
- [[skills/neuron-fs-brain/SKILL]]
- [[skills/neuronfs-governance-defaults/SKILL]]
- [[skills/neuronfs-subsumption-ordering/SKILL]]
- [[skills/note-taking/DESCRIPTION]]
- [[skills/note-taking/obsidian/SKILL]]
- [[skills/obsidian-markdown/SKILL]]
- [[skills/obsidian-cli/SKILL]]
- [[skills/productivity/DESCRIPTION]]
- [[skills/productivity/google-workspace/SKILL]]
- [[skills/productivity/google-workspace/references/gmail-search-syntax]]
- [[skills/productivity/nano-pdf/SKILL]]
- [[skills/productivity/notion/SKILL]]
- [[skills/productivity/notion/references/block-types]]
- [[skills/productivity/ocr-and-documents/DESCRIPTION]]
- [[skills/productivity/ocr-and-documents/SKILL]]
- [[skills/productivity/powerpoint/SKILL]]
- [[skills/productivity/powerpoint/editing]]
- [[skills/productivity/powerpoint/pptxgenjs]]

- [[skills/research/DESCRIPTION]]
- [[skills/research/arxiv/SKILL]]
- [[skills/research/blogwatcher/SKILL]]
- [[skills/research/llm-wiki/SKILL]]
- [[skills/research/polymarket/SKILL]]
- [[skills/research/polymarket/references/api-endpoints]]
- [[skills/research/research-paper-writing/SKILL]]
- [[skills/research/research-paper-writing/references/autoreason-methodology]]
- [[skills/research/research-paper-writing/references/checklists]]
- [[skills/research/research-paper-writing/references/citation-workflow]]
- [[skills/research/research-paper-writing/references/experiment-patterns]]
- [[skills/research/research-paper-writing/references/human-evaluation]]
- [[skills/research/research-paper-writing/references/paper-types]]
- [[skills/research/research-paper-writing/references/reviewer-guidelines]]
- [[skills/research/research-paper-writing/references/sources]]
- [[skills/research/research-paper-writing/references/writing-guide]]
- [[skills/research/research-paper-writing/templates/README]]
- [[skills/research/research-paper-writing/templates/aaai2026/README]]
- [[skills/research/research-paper-writing/templates/acl/README]]
- [[skills/research/research-paper-writing/templates/acl/formatting]]
- [[skills/research/research-paper-writing/templates/colm2025/README]]
- [[skills/seo-article-harvester/SKILL]]
- [[skills/seo-article-harvester/references/crawling-tools]]
- [[skills/smart-home/DESCRIPTION]]
- [[skills/smart-home/openhue/SKILL]]
- [[skills/social-media/DESCRIPTION]]
- [[skills/social-media/xitter/SKILL]]
- [[skills/software-development/plan/SKILL]]
- [[skills/software-development/requesting-code-review/SKILL]]
- [[skills/software-development/subagent-driven-development/SKILL]]
- [[skills/software-development/systematic-debugging/SKILL]]
- [[skills/software-development/test-driven-development/SKILL]]
- [[skills/software-development/writing-plans/SKILL]]
- [[skills/kanban-worker/SKILL]]
- [[skills/kanban-orchestrator/SKILL]]
- [[skills/kanban-dashboard/SKILL]]

## Links
- [[@identity/brain/rules]]
- [[@action/gateway/drewgent-architecture-dataflow]]
