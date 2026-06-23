# Brain Signal System — Complete Implementation Plan

## 목적

에이전트가 외부 기능(도구, 스킬, 어댑터, 명령어 등)을 자기 내부에 통합할 때,
자신이 어느 단계에 있는지 인식하고 다음 행동을 안내받는 범용 자아 인식 시스템.

---

## 1. 통합 영역 분류 (Integration Domains)

총 7개 영역. Tool과 Skill은 구현 완료. 나머지 5개 영역을 구현해야 한다.

| ID | 영역 | INTEGRATION_FILES | 완료 조건 |
|----|------|------------------|----------|
| T1 | Tool Integration | `tools/`, `model_tools.py`, `toolsets.py` | 3개 파일 모두 수정 |
| T2 | Skill Integration | `skills/`, `agent/skill_commands.py` | 2개 파일 모두 수정 |
| T3 | Gateway Platform | `gateway/platforms/`, `gateway/run.py` | platform 파일 + run.py 등록 |
| T4 | Slash Command | `drewgent_cli/commands.py`, `cli.py` | CommandDef + handler |
| T5 | MCP Server | `tools/mcp_tool.py`, `tools/<name>.py` | mcp_servers[] + handler 파일 |
| T6 | Cron Job | `cron/jobs.py`, `cron/scheduler.py` | job 등록 + 스케줄 설정 |
| T7 | Brain Signal 확장 | `agent/brain_signals.py`, `agent/signal_processor.py` | signal type 등록 + handler |

---

## 2. ArchitectureModel 확장 설계

현재 상태 (완료):
```python
TOOL_INTEGRATION_FILES = ["tools/", "model_tools.py", "toolsets.py"]
SKILL_INTEGRATION_FILES = ["skills/", "agent/skill_commands.py"]
```

완료 상태 (구현 대상):
```python
INTEGRATION_FILES = {
    "tool": {
        "files": ["tools/", "model_tools.py", "toolsets.py"],
        "completion": "all_modified",
    },
    "skill": {
        "files": ["skills/", "agent/skill_commands.py"],
        "completion": "all_modified",
    },
    "gateway_platform": {
        "files": ["gateway/platforms/", "gateway/run.py"],
        "completion": "file_created_and_registered",
        "register_in": "PLATFORM_REGISTRY or run.py import",
    },
    "slash_command": {
        "files": ["drewgent_cli/commands.py", "cli.py"],
        "completion": "commanddef_and_handler",
    },
    "mcp_server": {
        "files": ["tools/mcp_tool.py", "tools/<server>.py"],
        "completion": "server_config_and_handler",
    },
    "cron_job": {
        "files": ["cron/jobs.py", "cron/scheduler.py"],
        "completion": "job_defined_and_scheduled",
    },
    "brain_signal": {
        "files": ["agent/brain_signals.py", "agent/signal_processor.py"],
        "completion": "signal_registered_and_handled",
    },
}
```

핵심 추상화: 모든 영역이 동일한 구조를 가진다.
- files: 수정해야 할 파일 경로 목록
- completion: 완료 판단 기준
- register_in: 등록 위치 (영역마다 상이)

---

## 3. SignalEmitter 확장 설계

현재 상태: tool_patterns + skill_patterns 두 가지.
완료 상태: 모든 영역의 intent 패턴을 보유.

```python
class SignalEmitter:
    def __init__(self):
        self._patterns = {
            "tool": ["add.*tool", "새.*도구", "register.*tool", ...],
            "skill": ["add.*skill", "새.*스킬", ...],
            "gateway_platform": [
                "add.*gateway.*adapter", "새.*플랫폼.*어댑터",
                "discord.*setup", "slack.*setup",
                "telegram.*bot.*add", "whatsapp.*setup",
            ],
            "slash_command": [
                "add.*command", "새.*슬래시.*명령어",
                "register.*slash", "/.*command.*add",
            ],
            "mcp_server": [
                "add.*mcp.*server", "새.*mcp.*서버",
                "register.*mcp.*tool", "mcp.*connect",
            ],
            "cron_job": [
                "add.*cron.*job", "새.*크론.*작업",
                "schedule.*task", " periodic.*job",
            ],
            "brain_signal": [
                "add.*signal.*type", "새.*브레인.*시그널",
                "extend.*brain.*system", "new.*event.*type",
            ],
        }
        self._file_heuristics = {
            "gateway/platforms/": "gateway_platform",
            "drewgent_cli/commands.py": "slash_command",
            "cli.py": "slash_command",
            "tools/mcp_tool.py": "mcp_server",
            "cron/jobs.py": "cron_job",
            "agent/brain_signals.py": "brain_signal",
        }
```

