# NAS SSH + expect + sudo: Patterns That Actually Work

Synology DS920+에서 Huly(self-host) 또는 다른 docker stack을 원격 조작할 때, **expect로 sudo password prompt 다루기**는 본질적으로 fragile. 이 문서는 두 세션(2026-06-14, 2026-06-15)에 걸친 시행착오 끝에 확인된 패턴을 정리한다.

**For the canonical playbook (with full Huly self-host integration context, including the hcengineering/huly-selfhost reference cloning approach and cr_certs init container pattern), see the class-level skill `nas-synology-ssh-automation`.** This reference adds the Huly-specific failure modes on top of that base.

## User signals to stop and ask (before another expect round)

These user phrases during an expect-driven NAS session are STOP signals. Offer a manual-execution fallback immediately instead of retrying the expect script:

| User phrase | Meaning | Action |
|-------------|---------|--------|
| "네가 작업할 수 있는거잖아" (you can do it) | user is granting explicit go-ahead for the next destructive step | proceed, but use the **working** expect pattern (see "Single-sudo baseline" below) instead of the chained/looped one |
| "개소리 하지말고" / "이것부터 해결" | stop the meta-discussion, focus on the actual blocker | drop the explanation, switch to concrete next action |
| "이유를 설명해봐라" / "왜 안되지?" | user is asking for an honest post-mortem, not a fix | give the honest diagnosis (race condition, hostile env, etc.), do NOT immediately try another fix |
| "이게 문제라는데" + terminal output | user is showing a specific symptom; the bug report IS the request | diagnose THAT specific symptom, don't go off on tangents about other things you noticed |
| "처음부터 다시 하는건 어떻겠니?" | user is signaling that the current path is wrong, not just stuck | step back, **re-read the upstream reference** (e.g. github.com/hcengineering/huly-selfhost README), then start over with the canonical procedure |
| Silence after a `Do NOT retry` / `BLOCKED` message from the security policy | the platform itself is blocking the next action | offer a manual-execution fallback to the user (the "Drawer checklist" below); the policy is not under your control |

**Anti-pattern:** when the user signals "just do it" and you try 3+ expect patterns that all hang, the user is going to ask "왜 안되는거야" — and you'll have to admit that expect+sudo is fundamentally fragile and you should've offered manual execution after the first hang.

## Huly-specific gotchas on top of base expect patterns

### cr_huly_user init container — only `--certs-dir` is right

When writing the `cr_huly_user` init container in `compose.yml`, the cockroach sql command **must only pass `--certs-dir`**. **DO NOT** add `--ca-cert`, `--cert`, or `--key` flags. cockroach v24.2 errors with `ERROR: unknown flag: --ca-cert` if you do.

CORRECT:
```yaml
cr_huly_user:
  image: cockroachdb/cockroach:latest-v24.2
  entrypoint: ["/bin/sh", "-c"]
  command:
    - "sleep 20 && cockroach sql --certs-dir=/certs -e \"CREATE USER IF NOT EXISTS huly; CREATE DATABASE IF NOT EXISTS huly; GRANT ALL ON DATABASE huly TO huly;\" || true"
```

INCORRECT (will fail at runtime with unknown flag):
```yaml
command:
  - "sleep 20 && cockroach sql --certs-dir=/certs --ca-cert=/certs/ca.crt --cert=/certs/client.root.crt --key=/certs/client.root.key -e \"...\""
```

Reason: cockroach v24.2 only accepts `--certs-dir` as the umbrella flag. The individual `--ca-cert/--cert/--key` flags were removed/deprecated. `cockroach cert create-ca` and `cert create-client` produce the files in the right structure for `--certs-dir` to find them.

### cr_certs_init — keep it as a separate `cr_certs` volume

Don't try to make the cert creation share the same volume as the main cockroach data (`cr_data`). The cert files need to be **read-only** to cockroach at runtime, and the `chmod -R 777` that Synology forces on mounted dirs would otherwise expose the private key. The separate `cr_certs` named volume (in the `volumes:` block at the bottom of compose.yml) keeps certs isolated.

### `--insecure` mode is fundamentally broken on v24.2 — use secure mode + cr_certs

The earlier temptation to drop `--insecure` from `cockroach start-single-node` to avoid cert gymnastics **does not work** on cockroach v24.2:

- `CREATE USER huly WITH PASSWORD '...'` → fails with `setting or updating a password is not supported in insecure mode`
- Even `cockroach sql --url 'postgresql://root@localhost:***@localhost`

**Always use the cr_certs init container path.** See the "Working path" section in the main `huly-integration` SKILL.md for the full compose fragment.

