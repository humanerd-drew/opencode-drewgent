# Synology NAS (DS920+) Docker Setup

## Specs
- Model: DS920+ (4-bay, J4125 CPU)
- RAM: 20GB
- Storage: 14TB HDD + 4TB SSD cache
- Docker: 24.0.2
- Docker Compose: v2.20.1

## SSH Access
```bash
# Key-based auth (use the specific key — default id_rsa won't work):
ssh -i ~/.ssh/id_ed25519_dr2w247 -p 8528 drew@192.168.1.53

# Password fallback:
ssh -p 8528 drew@192.168.1.53
```
Password: `Emfbwjsxm4865`

**Key auth note:** The `id_ed25519_dr2w247` key is authorized on the NAS. SSH may try `id_rsa` first by default and fail — always use `-i` to specify the correct key. The key's comment is `dr2w247@github.com` (this is the same key used by the GitHub/automation tooling).

## Docker Access via SSH + Expect
Because Synology DSM requires a TTY for `sudo`, use `expect` scripts for automation:

```tcl
#!/usr/bin/expect -f
set timeout 15
set password "Emfbwjsxm4865"
spawn ssh -o StrictHostKeyChecking=no -p 8528 drew@192.168.1.53
expect "password:"
send "$password\r"
expect "drew@"
send "sudo docker compose -f /path/to/compose.yml up -d\r"
expect "password for drew:"
send "$password\r"
expect "drew@"
send "exit\r"
expect eof
```

## Sudoers Configuration
Created `/etc/sudoers.d/drew-docker` with:
```
drew ALL=(ALL) NOPASSWD: /usr/local/bin/docker
Defaults:drew !requiretty
```

## Docker Compose Directory
All Docker projects live at `/Volumes/humanerd/docker/` on the Mac Mini mount.
Projects: dev-humanerd, n8n, wordpress, nas-agent-browser

## Storage
- 16TB total volume (`/volume1`)
- Mounted via SMB on Mac Mini at `/Volumes/humanerd/` and `/Volumes/drewgent_storage/`
