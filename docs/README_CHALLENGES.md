## Challenge Template Structure

Challenge templates are maintained in [challenges/_templates](../challenges/_templates), grouped by family:

| Family | Type | Use Case | Example |
|--------|------|----------|---------|
| `web` | Docker | Web applications, login forms, SQL injection | `challenges/web/simple-login/` |
| `osint` | Static | OSINT, RECON tasks, documents | `challenges/osint/template-example/` |
| `sandbox` | Docker | Isolated environments, VMs, system challenges, SSH labs | `challenges/sandbox/ssh-lab/` |
| `reverse` | Docker | Reverse engineering, binary analysis | `challenges/reverse/simple-exe/` |
| `pwn` | Docker | Exploitation, buffer overflows, ROP | `challenges/pwn/basic-overflow/` |

**Important:** Do not deploy folders under `_templates` directly. Always generate a dedicated challenge directory first.

---

## Required File Structure

### Docker Challenge (e.g., web, sandbox, reverse, pwn)

Minimum files required:

```
challenges/web/my-challenge/
├── challenge.yml          # Metadata (name, points, author, tags)
├── Dockerfile             # Container image definition
├── docker-compose.yml     # Service composition & port mapping
├── app.py                 # Application code (or equivalent)
├── requirements.txt       # Python dependencies
├── flag.txt               # Flag content (for reference/testing)
└── README.md              # Deployment & testing instructions (optional)
```

**Example: challenge.yml**
```yaml
name: My Web Challenge
category: Web
difficulty: Medium
points: 100
description: |
  Description of what players do in this challenge.
authors:
  - Your Name
tags:
  - web
  - authentication

instance:
  type: docker-compose
  compose_file: docker-compose.yml
  ports:
    - "5000:5000"
  timeout: 60
```

**Example: docker-compose.yml**
```yaml
version: '3.8'
services:
  app:
    build: .
    container_name: my-challenge-${TEAM_ID:-0}
    ports:
      - "${PORT:-5000}:5000"
    environment:
      - FLAG=${FLAG:-FLAG{placeholder}}
    restart: always
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/health"]
      interval: 10s
      timeout: 5s
      retries: 3
```

### Static Challenge (e.g., osint)

Minimum files required:

```
challenges/osint/my-challenge/
├── challenge.yml           # Metadata
├── README.md               # Challenge description & hints
└── resources/              # Evidence files, documents, images
    ├── document.pdf
    └── image.jpg
```

**Example: challenge.yml (static)**
```yaml
name: My OSINT Challenge
category: OSINT
difficulty: Easy
points: 50
description: |
  Find information from provided resources.
authors:
  - Your Name
type: static
instance:
  type: static
  resources_dir: resources/
```

---

## Challenge Deployment Workflow

### Step 1: Create Challenge from Template

**Windows PowerShell:**
```powershell
./scripts/new-challenge.ps1 -Name [my-web-challenge] -Family [web]
```

Values to edit in the command:
- `[my-web-challenge]` = your challenge slug/name
- `[web]` = challenge family (`web`, `osint`, `sandbox`, `reverse`, `pwn`)

**Linux / macOS:**
```bash
bash ./scripts/new-challenge.sh [my-web-challenge] --family [web]
```

This generates a new directory at `challenges/[web]/[my-web-challenge]/` with template files.

### Step 2: Customize Challenge

Edit the generated files:
- Update `challenge.yml` with actual name, description, points
- Modify `app.py` with your challenge logic
- Update `requirements.txt` with dependencies
- Set correct `FLAG` value
- Customize `Dockerfile` if needed
- Ensure `docker-compose.yml` has correct port mapping

### Step 3: Validate Challenge Structure

**Windows PowerShell:**
```powershell
./scripts/validate-challenge.ps1 -Path challenges/web/my-web-challenge
```

**Linux / macOS:**
```bash
bash ./scripts/validate-challenge.sh challenges/web/my-web-challenge
```

Validation checks:
- ✅ All required files present
- ✅ Valid YAML syntax
- ✅ Port mappings unique (no collisions)
- ✅ No development secrets in code

