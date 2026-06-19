# NAS SSH + Docker Setup — Synology DS920+

Used to run Huly, WordPress, or other containers on the NAS. The Mac Mini's Docker (colima) talks to the NAS via SSH for remote Docker commands.

## Equipment

| Item | Spec |
|------|------|
| NAS | Synology DS920+ |
| RAM | 20 GB |
| Storage | 14 TB HDD + 4 TB SSD cache |
| OS | DSM (latest) |
| Docker | v24.0.2 (via DSM Package Center) |
| Docker Compose | v2.20.1 |

## SSH Access

**Port:** 8528 (non-standard, configured in DSM)

**User:** `drew` (DSM admin account, UID 1033)

**Credentials:** See `~/.hermes/.env` (NAS_PASSWORD) or the session credentials record.

### Step 1: Enable SSH on DSM

DSM → **Control Panel → Terminal & SNMP** → Enable SSH service. Port 8528.

### Step 2: Add SSH Public Key

Copy the Mac Mini's public key to the NAS for passwordless login:

```bash
# From the Mac Mini, using sshpass:
sshpass -p '<nas-password>' ssh -p 8528 drew@192.168.1.53 \
  "mkdir -p ~/.ssh && chmod 700 ~/.ssh && cat >> ~/.ssh/authorized_keys" \
  < ~/.ssh/id_ed25519_dr2w247.pub
```

Or manually via expect script if the above is blocked by security tooling:

```expect
#!/usr/bin/expect -f
set timeout 15
set password "<nas-password>"
set pubkey [exec cat ~/.ssh/id_ed25519_dr2w247.pub]
spawn ssh -o StrictHostKeyChecking=no -p 8528 drew@192.168.1.53
expect "password:" { send "$password\r" }
expect "drew@" { send "mkdir -p ~/.ssh && chmod 700 ~/.ssh\r" }
expect "drew@" { send "echo '$pubkey' >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys\r" }
expect "drew@" { send "exit\r" }
expect eof
```

### Step 3: Fix Home Directory Permissions

SSH key auth will fail if `~` has group/world-writable permissions (OpenSSH StrictModes).

```bash
ssh -i ~/.ssh/id_ed25519_dr2w247 -p 8528 drew@192.168.1.53 \
  "chmod 755 ~ && chmod 700 ~/.ssh && chmod 600 ~/.ssh/authorized_keys"
```

### Step 4: Enable Passwordless sudo for Docker

The `drew` user is in the administrators group but cannot use `docker` directly — needs sudo.

```bash
# Create sudoers entry (requires expect for the sudo password prompt):
echo 'Defaults:drew !requiretty' | sudo tee /etc/sudoers.d/drew-docker
echo 'drew ALL=(ALL) NOPASSWD: /usr/local/bin/docker' | sudo tee -a /etc/sudoers.d/drew-docker
sudo chmod 440 /etc/sudoers.d/drew-docker
```

**Pitfall:** Synology sudo requires either a real TTY or `-S` with password. The `!requiretty` entry and `NOPASSWD` together allow `sudo -n` over SSH without a TTY. Without BOTH tags, `docker exec` style automation will fail with "a password is required."

### Verification

```bash
ssh -i ~/.ssh/id_ed25519_dr2w247 -p 8528 drew@192.168.1.53 \
  "sudo -n docker ps && sudo -n docker compose version"
```

Expected output:
```
CONTAINER ID   IMAGE     COMMAND   CREATED   STATUS    PORTS     NAMES
Docker Compose version v2.20.1
```

## Docker on Synology

### Installation

DSM → **Package Center** → Search "Docker" → Install.

Docker runs as a DSM service. The socket is at `/var/run/docker.sock` (owned by `root:root`).

### Data Storage

Docker volumes on Synology should use shared folders for persistence:

```bash
/volume1/docker/          # Main Docker data directory
/volume1/docker/wordpress/  # WordPress uploads + DB
/volume1/docker/huly/      # Huly data (future)
```

Mounted on the Mac Mini at `/Volumes/humanerd/docker/` via SMB.

### Running Docker Compose

```bash
# From Mac Mini, SSH to NAS:
ssh -i ~/.ssh/id_ed25519_dr2w247 -p 8528 drew@192.168.1.53 \
  "cd /path/to/compose && sudo -n docker compose up -d"
```

### Docker API (Optional)

For direct Docker API access, add the `drew` user to the `docker` group (requires creating it first):

```bash
sudo synogroup --create docker
sudo synogroup --member docker drew
```

Then restart the SSH session. The user can now use `docker` without sudo.

**Pitfall:** On Synology DSM, the docker group may not exist by default. Creating it manually and adding the user is required for passwordless docker access. Even without the docker group, `sudo -n docker` works if step 4 is complete.

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `ssh: connect to host NAS port 22: Connection refused` | SSH service not running | DSM → Control Panel → Terminal → Enable SSH |
| `Permission denied (publickey)` | Key not authorized or wrong key used | Verify `~/.ssh/authorized_keys` has the right key, check `~` permissions are 755 |
| `sudo: a terminal is required...` | Missing `!requiretty` in sudoers | Add `Defaults:drew !requiretty` to the sudoers file |
| `sudo: a password is required` | Missing `NOPASSWD` tag | Verify the sudoers entry has `NOPASSWD: /path/to/docker` |
| `docker: command not found` | Docker not in PATH | Use full path `/usr/local/bin/docker`, or add `/usr/local/bin` to PATH in `~/.profile` |
| `Cannot connect to the Docker daemon` | User not in docker group | Use `sudo -n docker`, or add user to docker group |
