# gbrain Orphan Watchdog

## 발견 (2026-06-13)

GBrain MCP 서버가 무응답 — `hermes mcp test gbrain`이 40초 타임아웃, `gbrain stats`는 "Timed out waiting for PGLite lock".

**진단:** `gbrain serve` 프로세스가 3개 실행 중. PGLite가 단일 writer라서 lock 경쟁 발생.

```
PID 29420 ← 게이트웨이 (drewgent_cli.main gateway)    ← 유지
PID 42908 ← Hermes CLI (종료됨)                         ← orphan
PID 57813 ← Hermes CLI (종료됨)                         ← orphan
```

**원인:** Hermes MCP stdio transport가 `gbrain serve` subprocess를 spawn하지만, CLI 세션 종료 시 gbrain(bun 프로세스)이 orphan으로 잔류. stdin closure를 감지하고 자동종료하지 않음.

## 해결

### 1. Orphan 식별

```bash
for pid in $(ps aux | grep "gbrain serve" | grep -v grep | awk '{print $2}'); do
  ppid=$(ps -o ppid= -p $pid 2>/dev/null | tr -d ' ')
  pcmd=$(ps -o command= -p $ppid 2>/dev/null | head -1)
  echo "gbrain PID $pid ← parent PID $ppid ($pcmd)"
done
```

- Gateway parent → KEEP (`drewgent_cli.main gateway run`)
- Hermes CLI parent (종료됨) → KILL

### 2. Orphan kill

```bash
kill <orphan-pid-1> <orphan-pid-2>
# Verify
hermes mcp test gbrain  # Expected: ✓ Connected (<1s), 89 tools
```

### 3. 자동화: Watchdog script

**스크립트:** `~/.hermes/scripts/drewgent_gbrain_watchdog.sh`

`ps -eo pid,ppid,comm`으로 gbrain 프로세스의 부모 존재 여부 확인. 부모가 죽었고 PPID가 1이 아니면 orphan으로 간주하고 kill.

**bash 3.2 호환 주의:** macOS 기본 bash는 associative array(declare -A)를 지원하지 않음. `ps aux`의 $3는 %CPU, PPID가 아님.

**크론:** `gbrain-watchdog` (ID: 0fb33852686c, 15분 간격, no_agent)

## Pitfall: ps aux vs ps -eo

```bash
# ❌ 잘못된 방법 — $3는 %CPU
ps aux | grep "gbrain" | awk '{print $2, $3}'

# ✅ 올바른 방법
ps -eo pid,ppid,comm | grep "gbrain"
```

macOS 기본 bash 3.2와 `ps` (BSD 계열)는 Linux (GNU ps)와 컬럼 순서가 동일하지만 `ps aux`의 3번째 컬럼은 PPID가 아니라 %CPU. PPID는 `ps aux`에 기본 포함되지 않음. `ps -o ppid= -p $pid`로 개별 조회하거나 `ps -eo pid,ppid,...`로 명시적 지정.
