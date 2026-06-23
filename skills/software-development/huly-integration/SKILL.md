---
title: Huly Integration
name: huly-integration
description: "Integrate with Huly Cloud (formerly Huly Platform) — TypeScript API client, WebSocket-based data operations, issue/task synchronization from Hermes kanban."
trigger: "User wanted to replace Linear with Huly for PM/Kanban. Built from reverse-engineering the @hcengineering/api-client against Huly Cloud (huly.app)."
provenance:
  session: "2026-06-14 kanban-linear-huly"
  decision: "Huly Cloud free tier chosen over self-host (Colima 2GB RAM + Ollama + existing services would cause memory contention). API client works via Node.js WebSocket with window polyfill."
domain: software-development
created: 2026-06-14
updated: 2026-06-15
links:
  - "[[devops/kanban-worker]]"
  - "[[shell-init-side-effect-gating]]"
  - "[[P3-sensors/skills/SKILL-INDEX]]"
---

# Huly Integration

Huly (https://huly.io) is an all-in-one project management platform (alternative to Linear, Jira, Slack, Notion). This skill covers two approaches:

| Approach | When To Use | Tools |
|----------|-------------|-------|
| **MCP Server (Preferred)** | Agent-to-Huly interaction — issues, projects, milestones, comments, labels, search, members. Anything a user would ask you to do in Huly. | 81 native MCP tools via Hermes `mcp_servers.huly` |
| **Direct SDK** | Cron scripts, real-time bridge (pushHandler), bulk sync operations that run headless in the background. | `@hcengineering/api-client` (Node.js WebSocket) |

---

## MCP Server (Preferred Approach)

A native Hermes MCP server is configured at `~/.hermes/config.yaml` → `mcp_servers.huly`. It wraps the full Huly SDK and exposes 81 tools covering issues, projects, milestones, labels, comments, members, time tracking, workspaces, and accounts.

### Setup

```yaml
# ~/.hermes/config.yaml — already configured
mcp_servers:
  huly:
    command: /Users/drew/.drewgent/scripts/huly-mcp-wrapper.sh
```

The wrapper script (`~/.drewgent/scripts/huly-mcp-wrapper.sh`) reads `HULY_KEY` from `~/.hermes/.env` at runtime and bridges it as `HULY_TOKEN`. This keeps the JWT out of config.yaml — no credential exposure in version control.

**Auth:** No extra setup — the existing `HULY_KEY` (JWT from Settings → Integrations → API Access) is used directly.

**Server:** `@bgx4k3p/huly-mcp-server` (npm). Stdio transport, auto-loaded on every Hermes session.

### Available MCP Tools (81 total)

**Context & Workspace:**
- `get_huly_context` — sanitized runtime info
- `list_workspaces`, `get_workspace_info`, `get_workspace_members`

**Issues:**
- `list_issues`, `get_issue`, `create_issue`, `update_issue`, `delete_issue`
- `search_issues`, `get_my_issues`, `batch_create_issues`
- `move_issue`, `add_relation`, `add_blocked_by`, `set_parent`
- `create_issues_from_template` (feature/bug/sprint/release)

**Comments:**
- `list_comments`, `get_comment`, `add_comment`, `update_comment`, `delete_comment`

**Labels:**
- `list_labels`, `create_label`, `update_label`, `delete_label`, `get_label`
- `add_label`, `remove_label`

**Milestones:**
- `list_milestones`, `get_milestone`, `create_milestone`, `update_milestone`, `delete_milestone`
- `set_milestone`

**Projects:**
- `list_projects`, `get_project`, `create_project`, `update_project`, `delete_project`, `archive_project`
- `summarize_project`
- `list_statuses`, `get_status`, `list_task_types`, `get_task_type`
- `list_components`, `get_component`, `create_component`, `update_component`, `delete_component`

**Time Tracking:**
- `log_time`, `list_time_reports`, `get_time_report`, `delete_time_report`

**Members & Account:**
- `list_members`, `get_member`, `get_account_info`, `get_user_profile`
- `send_invite`, `create_invite_link`

### Quick Examples

```bash
# MCP tools are used via Hermes tool calls, not shell. Examples of what you can do:

# List all projects in the workspace
# → call huly:list_projects with {}

# Create an issue
# → call huly:create_issue with {project: "TST", title: "...", description: "..."}

# Add a comment
# → call huly:add_comment with {issueId: "TST-42", text: "..."}

# Search across projects
# → call huly:search_issues with {query: "login bug"}
```

### When to Fall Back to Direct SDK

The MCP server cannot (yet) handle these scenarios — keep using `@hcengineering/api-client`:
- **Real-time pushHandler** — bridge daemon (`huly_bridge.js`) needs persistent WebSocket
- **Document CRUD** — document/space operations not covered
- **Chunter (chat)** — channel message operations
- **Drive (storage)** — file operations
- **Headless cron scripts** — `huly_sync.js`, `huly_check.js` run as no_agent cron (no Hermes session → no MCP context)

---

## Self-Hosted Deployment (DS920+)

Huly is self-hosted on the Synology DS920+ NAS as well as using Huly Cloud.

| Detail | Value |
|--------|-------|
| URL | `http://192.168.1.53:8087` |
| Server | Synology DS920+ (20GB RAM, 14TB HDD, 4TB SSD cache) |
| Docker | v24.0.2, Compose v2.20.1 |
| Stack | 14 containers (cockroach, redpanda, minio, elastic, + Node.js services) |
| Setup | `/volume1/docker/huly/compose.yml` — cloned from `hcengineering/huly-selfhost` |

### ⚠️ Use `setup.sh --quick`, not manual compose edits (2026-06-15 lesson)

After **5+ hours of troubleshooting** the NAS Huly self-host by manually editing `compose.yml` to add custom `cr_certs_init` / `cr_node_cert` / `cr_client_cert` / `cr_huly_user` init containers (because the standard `start-single-node --insecure --accept-sql-without-tls` couldn't create the `huly` user), the entire problem was solved in 5 minutes by:

```bash
cd /volume1/docker/huly
sudo rm -rf huly                              # nuke the manually-edited version
sudo git clone https://github.com/hcengineering/huly-selfhost.git huly   # fresh clone
cd huly
cp example-huly.conf huly_v7.conf             # copy template
# edit huly_v7.conf: HOST_ADDRESS=192.168.1.53:8087, HTTP_PORT=8087,
#                    CR_USERNAME=huly, CR_USER_PASSWORD=***
sudo bash setup.sh --secret                   # generates SECRET in huly_v7.conf
sudo bash setup.sh --quick                    # writes nginx.conf + docker compose up -d
# 60 seconds later, http://192.168.1.53:8087 is live
```

`hcengineering/huly-selfhost` ships with a battle-tested `setup.sh` that handles:
- cert generation (CA + node + client) in a hidden init container (you don't see it in `compose.yml`, but `docker compose ps` reveals `huly-init-certs-1` etc.)
- user/database creation via `cockroach sql` with certs
- nginx config generation from the template
- `SECRET` generation
- volume path normalization (named volumes vs bind mounts)

**The standard compose.yml looks like it doesn't have cert init containers, but `setup.sh` adds them as ephemeral one-shot containers at runtime.** That's why the bare clone "looks incomplete" — it's not, the setup script completes it.

**Rule of thumb:** When `compose.yml` doesn't have a feature you think it needs, check if `setup.sh` adds it before writing custom init containers yourself. This applies broadly to self-hosted stacks (Gitea, n8n, Plane, etc.) — they often have setup scripts that hide the bootstrapping.

### Quick Start (re-deploy) — `setup.sh --quick` (the right way, 2026-06-15)

**Use the standard `setup.sh` from hcengineering/huly-selfhost — don't hand-edit compose.yml.** See the ⚠️ lesson at the top of this section for the full story; tl;dr is `bash setup.sh --quick` after editing `huly_v7.conf` (copied from `example-huly.conf`).

```bash
# SSH into NAS (key + port)
ssh -i ~/.ssh/id_ed25519_dr2w247 -p 8528 drew@192.168.1.53

# Fresh clone + setup (one-time, only if not already done)
cd /volume1/docker
sudo rm -rf huly                                                    # nuke old version
sudo git clone https://github.com/hcengineering/huly-selfhost.git huly
cd huly
cp example-huly.conf huly_v7.conf                                   # template

# Edit huly_v7.conf — the only required edits for NAS + 8087:
#   HULY_VERSION=v0.7.423
#   HOST_ADDRESS=192.168.1.53:8087
#   HTTP_PORT=8087
#   CR_USERNAME=huly
#   CR_USER_PASSWORD=*** Then:
sudo bash setup.sh --secret   # generates SECRET=*** huly_v7.conf
sudo bash setup.sh --quick    # generates nginx.conf + docker compose up -d

# Check status
sudo docker compose ps

# Monitor account service startup (first run takes 60-120s)
sudo docker compose logs account --tail 10
```

Note: The NAS requires a sudo password. Use `expect` scripts or interactive SSH — `sudo -n` (non-interactive) does NOT work because the SSH session doesn't cache sudo credentials. See `~/.drewgent/scripts/` for reusable expect wrappers or pipe via `ssh -tt`. For the canonical expect + NAS pattern, see `devops/nas-synology-ssh-automation`.

> **For expect + Synology sudo patterns** (the `sleep 2` + `send -- "$password\n"` + `exp_continue` sequence that actually works, plus anti-patterns that don't), see `references/nas-ssh-expect-patterns.md`.

**Initialization:** On first deploy or after deleting `data/cockroach`, CockroachDB creates the single-node cluster. This takes 60-120s. The account service will retry connecting until cockroach is ready. Give it 3-5 minutes before logging in.

### Known Issues (June 2026)

#### 1. Env Variable Naming Mismatch (compose.yml vs .env)

The Huly self-host compose.yml expects variable names that differ from what the stock .env ships:

| compose.yml expects | .env has | Effect |
|-------------------|----------|--------|
| `SECRET` | `SERVER_SECRET` | JWT signing fails: `"Require key"` in account logs |
| `CR_USER_PASSWORD` | `CR_PASSWORD` | CockroachDB password unset → auth failures |
| `HTTP_BIND` | (missing) | Nginx bind address (empty=all interfaces) |
| `REDPANDA_ADMIN_USER`/`REDPANDA_ADMIN_PWD` | (missing) | Kafka broker warnings |

**Fix:** Add the missing aliases to `.env`:
```bash
grep '^SERVER_SECRET=' .env | head -1 >> .env  # copies value as SECRET=...
grep '^CR_PASSWORD=' .env | head -1 >> .env    # copies value as CR_USER_PASSWORD=...
echo 'HTTP_BIND=' >> .env
echo 'REDPANDA_ADMIN_USER=admin' >> .env
echo 'REDPANDA_ADMIN_PWD=redpanda_secret' >> .env
```

#### 2. CockroachDB Certificate Permissions on Synology NAS (superseded)

> **Do NOT use the `--insecure` workaround below.** It was the path we tried first; it doesn't work on cockroach v24.2 (see "There is no good `--insecure` path" note at the end of this section). Use the canonical `setup.sh --quick` instead (see the "Working path" section below).

The original symptom (kept for archaeology):

```
key file certs/node.key has permissions -r-xr-xr-x, exceeds -rwxr-----
```

On Synology DSM, the ext4 filesystem applies 0777 (`rwxrwxrwx+`) to all Docker-mounted files due to ACL inheritance. CockroachDB strictly requires private keys (`*.key`) to be at most 0700. `chmod` on the host does not stick.

**Fix:** Run cockroach in `--insecure` mode. Modify `compose.yml`:
```yaml
services:
  cockroach:
    command: start-single-node --insecure --accept-sql-without-tls
    # Remove: $VOLUME_CR_CERTS_PATH:/cockroach/certs
```
Then remove the certs bind mount and delete the old certs directory:
```bash
sed -i '/VOLUME_CR_CERTS_PATH/d' compose.yml
rm -rf data/cockroach-certs
```

**Caveat (root cause confirmed 2026-06-15, refined after second attempt):** With `--insecure` AND a leftover `data/cockroach` from a previous secure-mode run, cockroach starts in insecure mode but the `COCKROACH_USER` / `COCKROACH_DATABASE` / `COCKROACH_PASSWORD` env vars are **silently ignored** by the official cockroachdb image (they're postgres/mariadb conventions, not cockroach's — the entrypoint script has no `CREATE USER` line). Result: the `huly` user/db never gets created, and account service loops with `password authentication failed for user huly`.

**Additional hard constraint (cockroach v24.2):** Insecure mode **rejects passwords outright**. `CREATE USER huly WITH PASSWORD '...'` fails with `setting or updating a password is not supported in insecure mode`. The user must be created without a password, and every service's `HULY_DB_CONNECTION` URL must also drop its password segment. The `.env` `CR_PASSWORD` / `CR_USER_PASSWORD` vars are dead weight under `--insecure` — leave them for forward compat with a future secure-mode deploy.

**There is no good `--insecure` path. Use secure mode with cr_certs init container.** Verified 2026-06-15 over two sessions: the `--insecure` path is fundamentally broken because (a) passwords can't be set, (b) `cockroach sql --url` only works in a ~30-90s "insecure window" before the cluster promotes itself to secure mode, and (c) once promoted, even root without password fails with `password authentication failed for user root@localhost`. The first `SHOW USERS` call right after fresh init succeeds; the second call 30 seconds later fails. **The only working path is secure mode + cr_certs init container chain.**

### Working path: use `setup.sh --quick` (the canonical, upstream-supported path)

> **The previous 5+ hours spent hand-rolling cr_certs init containers (documented in the legacy section below) were entirely unnecessary.** The correct path is `setup.sh --quick` from `hcengineering/huly-selfhost`, which adds the cert init containers at runtime and handles the user/db creation. If you ever find yourself editing `compose.yml` to add init containers for cert generation, **stop** and run `setup.sh --quick` first — it solves the same problem with upstream-tested code.

### Legacy: hand-rolled cr_certs init containers (kept for archaeology, **DO NOT USE**)

> The section below is preserved only so future agents can recognize the failure mode and understand what the underlying problem actually was. It is **NOT** a working path. If you reach for it, run `setup.sh --quick` instead.

The 5-hour lesson (kept for context):

1. **Change `cockroach` service in compose.yml** — drop `--insecure`, use certs:
   ```yaml
   services:
     cockroach:
       image: cockroachdb/cockroach:latest-v24.2
       command: start-single-node --certs-dir=/certs --ca-cert=/certs/ca.crt --cert=/certs/node.crt --key=/certs/node.key --advertise-addr=localhost
       environment:
         - COCKROACH_DATABASE=${CR_DATABASE}
         - COCKROACH_USER=${CR_USERNAME}
         - COCKROACH_PASSWORD=${CR_U...ORD}
       volumes:
         - ${VOLUME_CR_DATA_PATH:-cr_data}:/cockroach/cockroach-data
         - cr_certs:/certs          # <-- ADD THIS
       restart: unless-stopped
       networks:
         - huly_net
   ```

2. **Add cert init containers + a `cr_huly_user` init container** between `cockroach` and `redpanda` in compose.yml:
   ```yaml
     cr_certs:
       image: cockroachdb/cockroach:latest-v24.2
       command: cert create-ca --certs-dir=/certs --ca-key=/certs/ca.key
       volumes:
         - cr_certs:/certs
       networks:
         - huly_net

     cr_node_cert:
       image: cockroachdb/cockroach:latest-v24.2
       command: cert create-node localhost cockroach --certs-dir=/certs --ca-key=/certs/ca.key
       depends_on: [cr_certs]
       volumes:
         - cr_certs:/certs
       networks:
         - huly_net

     cr_client_cert:
       image: cockroachdb/cockroach:latest-v24.2
       command: cert create-client root --certs-dir=/certs --ca-key=/certs/ca.key
       depends_on: [cr_certs]
       volumes:
         - cr_certs:/certs
       networks:
         - huly_net

     cr_huly_user:
       image: cockroachdb/cockroach:latest-v24.2
       command: >-
         sh -c "
           sleep 10 &&
           cockroach sql --certs-dir=/certs --ca-cert=/certs/ca.crt
             --cert=/certs/client.root.crt --key=/certs/client.root.key
             -e \"CREATE USER huly WITH PASSWORD '$$CR_USER_PASSWORD';
                 CREATE DATABASE IF NOT EXISTS huly;
                 GRANT ALL ON DATABASE huly TO huly;\"
         "
       depends_on: [cr_client_cert, cockroach]
       volumes:
         - cr_certs:/certs
       environment:
         - CR_USER_PASSWORD=${CR_U...ORD}
       restart: on-failure
       networks:
         - huly_net
   ```

   Notes on the cr_huly_user init container:
   - `sleep 10` waits for cockroach to actually accept TLS connections (the cluster has to initialise before `cockroach sql` works, even with certs).
   - The `$$CR_USER_PASSWORD` in the compose heredoc escapes for docker-compose interpolation. Single `$` would be interpolated by compose itself; we want the value baked into the shell command.
   - `restart: on-failure` — if cockroach is still initialising when the init runs, the container will retry until it succeeds.
   - This init container removes the need for any out-of-band `cockroach sql` calls from the host. Everything is self-bootstrapping.

3. **Make sure the `cr_certs` named volume exists** in the `volumes:` section at the bottom of compose.yml. `hcengineering/huly-selfhost`'s default compose already defines it.

4. **Bring it up**:
   ```bash
   cd /volume1/docker/huly
   # Wipe any old insecure-mode data so the cluster is clean
   sudo rm -rf data/cockroach
   sudo mkdir -p data/cockroach
   sudo docker compose up -d
   # Wait 3-5 min for cockroach init + cert init containers to run
   sudo docker compose ps
   sudo docker compose logs account --tail 20
   ```

5. **Verify huly user got created**:
   ```bash
   sudo docker exec huly-cockroach-1 cockroach sql \
     --certs-dir=/certs --ca-cert=/certs/ca.crt \
     --cert=/certs/client.root.crt --key=/certs/client.root.key \
     -e "SHOW USERS; SHOW DATABASES;"
   ```
   You should see `huly` in the users list and `huly` in the databases list.

6. **Open the web UI**: `http://192.168.1.53:8087` — register the first admin account.

### Insecure window — what is it and why can't we rely on it

For host-side manual bootstrapping (when you can't edit compose.yml), you can run `cockroach sql` from the host **within ~30-90 seconds** of `docker compose up -d` on a fresh `data/cockroach`. After that window, cockroach promotes to secure mode and root without password fails. The cr_certs init container approach above removes this race entirely — run it from compose, on startup, every time.

### Legacy: the old Path A / Path B section was DELETED

Earlier revisions of this skill described an `--insecure` Path A (drop password from DB_URL) and Path B (manual `CREATE USER` from host). Both are non-working on cockroach v24.2 in practice. They are kept in git history for archaeology but should not be followed. If you reach for `--insecure`, stop and use the cr_certs path above.

### Three cockroach v24.2 CLI gotchas that bite during any manual fix

- `cockroach sql` called **without `--url`** silently attempts to connect as the current shell user (`huly` from `COCKROACH_USER` env), looping into the same auth failure. **Always pass `--url='postgresql://user:pass@host:port/dbname?sslmode=disable'` explicitly** (insecure) or `--certs-dir=...` (secure).
- The URL **must include a db name** in the path (`/huly`, `/defaultdb`, etc.) — `?sslmode=disable` alone in the query string fails to connect.
- Don't use `CREATE USER IF NOT EXISTS` — cockroach doesn't support that syntax variant. Use `CREATE USER` and catch the "already exists" error if running repeatedly.
- **`cockroach sql` only accepts `--certs-dir` as a single umbrella flag** in v24.2. Don't pass individual `--ca-cert`/`--cert`/`--key` flags — they error with `ERROR: unknown flag: --ca-cert`. The cert files produced by `cert create-ca` / `cert create-client` land in the right structure for `--certs-dir` to find them.
- **First-boot insecure window is short (~30-90s)**: cockroach starts in insecure mode, then promotes to secure mode once the cluster initialises. If you wait >2 min after `docker compose up -d`, `cockroach sql --url='postgresql://root@...'` will start failing with `password authentication failed for user root@localhost`. Either run the `CREATE USER`/`CREATE DATABASE` commands immediately after start, OR delete `data/cockroach` again to re-enter the window.

#### 3. Bind Mount Directory Not Auto-Created

Docker Compose does NOT create bind-mount host directories. `docker compose up -d` fails with:
```
Bind mount failed: '/volume1/docker/huly/data/cockroach' does not exist
```

**Fix:** Create the directory before starting the service:
```bash
mkdir -p data/cockroach
```

Named volumes (`VOLUME_*_PATH` unset → Docker internal volume) are auto-created; only explicit host bind mounts (absolute paths) need pre-creation.

#### 4. Auth Separate from Cloud

Self-host auth is independent of Huly Cloud MCP. MCP JWT tokens from huly.app/settings/integrations DO NOT work for self-hosted login. Self-hosted uses its own account service at port 3000 internally. Create the initial admin account via the web UI at `http://<nas-ip>:8087`.

#### 5. `envsubst` is not on Synology DSM by default — `setup.sh` silently fails

`setup.sh` uses `envsubst` to inject the `SECRET`, `HULY_VERSION`, and other values into `huly_v7.conf` / `.env` / compose templates. On Synology DSM (no `gettext` package preinstalled), `envsubst` is missing — `setup.sh` silently fails the envsubst step and the resulting `huly_v7.conf` becomes a **0-line empty file**. docker compose then runs with `DOCKER_NAME`, `HULY_VERSION`, `SECRET`, `CR_DB_URL`, `HOST_ADDRESS`, `DESKTOP_CHANNEL` all blank — visible as `WARN[0000] The "X" variable is not set. Defaulting to a blank string.` for every service.

**Detection:** After `setup.sh --quick`:
```bash
wc -l huly_v7.conf          # if this is 0, envsubst failed
docker compose config      # will show "blank string" warnings for every $VAR
```

**Fix:** Bypass envsubst entirely. Docker compose reads `.env` directly — if you write `.env` with the correct values, compose is happy without envsubst:

```bash
cd /volume1/docker/huly
# .env is a symlink to huly_v7.conf in upstream — populate huly_v7.conf instead
SECRET_VAL=$(cat .huly.secret)
CR_PW_VAL=$(cat .cr.secret)
RP_PW_VAL=$(cat .rp.secret)
cat > huly_v7.conf <<HULYCONF
HULY_VERSION=v0.7.423
DOCKER_NAME=huly
HOST_ADDRESS=192.168.1.53:8087
SECURE=
HTTP_PORT=8087
HTTP_BIND=
TITLE=Huly Self Host
DEFAULT_LANGUAGE=en
LAST_NAME_FIRST=true
REDPANDA_ADMIN_USER=superadmin
REDPANDA_ADMIN_PWD=$RP_PW_VAL
CR_DATABASE=huly
CR_USERNAME=huly
CR_USER_PASSWORD=$CR_PW_VAL
SECRET=$SECRET_VAL
DESKTOP_CHANNEL=0.7.423
HULYCONF
# .env is already a symlink to huly_v7.conf from upstream — no separate file needed
ls -la .env   # should show .env -> huly_v7.conf
```

**Why this works:** Docker compose's built-in `.env` reader is independent of `envsubst` (which is just one tool upstream happens to use to template `huly_v7.conf`). Compose reads `KEY=VALUE` lines from the file and uses them as variable bindings. No template engine needed.

**To get the secret values for hand-filling, run the secret files generation separately first:**
```bash
sudo bash setup.sh --secret
# This writes .huly.secret, .cr.secret, .rp.secret (65-byte hex each)
# These are the values you then paste into huly_v7.conf
```

**If you don't fix the empty huly_v7.conf, `docker compose up -d` will still succeed but every service will misbehave** — account service loops on missing config, transactor can't bind, etc. The HTTP front-end will return 200 (it just serves static files) but nothing works behind it.

**Long-term fix on the NAS:** install `gettext` package via Synology Package Center (if available) or via `opkg` (requires ipkg/entware). On most DSM installs, the cleanest path is just to hand-fill `huly_v7.conf` as above.

#### 6. `.env` is a symlink to `huly_v7.conf` — don't write a separate `.env`

The upstream `huly-selfhost` repo has a `.gitignore` rule that excludes `.env` from version control but the working `.env` in your local clone is **a symlink to `huly_v7.conf`**, not a copy. So:

- Editing `huly_v7.conf` automatically updates `.env` (no separate edit needed)
- Writing a new `.env` (e.g. `cat > .env`) **clobbers the symlink** with a regular file, breaking the link — then any future edit to `huly_v7.conf` doesn't reach docker compose anymore
- Removing the symlink: `rm .env && ln -s huly_v7.conf .env`

**Verification:** `ls -la .env` should show `.env -> huly_v7.conf`. If it shows `-rw-r--r--`, you have a regular file, not a symlink.

### Content Review Pipeline (Planned)

```mermaid
graph LR
    A[Content-manager] --> B[Draft files]
    B --> C[Huly issue: Todo]
    C --> D[User reviews in Huly UI]
    D --> E[Huly issue: Done]
    E --> F[Watcher -> WordPress push]
    F --> G[humanerd.kr]
```

## Direct SDK (Node.js / @hcengineering/api-client)

### Quick Start

### 1. Get an API Token

Huly Cloud: **Settings → Workspace General → API Access → Generate API Token**

This produces a JWT token valid for WebSocket connections. Save it to `~/.hermes/.env` as `HULY_KEY`.

### 2. Install API Client

```bash
npm install @hcengineering/api-client
```

Available on the public npm registry (no GitHub token needed).

### 3. Connect and Create an Issue

```javascript
// Polyfill window for Huly's browser WebSocket dependency
if (typeof globalThis.window === 'undefined') {
  globalThis.window = { addEventListener: () => {} };
}

const { connect, NodeWebSocketFactory } = require('@hcengineering/api-client');

async function main() {
  const client = await connect('https://huly.app', {
    token: process.env.HULY_KEY,
    workspace: 'your-workspace-slug',
    WebSocketFactory: NodeWebSocketFactory,
  });

  // Create an issue (use addCollection — createDoc fails for AttachedDoc)
  await client.addCollection(
    'tracker:class:Issue',   // issue class
    'tracker:project:DefaultProject',  // space (tracker project ID)
    'tracker:project:DefaultProject',  // attachedTo
    'core:class:Space',       // attachedToClass
    'issues',                 // collection name on the parent
    {
      title: 'Issue title',
      description: 'Issue body (markdown supported)',
    }
  );

  // Query existing issues
  const issues = await client.findAll('tracker:class:Issue', {});
  console.log(`Found ${issues.length} issues`);

  await client.close();
}
```

## API Reference

### Connection

```javascript
const client = await connect('https://huly.app', {
  token: '<JWT_TOKEN>',
  workspace: '<workspace-slug>',
  WebSocketFactory: NodeWebSocketFactory,  // required for Node.js
});
```

- Base URL is always `https://huly.app` for Huly Cloud
- Workspace slug is the path segment from the workbench URL (`https://huly.app/workbench/{slug}/`)
- `NodeWebSocketFactory` is essential — the default `BrowserWebSocketFactory` references `window`

### CRUD Operations

| Operation | Method | Notes |
|-----------|--------|-------|
| Find all | `client.findAll(className, filter)` | e.g. `'tracker:class:Issue'` |
| Find one | `client.findOne(className, filter)` | |
| Create doc | `client.createDoc(className, spaceId, attrs)` | Only works for standalone docs (not `AttachedDoc` subclasses) |
| Add collection | `client.addCollection(className, space, attachedTo, attachedToClass, collection, attrs)` | Required for `AttachedDoc` classes like `Issue` |
| Update | `client.updateDoc(className, spaceId, objectId, operations)` | |
| Remove | `client.removeDoc(className, spaceId, objectId)` | |

### Key Classes

| Class ID | Description |
|----------|-------------|
| `tracker:class:Issue` | Issues/tasks (extends `task:class:Task` → `core:class:AttachedDoc`) |
| `core:class:Space` | Spaces/projects (has 27 instances in a typical workspace) |
| `contact:class:Organization` | Organizations |
| `contact:class:Employee` | Employee/team member |
| `chunter:class:Channel` | Chat channels |

### Important: Issue Creation

`Issue` is an `AttachedDoc` — it must use `addCollection`, not `createDoc`. For top-level issues:

```javascript
await client.addCollection(
  'tracker:class:Issue',
  projectId,           // e.g. 'tracker:project:DefaultProject'
  projectId,           // parent document (the project itself)
  'core:class:Space',  // parent document class
  'issues',            // collection name
  { title, description }
);
```

### Finding the Tracker Project

```javascript
const spaces = await client.findAll('core:class:Space', {});
const trackerProject = spaces.find(s => s._id === 'tracker:project:DefaultProject');
```

The default tracker project has ID `tracker:project:DefaultProject`. Custom projects have UUID-based IDs (e.g. `6a2d4e8b...`).

### Querying Issues

```javascript
const issues = await client.findAll('tracker:class:Issue', {});
// Each issue has: title, description, status, assignee, space, identifier, number, priority, ...
```

## Known Pitfalls

### `.js` Scripts Fail in no_agent Cron

The Hermes cron scheduler's `_run_job_script()` dispatches scripts by file extension: `.sh`/`.bash` run via bash, everything else (`.js`, `.py`, etc.) runs via Python's `sys.executable`. A `.js` file executed by Python produces a SyntaxError on any non-ASCII character (e.g. `—` U+2014 in comments).

**Fix:** Wrap Node.js scripts in a `.sh` wrapper that reads `HULY_KEY` from `.env` and calls `node`:

```bash
#!/bin/bash
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR" || exit 1
HULY_KEY="$(grep '^HULY_KEY=' "$HOME/.hermes/.env" | head -1 | cut -d= -f2-)"
export HULY_KEY
exec node huly_sync.js 2>&1
```

Then set `script: huly_sync.sh` in the cron job, not `huly_sync.js`.

### Credential Masking Breaks Inline Code

### `window is not defined` (Node.js)

The Huly client-resources package references `window.addEventListener("beforeunload", ...)` in its Connection constructor. This only exists in browsers.

**Fix:** Polyfill `window` before importing the API client:
```javascript
if (typeof globalThis.window === 'undefined') {
  globalThis.window = { addEventListener: () => {} };
}
```

### `createDoc cannot be used for objects inherited from AttachedDoc`

`Issue`, `Task`, and most business objects extend `AttachedDoc` and must use `addCollection` instead of `createDoc`.

### `error code: 1010` (403 Forbidden)

All endpoints return 403 with `error code: 1010` when the API URL or auth mechanism is wrong. Huly Cloud uses a **WebSocket** primary protocol — REST endpoints at `https://huly.app/api/v1/*` return 403. Use the `@hcengineering/api-client` package instead.

### `domain not found: card:class:Space`

Use `core:class:Space` (not `card:class:Space`) for querying spaces.

### Credential Masking Breaks Inline Code

When writing Node.js/Python scripts that contain `process.env.HULY_KEY` or API key literals, the system's credential masking replaces them with `***` which breaks syntax. **Workaround:** Write scripts to files via `write_file` tool (handles obfuscation correctly) and read API keys from env vars or a separate temp file (`/tmp/huly_api_key.txt`). Alternatively, use `process.env[ENV_NAME]` with `ENV_NAME = 'HULY_KEY'` to avoid the literal match.

## Real-Time Event Bridge (pushHandler)

Huly Cloud has NO webhook support. Instead, the WebSocket connection supports registering a handler that receives ALL workspace transactions in real-time.

### Access Path

The pushHandler is on the RAW WebSocket Connection object, nested 4 levels deep:

```javascript
const client = await connect('https://huly.app', { token, workspace, WebSocketFactory });

// PlatformClientImpl → TxOperations → createClient result → raw Connection
const rawConn = client.client.client.conn;

rawConn.pushHandler((...txArr) => {
  for (const tx of txArr) {
    if (tx._class?.endsWith('TxCreateDoc') && tx.objectClass === 'tracker:class:Issue') {
      // Real-time notification of new Huly issues
      console.log('New issue:', tx.attributes?.title);
    }
    if (tx._class?.endsWith('TxUpdateDoc') && tx.objectClass === 'tracker:class:Issue') {
      // Issue status/title changed
      console.log('Issue updated:', tx.operations);
    }
  }
});
```

### Transaction Types

| Tx Class | Meaning | Key Fields |
|----------|---------|------------|
| `TxCreateDoc` | Document created | `objectId`, `objectClass`, `attributes` |
| `TxUpdateDoc` | Document updated | `objectId`, `objectClass`, `operations` |
| `TxRemoveDoc` | Document removed | `objectId`, `objectClass` |
| `TxMixin` | Mixin applied | `objectId`, `objectClass`, `attributes` |

### Bridge Daemon (Production)

Deployed as a launchd daemon at `ai.drewgent.huly-bridge` (PID verified running):

| File | Path |
|------|------|
| Node.js script | `~/.drewgent/scripts/huly_bridge.js` |
| Bash wrapper | `~/.drewgent/scripts/huly_bridge.sh` |
| launchd plist | `~/Library/LaunchAgents/ai.drewgent.huly-bridge.plist` |
| Log | `~/.drewgent/logs/huly-bridge.log` |

**Behavior:**
- Connects to Huly, registers pushHandler
- New `tracker:class:Issue` → runs `kanban_create()` (→ dispatcher spawns worker)
- Auto-reconnect with exponential backoff (1s → 60s max)
- launchd auto-restarts on crash (KeepAlive, SuccessfulExit=false, ThrottleInterval=10)

**Commands:**
```bash
launchctl load ~/Library/LaunchAgents/ai.drewgent.huly-bridge.plist   # start
launchctl stop ai.drewgent.huly-bridge                                  # stop
launchctl list ai.drewgent.huly-bridge                                  # status
tail -f ~/.drewgent/logs/huly-bridge.log                                # log
```

### Architecture Without Webhooks

```
Huly Server ──WebSocket──→ client.client.client.conn
                               │ pushHandler
                               ▼
                          bridge daemon
                               │
                    ┌──────────┼──────────┐
                    ▼          ▼          ▼
              Issue         Issue     (future:
              Created       Updated    status
                    │          │        notify)
                    ▼          ▼
              kanban      [logs /
              create     Discord msg]
```

## Kanban → Huly Sync

### Cron Job: huly-kanban-sync (every 120m, no_agent)

Pushes recently completed Hermes kanban tasks to Huly as new Issues.

```bash
# Script: ~/.drewgent/scripts/huly_sync.sh → huly_sync.js
# Cron: job fc33f33c8b47 in ~/.drewgent/cron/jobs.json
# Token: HULY_KEY from ~/.drewgent/.env
# Duplicate check: by title
```

### Cron Job: huly-check-discord (every 30m, no_agent)

Polls Huly for recent changes, posts to Discord #agent-chat when there are updates.

```bash
# Script: ~/.drewgent/scripts/huly_check.sh → huly_check.js
# Cron: job e38860f7e162 in ~/.drewgent/cron/jobs.json
# Silent when no changes (empty stdout = no delivery)
```

### Total Integration Architecture

```
Huly Issue created (by user in UI)
    ↓ REAL-TIME (pushHandler)
huly_bridge.js ──→ kanban create ──→ Drewgent dispatcher ──→ worker spawns
    ↓                                                                  ↓
huly_check.js (30min polling)                                worker completes
    ↓                                                                  ↓
Discord #agent-chat                                          huly_sync.js (120min)
                                                                    ↓
                                                              Huly issue status update
```

## Kanban → Huly Sync Architecture

See `scripts/huly_sync.js` in `~/.drewgent/scripts/` for the production sync script.

```
Drewgent kanban (done tasks)
    ↓ (every 120m via cron job, no_agent)
huly_sync.js (Node.js)
    ↓ (@hcengineering/api-client WebSocket)
Huly Cloud → tracker:project:DefaultProject
    ↓
Issues created as "[Kanban] title"
```

**Duplicate prevention:** Script checks existing issue titles before creating new ones.

**Cron job:** Registered in `~/.drewgent/cron/jobs.json` as `huly-kanban-sync` (job_id `fc33f33c8b47`). Runs every 120m, no_agent, script `huly_sync.js`.

**Env setup:** `HULY_KEY` stored in `~/.drewgent/.env`.

## Discord Webhook Bridge

Huly does NOT expose webhook config via API. To receive notifications in Discord:

1. **Discord webhook URL**: Channel → Integrations → Webhooks → Create. URL format: `https://discord.com/api/webhooks/{id}/{token}`
2. **Huly registration**: Settings → Integrations → Webhooks → paste Discord URL
3. Select events: Issues created/updated, Projects changed

### Alternative: LLM Watch

If Discord webhook isn't configured, a cron job with Discord delivery can periodically check kanban state. Register a no_agent cron job in `~/.drewgent/cron/jobs.json` with:
- `schedule`: `every 60m`
- `deliver`: `discord:1479507905276267553`
- `prompt`: "Summarize recent Huly workspace activity briefly"
```
