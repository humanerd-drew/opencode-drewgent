---
name: wrangler-pages-deploy
title: "wrangler-pages-deploy — Cloudflare Pages + wrangler OAuth multi-account gotcha 해결"
description: "Cloudflare Pages에 wrangler로 deploy할 때 발생하는 'More than one account available but unable to select one in non-interactive mode' 또는 403 Authentication error 해결 절차. OAuth token에 여러 CF 계정이 연결돼 있을 때 (personal + org 흔함) 발생하는 multi-account selection 문제 + wrangler.toml이 Pages 형식과 안 맞는 문제. humanerd.kr, Quartz publishing pipeline, fswatch 자동 deploy 등 영향."
type: skill
space: growth
tags: [skill, wrangler, cloudflare, pages, deploy, auth, oauth, devops, humanerd-site]
created: 2026-06-01
updated: 2026-06-1
links:
  - "[[skills/humanerd-site]]"
  - "[[skills/quartz-remove-drafts-customization]]"
  - "[[P3-sensors/gateway/drewgent-architecture-dataflow]]"
  - "[[P0-brainstem/brain/rules]]"---

# wrangler-pages-deploy

`npx wrangler pages deploy`가 실패할 때의 진단 + 해결 절차. **Drewgent 6/1 incident에서 4번의 dead end 후 5번째에 해결한 패턴**.

## 문제 — 4가지 가능한 증상

### 증상 A: `More than one account available but unable to select one`

```
✘ [ERROR] More than one account available but unable to select one in non-interactive mode.

  Please set the appropriate `account_id` in your Wrangler configuration file or assign it to the `CLOUDFLARE_ACCOUNT_ID` environment variable.
  Available accounts are (`<name>`: `<account_id>`):
    `humanerd_me`: `dc0199b6b6c27bc9bb2f3201d47cb643`
    `humanerd_org`: `ba5e8b86f33e63c791da65ef587bdc98`
```

원인: OAuth token에 CF 계정 2개 이상 연결. dev/sandbox 환경에서 흔함.

### 증상 B: 403 Authentication error

```
✘ [ERROR] A request to the Cloudflare API (/accounts/.../pages/projects/...) failed.

  Authentication error [code: 10000]
```

원인: OAuth token 권한 부족, 또는 token expired. **계정을 지정해도 발생 가능** (token 자체가 권한 잃은 경우).

### 증상 C: `Missing top-level field "name"` (Pages wrangler.toml)

```
✘ [ERROR] Running configuration file validation for Pages:
  - Missing top-level field "name" in configuration file.
  - Configuration file for Pages projects does not support "account_id"
```

원인: wrangler.toml 형식이 Workers용으로 작성됨. Pages는 별도 형식.

### 증상 D: `Missing "pages_build_output_dir" field, required by Pages`

```
We detected a configuration file at ... but it is missing the "pages_build_output_dir" field, required by Pages.
  Ignoring configuration file for now, and proceeding with project deploy.
```

원인: Pages config 형식이지만 `pages_build_output_dir` 누락. wrangler가 config 무시하고 deploy 시도.

## 진단 — 어느 증상인지 확인

### Step 1: wrangler.toml 확인

```bash
cat /Users/drew/.drewgent/humanerd-site/wrangler.toml
```

**Workers용 (잘못된 형식)** — Pages에서 안 먹음:
```toml
compatibility_date = "2024-01-01"
account_id = "dc0199b6b6c27bc9bb2f3201d47cb643"   # ← Pages는 top-level에서 안 받음

[pages]                                            # ← Pages에서는 unexpected field
project_name = "humanerd-site"
```

**Pages용 (올바른 형식)**:
```toml
name = "humanerd-site"
compatibility_date = "2024-01-01"
pages_build_output_dir = "public"
```

Pages용 핵심:
- `name` 필수 (top-level)
- `pages_build_output_dir` 필수
- `account_id` 없음 (env var로 전달)

### Step 2: OAuth token에 몇 계정 연결돼 있는지

```bash
npx wrangler whoami 2>&1 | head -20
# 또는
CLOUDFLARE_ACCOUNT_ID=... npx wrangler pages deploy ... 2>&1 | grep "Available accounts"
```

증상 A가 보이면 → multi-account. **env var로 명시 필요**.

### Step 3: wrangler 버전 확인

```bash
npx wrangler --version
```

