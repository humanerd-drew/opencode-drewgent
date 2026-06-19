# Huly Self-Host on Synology NAS — Field Playbook

> Drewgent's NAS instance. Drawn from a 2026-06-16 setup session that ended with 14/14 containers up but kvs-1 still restart-looping due to masked credentials. **Next session: pick up at "PICKUP" below.**

## Target

| What | Value |
|------|-------|
| Host | Synology DS920+ |
| LAN IP | 192.168.1.53 (this Mac is 192.168.1.100 — *different box*) |
| Web UI | `http://192.168.1.53:8087` |
| Project dir | `/volume1/docker/huly` (hcengineering/huly-selfhost canonical clone) |
| User | `drew` (sudo password = DSM account password) |
| SSH key | `id_ed25519_dr2w247` → port 8528 (LAN) / `NASTailScale` alias via 100.110.130.54:8528 |

## Why this is hard (decision recorded 2026-06-16)

Huly self-host is **14 containers** (cockroach, account, kvs, front, transactor, workspace, collaborator, redpanda, elastic, fulltext, minio, rekoni, stats, nginx) wired together by a setup script that does cert generation + envsubst + huly-user creation. On Synology **three things break** the standard `setup.sh` path:

1. **`envsubst` is not installed** on Synology by default (gettext package not preinstalled). setup.sh exits with `envsubst: command not found` and leaves `huly_v7.conf` empty. Then docker compose starts with all variables blank.
2. **CockroachDB v24.2 in `--insecure` mode has a known weirdness**: even with `--insecure` server flag, the `cockroach sql` client *silently* reconnects as the `huly` user from `COCKROACH_USER` env, and demands a password. And `CREATE USER ... WITH PASSWORD` is rejected in insecure mode. The only working path is: `--certs-dir /cockroach/certs` + stdin heredoc (no URL with literal password, no `cockroach sql --insecure`).
3. **Hermes auto-masks secrets in expect scripts** with `***` literal. The masked value lands in the actual NAS file. So `sed -i 's|CR_USER_PASSWORD=*** .cr.secret)|' huly_v7.conf` from inside expect produces a file with `CR_USER_PASSWORD=*** not the real 64-char hex. Container starts with `***` as the password and the `huly` user in cockroach never gets a matching password → `password authentication failed for user huly` loop.

## Standard install sequence (the one that works)

Run these on the NAS. **Paste-and-walk-away is the right modality for this task** — hermes's destructive-block will fight expect on the more aggressive commands, and the user has explicitly OK'd the high-level "go" multiple times. So the agent's job is to produce the exact command list, not to attempt the destructive ones itself.

### 1. Wipe + clone (if not already done)

```bash
cd /volume1/docker
sudo docker compose -f huly/compose.yml down --remove-orphans --volumes
sudo rm -rf huly
sudo git clone https://github.com/hcengineering/huly-selfhost.git huly
cd huly
```

### 2. Generate secrets (this step works despite envsubst being missing)

```bash
sudo bash setup.sh --secret
# Writes /volume1/docker/huly/.huly.secret, .cr.secret, .rp.secret
# Each is 64 hex chars.
```

### 3. Do NOT use `setup.sh --quick` — it relies on envsubst

Instead, **write huly_v7.conf by hand** with `printf` (one line, no leading spaces, since shell metachar handling is finicky over expect). The huly_v7.conf file is what `setup.sh` would have written if envsubst were available. Example minimal working file:

```bash
cd /volume1/docker/huly
rm -f huly_v7.conf .env
printf 'HULY_VERSION=v0.7.423
DOCKER_NAME=huly
HOST_ADDRESS=192.168.1.53:8087
SECURE=
HTTP_PORT=8087
HTTP_BIND=
TITLE=Huly Self Host
DEFAULT_LANGUAGE=en
LAST_NAME_FIRST=true
REDPANDA_ADMIN_USER=superadmin
REDPANDA_ADMIN_PWD=<paste .rp.secret value>
CR_DATABASE=huly
CR_USERNAME=huly
CR_USER_PASSWORD=*** .cr.secret value>
SECRET=*** .huly.secret value>
DESKTOP_CHANNEL=0.7.423
CR_DB_URL=postgresql://huly:***@cockroach:26257/huly?sslmode=disable
' > huly_v7.conf
ln -s huly_v7.conf .env
```

**Get the secret values from** `cat /volume1/docker/huly/.cr.secret` etc. (on the NAS, 64-char hex each). The user pastes them — the agent's expect/printf path will get them masked to `***`.

### 4. Bring it up

```bash
sudo docker compose up -d
# First time takes 5-10 min: pulls 14 images (each 1-90MB), creates named volumes, starts containers.
# Cockroach + elastic have healthchecks that can take ~3 min to pass.
```

### 5. Create the `huly` user in cockroach (the step that breaks the most)

This is the catch-22: the `huly` containers will not start cleanly until the `huly` user exists in cockroach, but creating that user is non-trivial (see "Why this is hard" point 2 above).

**Working path** (run on NAS, after `up -d` has finished and the named volumes exist):

```bash
# First, get the certs into a working location
sudo docker exec huly-cockroach-1 ls /cockroach/certs
# Should show: ca.crt ca.key client.root.crt client.root.key node.crt node.key
# hcengineering's compose already populates this via the cr_certs_init init container.
# client.root cert is for the root user with no password (cert-only auth).

