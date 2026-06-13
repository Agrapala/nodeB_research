# PoCL CI/CD — Full Docker + Jenkins Setup

Federated learning pipeline for 4 Sri Lanka hospital nodes.
Each hospital laptop runs its own Jenkins that trains locally and ships the model to the central server.

---

## Repository structure

```
pocl-cicd/
├── Jenkinsfile                   # Shared pipeline — same file on all 4 laptops
├── requirements.txt              # Pinned Python deps
├── hospital_node_client.py       # Training + send script
│
├── docker/
│   └── Dockerfile                # Image definition
│
├── scripts/
│   ├── setup_laptop.sh           # One-time laptop setup (run as root)
│   ├── build_and_push.sh         # Build + push image to GHCR
│   └── validate_model.py         # Standalone quality gate checker
│
└── monitoring/
    └── docker-compose.yml        # Central server stack
```

---

## Quick start

### Step 1 — Build and push Docker image (do this once from your dev machine)

```bash
# Login to GitHub Container Registry
echo YOUR_PAT | docker login ghcr.io -u YOUR_GITHUB_USER --password-stdin

# Build and push
bash scripts/build_and_push.sh YOUR_GITHUB_USER
```

### Step 2 — Set up each hospital laptop (run once per laptop)

```bash
# On Colombo laptop:
sudo bash scripts/setup_laptop.sh A

# On Kandy laptop:
sudo bash scripts/setup_laptop.sh B

# On Galle laptop:
sudo bash scripts/setup_laptop.sh C

# On Jaffna laptop:
sudo bash scripts/setup_laptop.sh D
```

### Step 3 — Configure Jenkins on each laptop

1. Open http://localhost:8080
2. Enter initial password:
   ```bash
   sudo cat /var/lib/jenkins/secrets/initialAdminPassword
   ```
3. Install suggested plugins + **GitHub plugin** + **Pipeline plugin**
4. New Item → Pipeline → name: `pocl-hospital-node`
5. Build Triggers → **GitHub hook trigger for GITScm polling**
6. Pipeline → Definition → **Pipeline script from SCM**
7. SCM: Git → your repo URL
8. Script Path: `Jenkinsfile`
9. Save

### Step 4 — Expose Jenkins for GitHub webhook

```bash
# Run on each laptop (keep this terminal open):
ngrok http 8080
# Copy the https://xxxx.ngrok.io URL
```

In GitHub repo → Settings → Webhooks → Add webhook:
- Payload URL: `https://xxxx.ngrok.io/github-webhook/`
- Content type: `application/json`
- Event: `Just the push event`

### Step 5 — Test it

```bash
git commit --allow-empty -m "trigger pipeline test"
git push
```

Watch Jenkins at http://localhost:8080 — all 4 pipelines should start.

---

## Pipeline stages

| Stage | What it does | Re-runs when |
|---|---|---|
| Checkout | `git pull` latest code | Always |
| Pull Docker image | `docker pull` from GHCR | Only if `requirements.txt` or `Dockerfile` changed |
| Train CNN | Runs `hospital_node_client.py --train_only` inside container | Always |
| Validate model | Reads `metadata.json`, checks accuracy/AUC/F1 gates | Always |
| Send model | Runs `hospital_node_client.py --send_only` inside container | Only if validation passes |

---

## Quality gates (edit in Jenkinsfile)

| Metric | Default threshold |
|---|---|
| val_accuracy | ≥ 0.75 |
| val_auc | ≥ 0.80 |
| val_f1 | ≥ 0.72 |

If any gate fails, the build is marked FAILED and the model is **not** sent to the server.

---

## Updating dependencies

When you need to change `requirements.txt`:

```bash
# 1. Edit requirements.txt
# 2. Rebuild and push the image
bash scripts/build_and_push.sh YOUR_GITHUB_USER

# 3. Push to git — webhook triggers pipelines
git add requirements.txt
git commit -m "bump tensorflow to 2.16"
git push
# Each laptop detects requirements.txt changed → pulls new image → trains
```

---

## Node → Hospital mapping

| Node | Hospital | Location |
|---|---|---|
| A | Colombo General Hospital | Colombo, Sri Lanka |
| B | Kandy Teaching Hospital | Kandy, Sri Lanka |
| C | Galle District Hospital | Galle, Sri Lanka |
| D | Jaffna Teaching Hospital | Jaffna, Sri Lanka |