핵심 추상화: file_heuristics로 파일 경로만으로 영역을 유추.
사용자가 "새 디스코드 어댑터 만들어줘"라고 하면:
1. 파일 생성 감지 → gateway_platform으로 분류
2. gateway_platform 플로우 시작

---

## 4. ArchitectureModel.detect_*() 확장

현재: detect_tool_integration_progress(), detect_skill_integration_progress()
추가: detect_gateway_integration_progress(), detect_command_integration_progress(), detect_mcp_integration_progress(), detect_cron_integration_progress(), detect_signal_integration_progress()

각 detect 함수의 공통 구조:
```python
def detect_<domain>_integration_progress(self, files_modified: list) -> dict:
    domain_files = INTEGRATION_FILES[<domain>]["files"]
    completed = [f for f in files_modified if self._matches_any(f, domain_files)]
    remaining = [f for f in domain_files if not self._is_modified(f, files_modified)]
    is_complete = len(completed) == len(domain_files)
    next_hint = self._get_hint_for_next_step(<domain>, remaining)
    return {
        "is_complete": is_complete,
        "completed": completed,
        "remaining": remaining,
        "next_hint": next_hint,
        "progress_pct": len(completed) / len(domain_files),
    }
```

---

## 5. AwarenessReporter 확장 설계

현재: tool_hint_template + skill_hint_template
완료: 모든 영역별 guidance 템플릿

```python
GUIDANCE_TEMPLATES = {
    "tool": {
        "started": "🔧 도구 통합 시작: tools/ 파일 먼저 생성하세요",
        "mid": "✅ {completed} 완료. 다음: {remaining[0]} 수정 필요",
        "complete": "🎉 도구 통합 완료! registry.register() 호출하면 됩니다",
    },
    "gateway_platform": {
        "started": "🌐 Gateway 플랫폼 어댑터 통합 시작",
        "mid": "✅ 플랫폼 파일 생성됨. 다음: gateway/run.py에 등록 필요",
        "complete": "🎉 Gateway 어댑터 등록 완료! 테스트해 보세요",
    },
    "slash_command": {
        "started": "⚡ Slash command 통합 시작",
        "mid": "✅ CommandDef 추가됨. 다음: cli.py에 handler 구현 필요",
        "complete": "🎉 Slash command 등록 완료! /help에서 확인하세요",
    },
    "mcp_server": {
        "started": "🔌 MCP 서버 통합 시작",
        "mid": "✅ 서버 핸들러 파일 생성. 다음: mcp_tool.py의 mcp_servers[]에 추가 필요",
        "complete": "🎉 MCP 서버 등록 완료! /tools mcp로 확인하세요",
    },
    "cron_job": {
        "started": "⏰ Cron job 통합 시작",
        "mid": "✅ job 함수 정의됨. 다음: scheduler에 등록 필요",
        "complete": "🎉 Cron job 등록 완료! crontab -e로 확인하세요",
    },
    "brain_signal": {
        "started": "🧠 Brain signal 확장 시작",
        "mid": "✅ 시그널 핸들러 정의됨. 다음: signal_processor에 등록 필요",
        "complete": "🎉 Brain signal 확장 완료! 테스트해 보세요",
    },
}
```

---

## 6. 힌트 주입 메커니즘 유지

run_agent.py의 힌트 주입 로직을 모든 영역으로 확장:
```python
# 모든 active workflow에 대해 progress check
for workflow in active_workflows:
    if workflow.integration_type == "tool":
        progress = arch.detect_tool_integration_progress(workflow.files_modified)
    elif workflow.integration_type == "gateway_platform":
        progress = arch.detect_gateway_integration_progress(workflow.files_modified)
    elif workflow.integration_type == "slash_command":
        progress = arch.detect_command_integration_progress(workflow.files_modified)
    elif workflow.integration_type == "mcp_server":
        progress = arch.detect_mcp_integration_progress(workflow.files_modified)
    elif workflow.integration_type == "cron_job":
        progress = arch.detect_cron_integration_progress(workflow.files_modified)
    elif workflow.integration_type == "brain_signal":
        progress = arch.detect_signal_integration_progress(workflow.files_modified)
    # ... skill은 이미 구현됨
```