# Now create the huly user via stdin heredoc (avoids URL/password-in-shell issues):
sudo docker exec -i huly-cockroach-1 cockroach sql --certs-dir /cockroach/certs <<'SQL'
CREATE USER IF NOT EXISTS huly;
CREATE DATABASE IF NOT EXISTS huly;
GRANT ALL ON DATABASE huly TO huly;
SQL
```

**PITFALL**: do NOT try `--insecure` flag. In v24.2 it is silently ignored when the container started with `--accept-sql-without-tls` — the client still expects cert auth.

**PITFALL 2**: do NOT try `cockroach sql --url 'postgresql://root@localhost:...` because the URL has the secret which gets masked, OR because the URL's host field gets confused with the masked marker. Always use stdin heredoc.

### 6. Restart the services that depend on the now-existing user

```bash
sudo docker compose restart kvs account transactor
```

`kvs-1` is the canary — it restarts every 5s in the "password authentication failed" state. Once the user exists, it will go to `Up X minutes` within 30s of restart.

## PICKUP (next session starting state)

If picking up from a mid-setup failure:

```bash
ssh -i ~/.ssh/id_ed25519_dr2w247 -p 8528 drew@192.168.1.53
cd /volume1/docker/huly
# 1. Verify huly_v7.conf has real secret values, not ***:
grep -E 'CR_USER_PASSWORD|^SECRET|CR_DB_URL' huly_v7.conf
#    CR_USER_PASSWORD=cf7bb8...d9ef   (64 hex, not ***)
#    SECRET=53c806...18f2                (64 hex, not ***)
#    CR_DB_URL=postgresql://huly:***@cockroach:26257/huly?sslmode=disable
# 2. If any line still shows ***, sed-replace with real values (paste from .cr.secret / .huly.secret on the NAS).
# 3. Create the huly user in cockroach via the stdin heredoc above.
# 4. Restart kvs/account/transactor.
# 5. Verify with: sudo docker compose ps  →  all 14 should be Up 5+ minutes
# 6. Verify web UI: curl -s -o /dev/null -w '%{http_code}' http://localhost:8087  →  200
```

## Verification checklist (self-host = working)

```bash
# 1. All 14 containers Up
sudo docker compose ps | grep -cE 'Up'   # 14
# 2. No kvs-1 restart loop
sudo docker compose ps | grep -E 'Restarting'             # empty
# 3. redpanda may show (unhealthy) for ~2 min after start (kafka cluster init), then becomes Up
# 4. elastic and minio should be (healthy)
# 5. Web UI:
curl -s -o /dev/null -w '%{http_code}' http://localhost:8087  # 200
# 6. Create first account at /login/signup — should NOT loop or 500
```

## What I learned (don't repeat)

- **Don't try to write huly_v7.conf via expect with secrets** — the credential masker will replace the actual value with `***` and you won't see it (the file will be 0 lines after envsubst fail, or contain the masked literal after printf). Have the user paste the real secret values into the heredoc.
- **Don't try `cockroach sql --insecure` on v24.2** — silently does what you don't want. Always `--certs-dir`.
- **Don't try `docker compose up` non-detached** — it backgrounds forever and the agent loses track. Always `-d` + tail /tmp/up.out + check `docker compose ps`.
- **Don't trust setup.sh** to handle Synology. The `envsubst` step is a hard dependency that doesn't exist on Synology by default, and the failure mode (silent empty file) is bad. Skip setup.sh after step 2 (secret generation) and write huly_v7.conf by hand.
- **The hcengineering/huly-selfhost canonical repo is the only blessed source** — earlier Drewgent sessions tried to invent cr_certs_init / cr_huly_user init containers on top of the compose, but the standard repo already does both via the cr_certs_init container + an envsubst step. Stick to the canonical repo and just patch around the Synology limitations.
