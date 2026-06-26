---
title: n8n Password Reset via SQLite
name: n8n-password-reset
description: n8n locked 계정 비밀번호 재설정 — SQLite DB 직접 조작으로 bcrypt 해시 교체
type: skill
space: outcome
tags: [skill, automation, n8n]
created: 2026-06-01
updated: 2026-06-01
links:
  - "[[@action/skills/SKILL-INDEX]]"
  - "[[skills/n8n-self-hosted-diagnostics]]"
  - "[[skills/automation/DESCRIPTION]]"
  - "[[@identity/brain/rules]]"---

# n8n Password Reset — SQLite Direct Update

n8n locked 계정에서 비밀번호를 재설정하는 절차.
`n8n user` CLI가 없으므로 DB 직접 조작으로만 가능.

## 환경

- **DB 경로**: `~/.n8n/database.sqlite`
- **Python bcrypt**: `pip install bcrypt`
- **n8n 사용자 테이블**: `user` (SQLite)

## 핵심 원리

n8n은 bcrypt ($2a$ prefix)로 비밀번호 해시 저장.
비밀번호 재설정 = DB에서 해시 직접 교체.

## Step 1: 현재 해시 확인

```python
import sqlite3, os

DB = os.path.expanduser("~/.n8n/database.sqlite")
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

cur = conn.execute('SELECT id, email, password FROM "user" LIMIT 5')
for row in cur.fetchall():
    print(f"{row['email']}: {row['password'][:30]}...")
conn.close()
```

## Step 2: 새 비밀번호 해시 생성 + DB 업데이트

```python
import bcrypt, sqlite3, os

new_password = "YOUR_NEW_PASSWORD_HERE"
salt = bcrypt.gensalt(rounds=10)
hashed = bcrypt.hashpw(new_password.encode(), salt)
# bcrypt은 $2b$를 생성하지만 n8n은 $2a$를 사용 — 변환 필수
hashed_str = hashed.decode().replace('$2b$', '$2a$')

DB = os.path.expanduser("~/.n8n/database.sqlite")
conn = sqlite3.connect(DB)
conn.execute('UPDATE "user" SET password = ? WHERE email = "TARGET@EMAIL.COM"', (hashed_str,))
conn.commit()
print(f"Updated hash: {hashed_str}")

# 검증
cur = conn.execute('SELECT password FROM "user" WHERE email = "TARGET@EMAIL.COM"')
row = cur.fetchone()
print(f"Verification: {bcrypt.checkpw(new_password.encode(), row[0].encode())}")
conn.close()
```

## Step 3: n8n API 로그인 검증

```bash
curl -s -X POST http://localhost:5678/rest/login \
  -H "Content-Type: application/json" \
  -d '{"emailOrLdapLoginId":"TARGET@EMAIL.COM","password":"YOUR_NEW_PASSWORD_HERE"}'
```

정상 응답: `{"data":{...}}` — `role: "global:owner"` 확인

## 시험 과정에서 배운 것

| # | 발견 | 의미 |
|---|------|------|
| 1 | `n8n user` CLI 명령 없음 | CLI로는 비밀번호 재설정 불가 |
| 2 | `$2b$` → `$2a$` 변환 필수 | bcrypt 생성 해시의 prefix를 n8n 호환으로 변환해야 login 성공 |
| 3 | `emailOrLdapLoginId` 필드명 | REST API 로그인 시 필드가 `email`이 아님 |
| 4 | DB 경로 `~/.n8n/` | n8n data 디렉토리 아래 database.sqlite |

## Pitfalls

- **$2b$ → $2a$ 변환 안 하면**: login 실패. n8n의 bcrypt.checkpw가 $2a$를 기대하기 때문
- **MFA enabled인 경우**: 이 절차로도 로그인 불가 — MFA도 DB에서 disable 필요
- **rounds는 10으로固定**: n8n 기본값과 호환되는 안전하고 빠른 선택

## Related

- [[skills/n8n-self-hosted-diagnostics]] — n8n 상태 진단 (비밀번호 reset 절차 없음 — 이 스킬이 보완)
- [[skills/automation/DESCRIPTION]] — n8n automation skill
