# Huly Self-Host Deployment (DS920+)

Deployed at `/volume1/docker/huly/` on the Synology NAS.

## Services (14 containers)
nginx, cockroach, redpanda, minio, elastic, rekoni, transactor, collaborator, account, workspace, front, fulltext, stats, kvs

## Configuration

### .env File
Located at `/volume1/docker/huly/.env` (symlinked from `huly_v7.conf`).

**Key vars:**
```
HULY_VERSION=v0.7.423
HOST_ADDRESS=192.168.1.53
HTTP_PORT=8087
SERVER_SECRET=*** fix needed — see below)
```

### ⚠️ CockroachDB Connection Issue
The account service fails to connect to the database:
```
Error while initializing postgres account db connect ECONNREFUSED 127.0.0.1:5432
```

**Root cause:** `CR_DB_URL` and related `CR_DATABASE`, `CR_USERNAME`, `CR_PASSWORD` are not set in `.env`. The compose.yml references `${CR_DB_URL}` with no default, so services default to PostgreSQL connection (port 5432) instead of CockroachDB (port 26257).

**Fix:** Add to `.env`:
```
CR_DATABASE=huly
CR_USERNAME=huly  
CR_PASSWORD=huly_sing_node
CR_DB_URL=postgresql://huly:huly_sing_node@cockroach:26257/huly
```

Also, the `compose.yml` has `SERVER_SECRET=***` hardcoded in some service definitions. These should use `${SERVER_SECRET}` variable substitution instead.

## Management Commands
```bash
# Via expect (password required for sudo):
expect << 'EOF'
spawn ssh -i ~/.ssh/id_ed25519_dr2w247 -p 8528 drew@192.168.1.53
expect "drew@"
send "cd /volume1/docker/huly && sudo docker compose up -d\r"
expect "password for drew:"
send "Emfbwjsxm4865\r"
expect "drew@"
send "exit\r"
expect eof
EOF

# Container status:
ssh -i ~/.ssh/id_ed25519_dr2w247 -p 8528 drew@192.168.1.53 "sudo -n docker ps"

# Logs:
ssh -i ~/.ssh/id_ed25519_dr2w247 -p 8528 drew@192.168.1.53 "sudo -n docker compose logs account --tail 30"
```

## Network
- Web UI: `http://192.168.1.53:8087`
- CockroachDB: `cockroach:26257` (internal Docker network)
- Elasticsearch: `elastic:9200`
- MinIO: `minio:9000` (API), `minio:9001` (console)