### Step 4a: Test Locally (Direct Docker Compose)

For quick iteration without orchestrator:

```bash
# SSH into VM
vagrant ssh

# Navigate to challenge
cd /vagrant/challenges/web/my-web-challenge

# Build and run
docker compose up -d --build

# Test
curl http://localhost:5000

# Clean up
docker compose down
```

### Step 4b: Test via Orchestrator API (Recommended)

Deploy isolated per-team instance:

```bash
# Generate signature (run directly in your shell, no file required)
ts=$(date +%s)
body='{"challenge": "my-web-challenge", "team_id": "1", "ttl_min": 60}'
sig=$(printf "%s.%s" "$ts" "$body" | \
  openssl dgst -sha256 -hmac "ChangeMe-Orchestrator-Signing-Secret" -binary | \
  xxd -p -c 256)

# Start instance via orchestrator
curl -X POST http://192.168.56.10:8181/start \
  -H "X-Orchestrator-Token: ChangeMe-Orchestrator-Token" \
  -H "X-Signature-Timestamp: $ts" \
  -H "X-Signature: $sig" \
  -H "Content-Type: application/json" \
  -d "$body" | jq '.'

# Response includes port assignment
# {"ok": true, "port": 6101, "url": "http://192.168.56.10:6101", ...}

# Access challenge
curl http://192.168.56.10:6101

# Stop instance when done
ts=$(date +%s)
body='{"challenge": "my-web-challenge", "team_id": "1"}'
sig=$(printf "%s.%s" "$ts" "$body" | \
  openssl dgst -sha256 -hmac "ChangeMe-Orchestrator-Signing-Secret" -binary | \
  xxd -p -c 256)

curl -X POST http://192.168.56.10:8181/stop \
  -H "X-Orchestrator-Token: ChangeMe-Orchestrator-Token" \
  -H "X-Signature-Timestamp: $ts" \
  -H "X-Signature: $sig" \
  -d "$body"
```

What these variables do:
- `ts`: current Unix timestamp used by server-side replay protection.
- `body`: exact JSON payload sent to the API.
- `sig`: HMAC-SHA256 signature computed from `"<timestamp>.<body>"`.

Important:
- You should execute these commands directly in terminal (TTY).
- `sig` must be recomputed every time `ts` or `body` changes.
- For production, never keep `ChangeMe-...` secrets; use real values from Vault-managed config.

### Step 5: Commit & Submit PR

```bash
git add challenges/web/my-web-challenge/
git commit -m "feat(challenges): add my-web-challenge"
git push -u origin feat/my-web-challenge
# Create PR on GitHub
```

CI will automatically:
- Run validation
- Check for security issues
- Verify Dockerfile builds

CI details:
- Challenge CI: `.github/workflows/challenge-validation.yml` (triggered on challenge changes in PR/push)
- Security CI: `.github/workflows/security-preflight.yml` (triggered on security-config related changes)

---

## Challenge Configuration Details

### challenge.yml Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | ✓ | Display name |
| `category` | string | ✓ | Challenge type (Web, reverse, pwn, etc.) |
| `difficulty` | string | ✓ | Easy, Medium, Hard |
| `points` | integer | ✓ | Points awarded for solving |
| `description` | string | ✓ | What players do ("Find the flag", etc.) |
| `authors` | list | ✓ | Challenge creators |
| `tags` | list | ✓ | Tags for filtering/searching |
| `instance` | object | ✓ | Deployment config (see below) |
| `connection_mode` | string | optional | `web`, `ssh`, `instruction`, or `auto` for launch-card rendering |
| `ssh_user` | string | optional | Username used to render SSH commands |
| `access_instructions` | string | optional | Human-readable instructions for static/instruction-only challenges |
| `container_port` | integer | optional | Internal container port when it is not the default `5000` |

### instance.type = "docker-compose"

```yaml
instance:
  type: docker-compose
  compose_file: docker-compose.yml      # Path relative to challenge dir
  ports:
    - "5000:5000"                        # Container:Host port mapping
    - "8080:8080"                        # Multiple ports OK
  timeout: 60                            # Instance TTL in seconds (optional)
```

