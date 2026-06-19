---
title: n8n Self-Hosted Diagnostics
name: n8n-self-hosted-diagnostics
description: npm으로 설치된 n8n 셀프호스트 상태 진단 + launchd 관리 스킬
type: skill
space: outcome
tags: [skill, n8n, self-hosted, diagnostics]
created: 2026-06-01
updated: 2026-06-01
links:
  - "[[P3-sensors/skills/SKILL-INDEX]]"
  - "[[skills/automation/DESCRIPTION]]"
  - "[[P0-brainstem/brain/rules]]"---

# n8n Self-Hosted Diagnostics

npm으로 설치된 n8n 셀프호스트의 상태를 진단하고 launchd로 관리하는 스킬.

## 환경 (2026-06-01 기준)

- **설치**: npm global (`/opt/homebrew/lib/node_modules/n8n`)
- **실행 경로**: `/opt/homebrew/bin/n8n` → symlink to npm package
- **데이터 경로**: `~/.n8n/`
- **DB**: `~/.n8n/database.sqlite` (SQLite)
- **설정**: `~/.n8n/config` (JSON — encryptionKey 포함)
- **포트**: 5678
- **launchd plist**: `~/Library/LaunchAgents/ai.drewgent.n8n.plist`
- **로그**: `~/P6-prefrontal/logs/n8n.log`, `n8n.error.log`
- **launchd label**: `ai.drewgent.n8n`
- **업데이트**: `npm update -g n8n` (Homebrew formula 없음)

## launchd 관리

```bash
# 상태 확인
launchctl list | grep n8n

# 수동 시작
launchctl start ai.drewgent.n8n

# 수동 정지
launchctl stop ai.drewgent.n8n

# 재시작
launchctl stop ai.drewgent.n8n && sleep 2 && launchctl start ai.drewgent.n8n

# plist reload
launchctl unload ~/Library/LaunchAgents/ai.drewgent.n8n.plist
launchctl load ~/Library/LaunchAgents/ai.drewgent.n8n.plist
```

재부팅 시 `RunAtLoad: true`로 자동 시작됩니다.

## 진단 체크리스트

```bash
# 1. launchd 상태
launchctl list | grep n8n

# 2. 프로세스 확인
ps aux | grep n8n | grep -v grep

# 3. 포트 LISTEN 확인
lsof -i :5678

# 4. HTTP 응답 확인
curl -s -o /dev/null -w "%{http_code}" http://localhost:5678

# 5. 데이터 디렉토리
ls -la ~/.n8n/

# 6. 로그 확인
tail -20 ~/P6-prefrontal/logs/n8n.log
tail -20 ~/P6-prefrontal/logs/n8n.error.log
```

## 계정 복구 — SQLite 직접 초기화 (bcrypt 해시 교체)

n8n은 bcrypt 해시 사용. **UI "Forgot my password"가 작동하지 않는 경우** SQLite에서 직접 bcrypt 해시를 교체.

### 핵심: bcrypt 해시 — $2b$ vs $2a$

**최신 n8n (2025~2026)은 `$2b$` prefix도 인식함.**

```python
import bcrypt, sqlite3, os

DB = os.path.expanduser('~/.n8n/database.sqlite')
new_password = '새비밀번호'

# bcrypt 해시 생성
salt = bcrypt.gensalt(rounds=10)
hashed_str = bcrypt.hashpw(new_password.encode(), salt).decode()

# 유저 확인
conn = sqlite3.connect(DB)
cur = conn.execute('SELECT id, email FROM "user"')
for row in cur.fetchall():
    print(row)

# 비밀번호 업데이트
conn.execute('UPDATE "user" SET password = ? WHERE email = ?', (hashed_str, '대상@이메일.com'))
conn.commit()

# 검증
row = conn.execute('SELECT password FROM "user" WHERE email = ?', ('대상@이메일.com',)).fetchone()
print(f'해시 검증: {bcrypt.checkpw(new_password.encode(), row[0].encode())}')
conn.close()
print('완료 — http://localhost:5678 에서 로그인 시도')
```

**躬行 결과 (2026-06-01)**:
- 계정: `drew@humanerd.kr` (disabled=true 상태)
- `$2b$` 해시로 교체 후 바로 로그인 성공
- disabled 계정도 비밀번호 교체로 복구 확인

### 주의
- `rounds=10` (n8n 기본값)
- `"user"` 테이블명은 따옴표 필수 (SQLite 키워드 충돌)
- `disabled=true` 계정도 password만 교체하면 복구 가능

## workflow 확인

```bash
sqlite3 ~/.n8n/database.sqlite "SELECT id, name, active FROM workflow_entity LIMIT 10;"
```

## Discord webhook 403 Forbidden

workflow의 Discord webhook이 `403 Forbidden`을 반환하는 경우:
- Discord webhook URL이 유효하지만 bot이 서버에서 **삭제**된 경우

**확인**: `curl -X POST -H 'Content-Type: application/json' -d '{"content":"test"}' <webhook_url>`
- `403` 반환 → webhook 무효화. 새 webhook URL 발급 필요.

## encryptionKey의중요성

n8n의 encryptionKey는 credential 안전화에 사용됨. config 파일 유실 시 n8n이 시작되지 않음.

## npm 업데이트 (n8n 버전 유지)

```bash
# 현재 버전 확인
n8n --version

# 업데이트 확인
npm outdated -g n8n

# 업데이트 실행
npm update -g n8n

# 또는 특정 버전
npm install -g n8n@latest
```

**참고**: n8n은 Homebrew formula가 없음 (`brew search n8n` → `n8n-mcp`만 있음). npm으로 관리해야 합니다.

## Known Issue: 충돌 루프

**증상**: `n8n's port 5678 is already in use` 로그 반복 + launchd 재시작 루프.

**원인**: n8n이 plist 외 경로로 이미 실행 중일 때 충돌.

**해결**:
```bash
# 기존 프로세스 중지
kill $(ps aux | grep 'n8n' | grep -v grep | awk '{print $2}')

# plist reload
launchctl unload ~/Library/LaunchAgents/ai.drewgent.n8n.plist
launchctl load ~/Library/LaunchAgents/ai.drewgent.n8n.plist
```