현재 if-elif 체인으로 되어 있으므로, 각 영역마다 분기 추가.

---

## 7. 단일 책임 원칙: IntegrationDomain 추상화

현재 문제를 해결하는 구조적 개편:

```python
from abc import ABC, abstractmethod

class IntegrationDomain(ABC):
    @abstractmethod
    def detect_type(self) -> str: pass
    @abstractmethod
    def get_required_files(self) -> list: pass
    @abstractmethod
    def is_complete(self, files_modified: list) -> bool: pass
    @abstractmethod
    def get_next_hint(self, files_modified: list) -> str: pass
    @abstractmethod
    def get_patterns(self) -> list: pass

class ToolDomain(IntegrationDomain):
    def detect_type(self): return "tool"
    def get_required_files(self): return ["tools/", "model_tools.py", "toolsets.py"]
    def is_complete(self, files): return self._all_modified(files)
    def get_patterns(self): return ["add.*tool", "새.*도구", ...]

class GatewayPlatformDomain(IntegrationDomain):
    def detect_type(self): return "gateway_platform"
    def get_required_files(self): return ["gateway/platforms/", "gateway/run.py"]
    def is_complete(self, files): return self._file_and_registered(files)
    def get_patterns(self): return ["add.*gateway.*adapter", ...]

# ArchitectureModel은 IntegrationDomain 리스트를 순회하며 분류
domains = [ToolDomain(), SkillDomain(), GatewayPlatformDomain(), ...]
```

이 구조로 새로운 영역 추가 시: IntegrationDomain subclass 생성 + ArchitectureModel._domains에 추가.

---

## 8. 파일 변경 추적 메커니즘 강화

현재: tool_start → agent_modifying 이벤트 체인.
개선: 파일 경로 정규화 + 영역 매핑 자동화.

```python
def _classify_file_path(self, file_path: str) -> str | None:
    """파일 경로만으로 integration domain을 분류."""
    for domain, files in INTEGRATION_FILES.items():
        for pattern in files:
            if pattern in file_path or self._fnmatch(file_path, pattern):
                return domain
    return None
```

예: "gateway/platforms/discord.py" 생성 감지
→ _classify_file_path → "gateway_platform"
→ IntegrationWorkflow 자동 생성
→ awareness hint: "Gateway 플랫폼 어댑터입니다. 다음: gateway/run.py에 등록하세요"

---

## 9. Persistence 레이어 (완료 — 유지보수)

sessionDB v8 schema + workflow persistence 이미 구현 완료.
새 영역 추가해도 schema 불변. workflow.integration_type만 확장.

```sql
-- integration_workflows 테이블 (기존 구조 그대로 유지)
workflow_id, session_id, integration_type, target_name,
files_modified, steps_completed, started, completed,
completed_at, correlation_id, created_at

-- integration_type이 "gateway_platform", "slash_command", "mcp_server",
-- "cron_job", "brain_signal" 등 확장 가능
```

---

## 10. 구현 작업 목록 (Phase별)

### Phase B1: Gateway Platform Integration
- [ ] `signal_processor.py`: INTEGRATION_FILES["gateway_platform"] 정의
- [ ] `signal_processor.py`: `detect_gateway_integration_progress()` 구현
- [ ] `brain_signals.py`: gateway_platform 패턴 추가
- [ ] `awareness_reporter.py`: GATEWAY_PLATFORM_GUIDANCE 추가
- [ ] `run_agent.py`: gateway_platform 분기 추가
- [ ] 테스트: "새 디스코드 어댑터 만들어줘" 시나리오

### Phase B2: Slash Command Integration
- [ ] `signal_processor.py`: INTEGRATION_FILES["slash_command"] 정의
- [ ] `signal_processor.py`: `detect_command_integration_progress()` 구현
- [ ] `brain_signals.py`: slash_command 패턴 추가
- [ ] `awareness_reporter.py`: SLASH_COMMAND_GUIDANCE 추가
- [ ] `run_agent.py`: slash_command 분기 추가
- [ ] 테스트: "새 slash command 만들어줘" 시나리오

