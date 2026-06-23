# Scripts Index

## Active (25)

| Script | Purpose | Referenced By |
|--------|---------|---------------|
| agent_dashboard_push.py | Push agent state to Cloudflare dashboard | cron/jobs.json, skills/ |
| ard_query.py | ARD Registry search client | AGENTS.md |
| cron_health_check.py | Cron job health monitoring | cron/jobs.json |
| cron_runner.py | Cron job executor | cron/jobs.json, skills/ |
| cron_seo_harvester.sh | SEO article collection shell wrapper | cron/jobs.json |
| discord_bot.py | Discord ↔ opencode gateway | launchd |
| discord_send.py | Discord message chunk sender | drewgent_cron.py, skills/ |
| drewgent_cron.py | Cron dispatcher (60s interval) | launchd |
| drewgent_gbrain_watchdog.sh | gbrain brain sync health check | skills/ |
| drewgent_harmony_check.sh | Vault graph integrity check | cron/jobs.json, skills/ |
| drewgent_log_rotate.sh | Log rotation and compression | cron/jobs.json, skills/ |
| excalidraw-to-png.js | Excalidraw diagram to PNG conversion | skills/ |
| install.sh | Drewgent installer | repo root |
| install.cmd | Windows installer | repo root |
| install.ps1 | PowerShell installer | repo root |
| kanban_maintenance.py | Kanban DB maintenance | skills/ |
| minimax_usage.py | Token usage tracking | skills/ |
| n8n_trigger_runner.py | LLM-generated cron trigger execution | cron/jobs.json |
| office_autopilot.sh | Kanban autopilot (5min cycle) | cron/jobs.json |
| opencode_health_check.py | opencode daemon health check | launchd |
| run_kanban_worker.py | Kanban task executor | skills/ |
| seo_analyzer.sh | SEO article analysis shell wrapper | cron/jobs.json |
| trend_harvester.py | AI trend collection | cron/jobs.json, skills/ |
| trend_usage_watch.py | Trend usage monitoring | cron/jobs.json, skills/ |
| wordpress-mcp-server.js | WordPress MCP server | skills/ |

## Archived (18)

Moved to archive/ — unreferenced in docs, cron, or imports.

| Script | Reason |
|--------|--------|
| add_content_pipeline_job.py | No references found |
| agent_dashboard_local_server.py | No references found |
| cron_seo_harvester.py | Replaced by cron_seo_harvester.sh |
| cron_trend_harvester.py | No references found |
| deepseek_humanize.py | No references found |
| discord_context_transfer.py | No references found |
| discord-voice-doctor.py | No references found |
| kanban_dispatcher.py | Superseded by office_autopilot.sh |
| kill_modal.sh | No references found |
| obsidian_graph_integrity.py | No references found |
| release.py | No references found |
| report_generator.py | No references found |
| sample_and_compress.py | No references found |
| setup_update_checker.sh | No references found |
| test_croniter_tz.py | Test file, not referenced |
| threads_post.py | No references found |
| update_content_pipeline_cron.py | No references found |
| verify_pfolder.py | No references found |