### instance.type = "static"

```yaml
instance:
  type: static
  resources_dir: resources/              # Directory with static content
```

---

## Docker Compose Best Practices

### Environment Variable Injection

Container should accept FLAG and other config via environment:

```dockerfile
# Dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY app.py .
CMD ["python", "app.py"]
EXPOSE 5000
```

```python
# app.py
import os
FLAG = os.environ.get("FLAG", "FLAG{default_for_testing}")

@app.route("/flag")
def get_flag():
    return FLAG
```

### Port Mapping

Use environment variable for dynamic port assignment:

```yaml
# docker-compose.yml
services:
  app:
    ports:
      - "${PORT:-5000}:5000"  # From env, fallback to 5000
    environment:
      - PORT=${PORT}
      - FLAG=${FLAG}
```

Orchestrator provides `PORT` when spawning instances.

### Health Checks

Include a health check endpoint:

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:5000/health"]
  interval: 10s
  timeout: 5s
  retries: 3
  start_period: 10s
```

Orchestrator uses this to verify instance readiness.

### Container Naming

Use dynamic naming to avoid collisions:

```yaml
services:
  app:
    container_name: ${CHALLENGE}-${TEAM_ID}  # e.g., web-01-team-1
```

---

## Optional Deep Local Checks (Before Orchestrator)

Step 4a already covers standard local Compose testing. The checks below are optional when you need deeper debugging.

### Build Docker image

```bash
cd challenges/web/my-challenge
docker build -t my-challenge:latest .
docker run -p 5000:5000 -e FLAG="FLAG{test}" my-challenge:latest
```

### Compose up/down

```bash
docker compose up -d --build
curl http://localhost:5000/health
docker compose down
```

### Python syntax check

```bash
python -m py_compile app.py
python -m flake8 app.py  # Optional: linting
```

---

## Validation Layers

`Step 3: Validate Challenge Structure` is the single-challenge local gate.
This section explains the full validation model (local gate + CI gate).

### Local Validation

Run before commit:

**Windows:**
```powershell
./scripts/validate-challenge.ps1 -Path challenges/web/my-challenge
```

**Linux:**
```bash
bash ./scripts/validate-challenge.sh challenges/web/my-challenge
```

Checks:
- File presence (required files exist)
- YAML syntax (challenge.yml valid)
- Docker syntax (Dockerfile valid)
- Unique ports (no collision with other challenges)
- No security issues (dev defaults, secrets, etc.)

### CI Validation Workflow

When a PR or push includes files under `challenges/**`, `.github/workflows/challenge-validation.yml` runs automatically.

Security checks run in a separate workflow (`.github/workflows/security-preflight.yml`) when security config files change.

Challenge CI runs these checks:

```bash
# Validate all challenge directories
python scripts/validate_challenges_ci.py

# Build all Dockerfiles
for challenge in challenges/*/*/Dockerfile; do
  docker build $(dirname $challenge)
done
```

Summary:
- Local validation script: run manually before commit (fast feedback).
- CI validation: runs automatically after commit/PR based on changed paths.

---

## Commands Only (Fast Path)

Use this compact sequence for the standard flow:

```bash
# 1) create skeleton
bash ./scripts/new-challenge.sh [my-web-challenge] --family [web]

# 2) local structure validation
bash ./scripts/validate-challenge.sh challenges/[web]/[my-web-challenge]

# 3) optional local compose smoke test
vagrant ssh -c "cd /vagrant/challenges/[web]/[my-web-challenge] && docker compose up -d --build && docker compose down"

# 4) commit + push branch
git checkout -b feat/[my-web-challenge]
git add challenges/[web]/[my-web-challenge]
git commit -m "feat(challenges): add [my-web-challenge]"
git push -u origin feat/[my-web-challenge]

