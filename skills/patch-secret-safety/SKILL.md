---
name: patch-secret-safety
title: Patch 시 Secret/Token Truncate 함정 회피
description: mcp_patch 또는 mcp_write_file로 secret이 포함된 config/env/credential 파일을 편집할 때, read_file이 마스킹한 truncated form을 new_string에 넣으면 실제 secret이 사라지는 함정을 피하는 절차. 트리거: Bearer, sk-, ghp-, api_key, password, TOKEN, KEY, SECRET 같은 패턴이 들어있는 파일을 patch로 편집.
type: skill
space: growth
tags: [skill, safety, secrets, patch, file-editing, credentials]
created: 2026-06-01
updated: 2026-06-01
links:
  - "[[skills/python-nested-import-nameerror]]"
  - "[[skills/filesystem-truth-audit]]"
  - "[[@identity/brain/Drewgent-brain/P0-brainstem/禁/禁secrets_in_code.neuron]]"
  - "[[@identity/brain/Drewgent-brain/P0-brainstem/禁/禁blind_write.neuron]]"
  - "[[@identity/brain/rules]]"---


# Patch 시 Secret/Token Truncate 함정 회피

## 문제: read_file 마스킹 → patch 시 secret 사라짐

`mcp_read_file`은 secret 값을 `***` 또는 truncated form으로 가린다 (예: `df90de...59a7`, `sk-cp-...tEAs`). 그래서 secret이 들어있는 config 파일을 patch하려면 read_file로 파일을 다시 보고, 그 안의 secret을 `new_string`에 그대로 복사해야 하는데 — 마스킹된 값을 그대로 복사하면 patch가 성공해도 **실제 secret이 truncated form으로 교체**되어, 다음 인증 호출이 다 깨진다.

## 함정의 정확한 메커니즘

```
[read_file 호출]
   ↓
display: "Authorization: Bearer df90de...59a7"  ← 화면엔 truncated
   ↓
실제 파일: "Authorization: Bearer df90de21-b838-44c7-b653-d29c6f3759a7"
   ↓
내가 new_string에 "Bearer df90de...59a7" 넣고 patch
   ↓
patch는 byte-level 비교. diff는 실제 원본 "df90de21-b838-44c7-b653-d29c6f3759a7"을 보여줌
   ↓
하지만 내가 new_string에 truncated form을 넣었으므로
"df90de...59a7"가 실제 값으로 patch됨 ← SECRET 사라짐
```

**핵심**: `mcp_patch`의 diff는 byte-level이라 실제 원본 값을 보여주지만, `mcp_read_file`의 display는 human-readable truncated form만 보여준다. **두 source가 서로 다른 정보를 보여주는 게 함정이다.**

## 올바른 절차

### Step 1: secret 패턴 감지

편집 대상 파일을 먼저 보고, secret이 들어있는지 확인:

```python
SECRET_PATTERNS = [
    r"Bearer\s+[A-Za-z0-9_\-\.]{10,}",          # Bearer tokens
    r"sk-[A-Za-z0-9\-]{20,}",                    # OpenAI-style sk- keys
    r"sk-ant-[A-Za-z0-9\-]{20,}",                # Anthropic
    r"sk-cp-[A-Za-z0-9\-]{20,}",                 # coding plan (MiniMax)
    r"ghp_[A-Za-z0-9]{36}",                      # GitHub PAT
    r"xox[abposr]-[A-Za-z0-9\-]{10,}",          # Slack
    r"AIzaSy[A-Za-z0-9_\-]{33}",                # Google API
    r"[A-Za-z0-9]{32,}\.[A-Za-z0-9_\-]{40,}\.[A-Za-z0-9_\-]{20,}",  # JWT
    r"[A-Fa-f0-9]{8}-[A-Fa-f0-9]{4}-[A-Fa-f0-9]{4}-[A-Fa-f0-9]{4}-[A-Fa-f0-9]{12}",  # UUID tokens
    r"api[_-]?key\s*[=:]\s*['\"]?[A-Za-z0-9_\-]{10,}",
    r"password\s*[=:]\s*['\"]?[A-Za-z0-9_\-\.!@#$%^&*]{6,}",
    r"token\s*[=:]\s*['\"]?[A-Za-z0-9_\-]{10,}",
    r"_TOKEN\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{10,}",
    r"_KEY\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{10,}",
    r"_SECRET\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{10,}",
]
```

### Step 2: secret 위치 파악

해당 secret을 가만히 두는 게 안전한지, 아니면 옆 라인을 patch하면서 secret을 보존해야 하는지 결정. **secret을 건드릴 이유가 없으면 그 라인은 old_string/new_string에 포함시키지 않는다.**

### Step 3: secret을 보존해야 할 때 — diff가 정답

옆 라인을 patch해야 하는데 secret 라인도 old_string에 들어가야 할 때:

1. `mcp_read_file`로 파일 읽기 → display는 truncated
2. **먼저 git에서 원본을 본다**:
   ```bash
   git show HEAD:path/to/file.yaml | grep -A 2 "Bearer"
   ```
3. 위의 truncated display + diff의 byte-level 값을 결합해서 **실제 secret을 재구성**한다.
4. 그 실제 secret을 `old_string`과 `new_string` 양쪽에 그대로 넣는다.
5. **절대로 truncated form을 new_string에 넣지 않는다.**

### Step 4: patch 후 verify

patch 성공 후 즉시 secret이 살아있는지 확인:

```bash
# 또는 mcp_terminal로:
grep "Authorization" config.yaml        # secret prefix 확인
python3 -c "import yaml; print(len(yaml.safe_load(open('config.yaml'))['mcp_servers']['X']['headers']['Authorization']))"  # 길이 sanity check (truncated면 너무 짧음)
```

**verify 안 하고 끝내지 마라.** truncated patch는 patch success로 보고되지만 runtime에서 401 Unauthorized로 한참 후에 발견된다 — 디버깅 시간 폭증.

## 안전한 대안

### 대안 1: secret 라인 제외하고 patch

옆 라인만 수정하고 secret 라인은 절대 old_string에 안 넣는다. patch는 unique한 context line을 기준으로 매칭하므로 secret이 필요 없는 경우라면 가능:

```python
# BAD: secret이 old_string에 포함됨
old_string = "Authorization: Bearer df90de...59a7\n  timeout: 60"
new_string = "Authorization: Bearer <new-secret>\n  timeout: 120"

# GOOD: secret 라인 위 라인만 context로 사용
old_string = "  lazyweb:\n    url: https://www.lazyweb.com/mcp\n    headers:"
new_string = "  lazyweb:\n    url: https://www.lazyweb.com/mcp\n    headers:\n      Authorization: Bearer <new-secret>"
```

### 대안 2: mcp_terminal + sed -i (interactive)

```bash
sed -i.bak 's|Bearer df90de...59a7|Bearer <new-secret>|' config.yaml
# sed는 secret을 직접 매칭하므로 read_file 마스킹 우회
```

### 대안 3: mcp_write_file로 전체 재작성

파일이 작으면 read_file로 display 확인 → git show로 실제 secret 확인 → 둘을 머지 → write_file로 전체 재작성. patch보다 안전 (전체 컨텍스트가 new_string에 있으므로).

## 실전 예시 (2026-06-01 incident)

### 상황
`~/.drewgent/config.yaml`에 MCP 서버 추가. `mcp_servers` 블록에 두 개의 secret이 있었음:
- `lazyweb.Authorization: Bearer df90de21-b838-44c7-b653-d29c6f3759a7`
- `minimax.env.MINIMAX_API_KEY: sk-cp-e-PhdzslOiYElDMAyjWyPr16yyVDDPzRPLYlMPSc03Oqp6ttyT0l-LDlMoAyrU1XpOsd4-c2U9NnJ9gdfGE8-GAt6gnCddanxF_oxBWt2WMovDjEoaitEAs`

### 실수
read_file이 `***`로 마스킹한 걸 보고 내가 new_string에 truncated form:
- `df90de...59a7` (28자)
- `sk-cp-...tEAs` (12자)

을 넣음. patch는 success.

### 즉시 복구
1. patch response의 `diff` 필드 다시 읽기 → byte-level이라 실제 secret이 거기 있음
2. 다시 patch로 truncate된 부분을 원본 secret으로 교체
3. `load_config()`로 verify → mcp_servers keys 정상 노출

### 재발 방지
이 skill 생성. 다음번엔 display의 truncated form을 보고도 new_string에는 절대 그걸 안 넣고, git에서 원본을 본다.

## Patch tool 인코딩 함정 — 템플릿 리터럴 이스케이프 (2026-06-11)

`mcp_patch`는 JavaScript/TypeScript 템플릿 리터럴(백틱 `)을 자동으로 백슬래시 이스케이프(`\`)한다.
이로 인해 JS 파싱 에러(`Uncaught SyntaxError: Invalid or unexpected token`)가 발생한다.

**증상**: 
```javascript
// 수정 후 → SyntaxError
return \`<div>...</div>\`;  // ← \` 가 깨짐
```

**회피**:
1. 백틱이 포함된 JS/TS 파일은 `write_file`로 전체 재작성 (patch 말고)
2. 또는 patch 후 즉시 `node --check <file>`로 문법 검증
3. diff에 `\`가 보이면 추가 수동 수정 필요

**판단 기준**:
| 조건 | 도구 |
|------|------|
| 파일에 백틱 없음 | `patch` 안전 |
| 백틱 있고 변경 범위 작음 | `write_file`로 해당 블록만 |
| 백틱 있고 변경 범위 큼 | `terminal` + `sed`로 line 교체 |

## Verification checklist

patch가 secret을 건드렸다면:

- [ ] `mcp_terminal` + `grep` 으로 secret prefix 확인 (`sk-cp-e-...`인지 `df90de21-...`인지)
- [ ] python parser로 secret 길이 sanity check (정상 secret은 36자 UUID 또는 100자+ sk- 키)
- [ ] 관련 서비스에 실제 인증 호출 (curl / load_config() / etc.)
- [ ] `git diff`로 patch 결과가 secret을 truncated로 만들지 않았는지 확인

## Related

- [[@identity/brain/Drewgent-brain/P0-brainstem/禁/禁secrets_in_code.neuron]] — 코드에 secret 박지 말라는 P0 규칙 (이 skill은 **편집 시**의 secret 보존)
- [[@identity/brain/Drewgent-brain/P0-brainstem/禁/禁blind_write.neuron]] — 읽기 없이 쓰지 말라 (이 skill도 같은 원칙을 patch에 적용)
- [[skills/python-nested-import-nameerror]] — Python lexical scoping 함정. 같은 "patch 전 읽기 + 정확한 byte 보존" 카테고리
- [[skills/filesystem-truth-audit]] — memory/vault의 "Done" path가 실제 filesystem에 있는지 검증. 이 skill의 "patch 후 verify" 단계와 같은 정신