### hcengineering/huly-selfhost standard already has certs handled — use `setup.sh --quick`

If you ever want to **start over from scratch** on the NAS — or hit a wall with hand-rolled cr_certs init containers — the canonical path is:

```bash
# SSH in, clean up the messy custom compose
cd /volume1/docker
sudo docker compose -f huly/compose.yml down --remove-orphans --volumes
sudo rm -rf huly
# Clone the canonical reference
sudo git clone https://github.com/hcengineering/huly-selfhost.git huly
cd huly
cp example-huly.conf huly_v7.conf
# Edit huly_v7.conf: HOST_ADDRESS, HTTP_PORT, CR_USERNAME, CR_USER_PASSWORD
sudo bash setup.sh --secret   # generates SECRET=*** in huly_v7.conf
sudo bash setup.sh --quick    # generates nginx.conf + docker compose up -d
# Wait 60 seconds. http://192.168.1.53:8087 is live.
```

The reference `setup.sh` **already** has the cr_certs init container logic integrated (it adds a hidden init container at runtime that creates the certs and the huly user). Our manual add of `cr_certs_init` / `cr_huly_user` is reinventing what upstream already solved. The 5-hour debugging session (2026-06-15) was entirely unnecessary — `setup.sh --quick` would have done it in 5 minutes.

Future re-deploys should use the upstream `setup.sh` and apply only the env-specific patches (SERVER_SECRET, NAS bind paths, etc.) on top. Do NOT hand-roll cr_certs init containers.

## Failure modes hit during 2026-06-14 + 2026-06-15 sessions

| Symptom | Root cause | Fix |
|---------|-----------|-----|
| `password authentication failed for user huly` (account service logs) | `huly` user doesn't exist in cockroach — the `COCKROACH_USER` env var is ignored by the official cockroachdb image (postgres/mariadb convention, not cockroach's) | Use `setup.sh --quick` (it does this for you), or run the cr_huly_user init container (secure mode + certs path) |
| `key file certs/node.key has permissions -r-xr-xr-x, exceeds -rwxr-----` | Synology ext4 ACLs force 0777 on bind-mounted files | Use `cr_certs` named volume (Docker-managed perms) instead of bind mount |
| `Bind mount failed: '/volume1/docker/huly/data/cockroach' does not exist` | compose does NOT create host bind mount dirs | `sudo mkdir -p data/cockroach` before `up -d` |
| account service loops `ECONNREFUSED 192.168.48.X:26257` | cr_huly_user init didn't run (cert issue or compose path wrong), so huly user/db was never created | Verify cr_certs init completed, then `sudo docker compose ps` should show cr_huly_user as `Exited (0)` not `Restarting` |
| `Require key` in account logs (JWT signing fails) | compose expects `SECRET` env var, stock .env only has `SERVER_SECRET` | Add `SECRET=*** to .env or copy `SERVER_SECRET` to `SECRET` |
| `Sorry, try again.` in expect after `send -- "$password\r"` (race condition) | sudo's prompt takes longer than expect's `sleep N` to render; expect sends the password before sudo is ready, sudo rejects it | Use `sleep 2` (not 1) and `send -- "$password\n"` (not `\r`); if still failing, the issue is `tty` setup (use `-tt` not `-T`) |
| expect hangs after multi-sudo `&&` chained command | second `sudo` doesn't prompt (cache), expect's `expect "drew@"` waits for next prompt that never comes | Either split into single `sudo` per expect round-trip, or use `sudo bash -c '...'` to wrap the chain in one sudo |

## Drawer checklist — when NOT to write a custom expect script

Writing complex expect automation is **frequently slower** than asking the user to copy-paste 4 commands. Stop and offer a manual-execution fallback when:

- `sudo` + `&&` + python script + >500 char base64 combined
- `sudo` + heredoc + >3 distinct commands
- 3+ consecutive expect sessions have already timed out
- The command would be classified as destructive (`rm -rf`, `down --volumes`, etc.) and the user hasn't given explicit go for THIS specific step

When offering manual execution, the format that works:

```
NAS에서 다음 명령 실행:
\\`\\`\\`bash
cd /volume1/docker/huly
sudo docker compose down --remove-orphans --volumes
sudo rm -rf data/cockroach
sudo mkdir -p data/cockroach
sudo docker compose up -d
\\`\\`\\`
끝나면 `sudo docker compose ps` 출력 복사해서 보내주세요.
```

## See also

- `nas-synology-ssh-automation` — the class-level skill. This file is the Huly-flavoured supplement.
- `huly-integration` SKILL.md "Working path" section — the canonical cr_certs compose fragment (legacy; the right way is `setup.sh --quick` per the table above).