# 5) publish to CTFd (recommended path)
python scripts/sync_challenges_ctfd.py --ctfd-url http://192.168.56.10 --api-token <ADMIN_TOKEN> --state visible --instance-base-url http://192.168.56.10
```

Editable values in step 1:
- `[my-web-challenge]`
- `[web]`

---

## Connecting to CTFd

### A) Automatic Deployment (Recommended)

Use the Git -> API sync pipeline documented in [docs/CTFD_CHALLENGE_SYNC.md](CTFD_CHALLENGE_SYNC.md).

Why this is the default:
- Git remains source of truth for challenge metadata.
- Sync is idempotent (create/update safely).
- Reduces drift between repo and CTFd admin UI.

Typical command:

```bash
python scripts/sync_challenges_ctfd.py \
  --ctfd-url http://192.168.56.10 \
  --api-token <ADMIN_TOKEN> \
  --state visible \
  --instance-base-url http://192.168.56.10
```

### B) Manual Deployment (Fallback Only)

Use this only for debug/demo/one-off actions.

After deployment, challenges can be registered in CTFd:

1. Access CTFd: `http://192.168.56.10`
2. Admin panel → Challenges → New Challenge
3. Fill in from `challenge.yml`:
   - Name → `challenge.yml.name`
   - Description → `challenge.yml.description`
   - Points → `challenge.yml.points`
   - Category → `challenge.yml.category`
4. Create challenge
5. For player access: provide orchestrator port (6101, 6102, etc.)

Why manual is not the default:
- It duplicates metadata entry.
- It bypasses idempotent GitOps sync behavior.
- It increases drift risk between `challenge.yml` and CTFd UI state.

---

## Common Issues

### "Port already in use"
```bash
# Change docker-compose.yml port mapping
ports:
  - "5001:5000"  # Changed from 5000
```

### "Docker build fails"
```bash
# Rebuild without cache
docker build --no-cache -t my-challenge .

# Check Dockerfile syntax
docker build --file=Dockerfile .lint
```

### "Health check fails"
```bash
# Verify health endpoint is correct
curl http://localhost:5000/health

# Check logs
docker compose logs app
```

### "Flag not displaying"
```bash
# Verify FLAG env var is set
docker compose exec app env | grep FLAG

# Override in docker-compose
environment:
  - FLAG=FLAG{custom_flag_here}
```

---

## Team Conventions

✅ **DO:**
- Use unique challenge identifiers (`web-01-auth`, not `challenge`)
- Keep challenge.yml synced with implementation
- Test both locally and via orchestrator
- Document any special setup in README
- Include meaningful flag text (not just "flag" or "test")

❌ **DON'T:**
- Hardcode ports (use environment variables)
- Store secrets in Dockerfile or code
- Use `latest` tags (pin versions)
- Deploy template folders directly
- Use manual CTFd form entry as the primary publication path (prefer sync script)
- Modify challenge after players start solving

---

## Recommended End-to-End Pipeline

This is the canonical challenge flow for this repository:

```mermaid
flowchart TD
  A[Step 1: Create challenge from family template] --> B[Step 2: Implement and update challenge.yml]
  B --> C[Step 3: Run local validate script]
  C --> D[Step 4a: Local compose smoke test optional]
  D --> E[Step 4b: Orchestrator API test recommended]
  E --> F[Step 5: Commit and open PR]
  F --> G[CI: challenge-validation workflow]
  F --> H[CI: security-preflight workflow when relevant files change]
  G --> I[Merge to main]
  H --> I
  I --> J[Publish with sync_challenges_ctfd.py]
  J --> K[Final smoke test in CTFd]
```

Quick interpretation:
- Local validation gives fast feedback before you push.
- CI enforces structure and regression checks after PR/push.
- Sync script is the default publication path to CTFd.
- Manual CTFd challenge creation is fallback only.

---

## See Also

- [docs/PLAYER_INSTANCE_ORCHESTRATOR.md](PLAYER_INSTANCE_ORCHESTRATOR.md) - API reference for orchestrator
- [docs/VAULT_SETUP.md](VAULT_SETUP.md) - Managing secrets in challenges
- [challenges/_templates](../challenges/_templates/) - Template source files
- [challenges/web/simple-login](../challenges/web/simple-login/) - Example challenge