### Phase B3: MCP Server Integration
- [ ] `signal_processor.py`: INTEGRATION_FILES["mcp_server"] 정의
- [ ] `signal_processor.py`: `detect_mcp_integration_progress()` 구현
- [ ] `brain_signals.py`: mcp_server 패턴 추가
- [ ] `awareness_reporter.py`: MCP_SERVER_GUIDANCE 추가
- [ ] `run_agent.py`: mcp_server 분기 추가
- [ ] 테스트: "새 MCP 서버 연결해줘" 시나리오

### Phase B4: Cron Job Integration
- [ ] `signal_processor.py`: INTEGRATION_FILES["cron_job"] 정의
- [ ] `signal_processor.py`: `detect_cron_integration_progress()` 구현
- [ ] `brain_signals.py`: cron_job 패턴 추가
- [ ] `awareness_reporter.py`: CRON_JOB_GUIDANCE 추가
- [ ] `run_agent.py`: cron_job 분기 추가
- [ ] 테스트: "새 cron job 만들어줘" 시나리오

### Phase B5: Brain Signal Expansion
- [ ] `signal_processor.py`: INTEGRATION_FILES["brain_signal"] 정의
- [ ] `signal_processor.py`: `detect_signal_integration_progress()` 구현
- [ ] `brain_signals.py`: brain_signal 패턴 추가
- [ ] `awareness_reporter.py`: BRAIN_SIGNAL_GUIDANCE 추가
- [ ] `run_agent.py`: brain_signal 분기 추가
- [ ] 테스트: "새 brain signal 만들어줘" 시나리오

### Phase B6: Refactoring — IntegrationDomain 추상화
- [ ] `agent/integration_domain.py`: IntegrationDomain ABC 정의
- [ ] 각 Domain subclass 구현 (ToolDomain, SkillDomain, GatewayDomain, ...)
- [ ] `signal_processor.py`: _domains 리스트로 리팩토링
- [ ] `awareness_reporter.py`: get_hint_for_domain() 추상화
- [ ] 모든 기존 테스트 통과 확인

### Phase B7: End-to-End Test Suite
- [ ] 각 영역별 통합 테스트 생성
- [ ] workflow persistence 시나리오 테스트
- [ ] multi-domain 동시 추적 테스트

---

## 11. 예상工作量

| Phase | 영역 | 예상 시간 |
|-------|------|----------|
| B1 | Gateway Platform | 1.5-2h |
| B2 | Slash Command | 1-1.5h |
| B3 | MCP Server | 1-1.5h |
| B4 | Cron Job | 1-1.5h |
| B5 | Brain Signal 확장 | 1h |
| B6 | IntegrationDomain 리팩토링 | 2-3h |
| B7 | End-to-End 테스트 | 1.5-2h |
| **Total** | | **9-13h** |

---

## 12. 설계 원칙 요약

1. **모든 영역은 동형 구조**: files + patterns + completion + hint
2. **자동 분류**: 파일 경로만으로 영역 유추
3. **완료 기준 명확화**: 각 영역의 "완료" 정의가 명시적
4. **힌트는 ephemeral**: user message 주입, sessionDB 불변
5. **확장성**: 새로운 영역 추가 시 IntegrationDomain subclass만 구현
6. **기존 유지보수**: tool/skill은 이미 완료, B6에서 구조적으로 통합

---

## 13. 테스트 검증 전략

각 영역 테스트 시나리오:
```
[시나리오 1] "새 디스코드 어댑터 만들어줘"
  → gateway_platform workflow 시작
  → gateway/platforms/discord.py 생성 → file tracked
  → hint: "gateway/run.py에 등록 필요"
  → gateway/run.py 수정 → is_complete
  → celebration hint

[시나리오 2] "새 slash command 만들어줘"
  → slash_command workflow 시작
  → drewgent_cli/commands.py에 CommandDef 추가 → file tracked
  → hint: "cli.py에 handler 구현 필요"
  → cli.py에 handler 추가 → is_complete

[시나리오 3] multi-domain: "디스코드 어댑터랑 cron job 둘 다 만들어줘"
  → gateway_platform workflow + cron_job workflow 동시 추적
  → 각 workflow별 hint 주입
```

---

## 14. 완료 정의

- 7개 영역 모두 IntegrationDomain 구조로 통합
- 각 영역별 시나리오 테스트 통과
- workflow persistence (중단/재개) 모든 영역에서 작동
- run_agent.py 힌트 주입 로직이 모든 영역 지원
- AGENTS.md 완전 문서화