**주의**: 4.95와 4.42.1 둘 다 같은 multi-account 에러 발생. wrangler 업그레이드가 해결책 아님. **OAuth token 문제지 wrangler 버전 문제가 아님**.

## Fix — 검증된 4단계 절차

Drewgent humanerd.kr에서 6/1에 적용한 방식 (4번의 dead end 후 성공):

### 1단계: wrangler.toml을 Pages 형식으로 단순화

```bash
cat > /Users/drew/.drewgent/humanerd-site/wrangler.toml <<'EOF'
name = "humanerd-site"
compatibility_date = "2024-01-01"
pages_build_output_dir = "public"
EOF
```

**확인 사항:**
- `[pages]` 섹션 없음
- `account_id` 없음
- `name`, `compatibility_date`, `pages_build_output_dir` 3개만

### 2단계: user가 `npx wrangler login` 실행

OAuth token 갱신. **반드시 user가 직접 terminal에서 실행** (non-interactive mode라 agent가 대신 못 함).

```bash
npx wrangler login
# 브라우저에서 CF Dashboard 인증 → 토큰 갱신됨
```

### 3단계: env var로 account 명시

```bash
CLOUDFLARE_ACCOUNT_ID=dc0199b6b6c27bc9bb2f3201d47cb643 \
  npx wrangler pages deploy public/ --project-name=humanerd-site --commit-dirty=true
```

**project name은 wrangler.toml에 있으면 안 적어도 되지만 명시 권장** (실수 방지).

### 4단계: deploy 검증

```bash
# Preview URL 확인
echo "Deploy complete → check https://<hash>.humanerd-site.pages.dev"

# Custom domain 확인
curl -s -o /dev/null -w "%{http_code}\n" https://humanerd.kr/
# 200 = 성공
```

## Pitfalls

### 1. **wrangler 4.95로 업그레이드 시도 — 효과 없음**

OAuth token expired 문제는 wrangler 버전 무관. 4.42.1 → 4.95 업그레이드 해도 같은 403. **wrangler 다운그레이드도 비추** — token이 정상이라면 4.95가 더 안전.

**판단 기준**: token 자체를 갱신하는 것이 wrangler 버전 변경보다 우선.

### 2. **account_id를 wrangler.toml에 넣기 — Pages에서는 안 먹음**

```toml
# Wrong — Pages는 top-level account_id를 무시 (또는 error)
account_id = "dc0199..."

# Right
# wrangler.toml에는 account_id 없음
# env var: CLOUDFLARE_ACCOUNT_ID=...
```

Workers와 Pages의 wrangler.toml 형식이 다르다는 점 주의. Workers는 `account_id` + `main` 필드, Pages는 `name` + `pages_build_output_dir` 필드.

### 3. **CF Pages edge cache 전파 지연 (5~30초)**

deploy 직후 curl로 live URL 테스트하면 **stale 404**가 나올 수 있음. CF Pages는 global edge에 deploy 결과 전파하는 데 5~30초 걸림 (변동 큼).

```bash
# 잘못된 진단: deploy 후 5초 만에 curl → 404 → "deploy 실패" 잘못 판단
curl -s -o /dev/null -w "%{http_code}\n" https://humanerd.kr/insights/foo
# 404

# 30초 후 다시 → 200
sleep 30
curl -s -o /dev/null -w "%{http_code}\n" https://humanerd.kr/insights/foo
# 200
```

**올바른 진단**: deploy 후 30~60초 wait → curl. 또는 Preview URL (`<hash>.humanerd-site.pages.dev`)로 즉시 확인 가능 (전파 안 거치고 origin hit).

### 4. **fswatch LaunchAgent가 죽었어도 wrangler deploy는 동일하게 실패**

`com.drewgent.quartz-fswatch` LaunchAgent가 멈춰있어도 wrangler 인증 문제는 wrangler 토큰 문제일 뿐, fswatch 재시작이 해결책 아님.

진단:
```bash
launchctl list | grep quartz-fswwatch
# PID 숫자 = running
# PID = - = loaded이지만 spawn 안 됨
```

fswatch 자체가 죽었으면:
```bash
launchctl unload ~/Library/LaunchAgents/com.drewgent.quartz-fswatch.plist
launchctl load -w ~/Library/LaunchAgents/com.drewgent.quartz-fswatch.plist
```

이건 wrangler auth와 별개. **둘 다 점검 필요**.

### 5. **`wrangler pages deploy`는 git과 무관 — directory deploy**

`--commit-dirty=true`는 git dirty check를 skip할 뿐, **git push를 안 함**. CF Pages에 directory를 직접 upload하는 모드. Drewgent humanerd.kr는 git 없이 `public/` → wrangler → CF Pages 흐름.

GitHub Pages / Cloudflare Pages with git 연결 방식과는 다름.

### 6. **OAuth token 권한 부족 시 `wrangler login`만으로 해결 안 될 수 있음**

OAuth로 인증했어도 그 계정의 Pages project에 대한 `pages:write` 권한이 없을 수 있음. 이 경우:
- CF Dashboard → Account → Members → 본인 user 확인 → role이 `Administrator` 또는 `Pages Editor`인지
- 또는 별도 API token 발급 (User API Token, `Cloudflare Pages: Edit` scope)

OAuth flow가 정상이고 `wrangler login`이 성공해도 권한 부족이면 동일 에러.

## 운영 자동화 (Drewgent fswatch script에 적용 권장)

`~/.drewgent/P4-cortex/scripts/quartz-deploy.sh`에 다음 추가:

```bash
#!/bin/bash
# Multi-account OAuth 환경에서 deploy
export CLOUDFLARE_ACCOUNT_ID="${CLOUDFLARE_ACCOUNT_ID:-dc0199b6b6c27bc9bb2f3201d47cb643}"
PROJECT="humanerd-site"
BUILD_DIR="public"

cd /Users/drew/.drewgent/humanerd-site
npx wrangler pages deploy "$BUILD_DIR" --project-name="$PROJECT" --commit-dirty=true
```

`~/.drewgent/P4-cortex/scripts/quartz-fswatch.sh`에서:
```bash
export CLOUDFLARE_ACCOUNT_ID="dc0199b6b6c27bc9bb2f3201d47cb643"
bash /Users/drew/.drewgent/P4-cortex/scripts/quartz-deploy.sh
```

이렇게 해두면 user가 `npx wrangler login`만 다시 실행해도 fswatch가 자동 deploy 정상 동작.

## 흔한 follow-up 질문

**Q: `CLOUDFLARE_API_TOKEN` env var는 안 써도 되나?**
A: OAuth flow에선 API token 안 써도 됨. OAuth user의 권한에 따름. **다만 OAuth보다 API token이 더 세밀한 권한 제어 가능** (예: Pages project 1개만 접근). token 발급은 CF Dashboard에서 가능.

**Q: Preview URL은 custom domain과 다른가?**
A: 다름. `<hash>.humanerd-site.pages.dev` (preview) ≠ `humanerd.kr` (custom domain). Preview는 즉시 전파, custom domain은 DNS + edge cache 거쳐서 30~60초.

**Q: wrangler.toml과 wrangler.jsonc 중에 어느 거 쓰나?**
A: 둘 다 지원하지만 `.toml`이 공식 권장. `jsonc`는 Workers의 옛 형식.

**Q: Account ID `dc0199b6b6c27bc9bb2f3201d47cb643`는 어디서 찾나?**
A: CF Dashboard 우측 하단 → "Account ID" 또는 Workers & Pages → Overview → Account ID. Drewgent는 `humanerd_me` 계정의 ID. 절대 노출 안 되는 정보는 아님 (계정 식별자일 뿐).

## Related

- [[skills/humanerd-site]] — Quartz publishing pipeline 전체 운영
- [[skills/quartz-remove-drafts-customization]] — Quartz draft filter customization
- [[P3-sensors/gateway/drewgent-architecture-dataflow]] — vault → site 데이터 흐름

## 6/1 incident timeline (왜 이 skill이 필요한가)

- 20:18:30 — 마지막 successful deploy (5/27)
- 6/1 15:00대 — fswatch dead, 5개 cron job 1.5일 dormant 발견
- 6/1 15:00~15:30 — kanban-stuck-task-recovery + cron-jobs-stalled 두 incident 동시 처리
- 6/1 15:30 — wrangler 403 → 4번의 dead end (upgrade, downgrade, wrangler.toml 추가, env var)
- 6/1 16:00 — user의 `npx wrangler login` + Pages용 wrangler.toml 단순화로 해결

**총 dead end 횟수: 4**. 이 skill은 그 시행착오를 압축한 결과물.
