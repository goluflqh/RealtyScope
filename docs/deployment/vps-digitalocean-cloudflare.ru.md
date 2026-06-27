# RealtyScope VPS Deployment Runbook

Updated: 2026-06-27

This runbook deploys the same Dockerized runtime used locally for the final RealtyScope demo:

- FastAPI backend;
- Streamlit dashboard;
- PostgreSQL;
- Redis;
- MLflow service inside the Docker network;
- Caddy reverse proxy;
- Dockerized one-shot ingestion job for scheduled bounded Domclick snapshot parsing;
- restored PostgreSQL runtime data;
- restored phase5 model artifact volume.

Public endpoints:

- `https://realtyscope.bond` -> Streamlit UI;
- `https://api.realtyscope.bond` -> FastAPI.

Private services:

- PostgreSQL, Redis, and MLflow must stay inside the Docker network.

## 0. Release gate before Termius

Do not redeploy from Termius until the local branch is actually merged and pushed to `origin/main`.

Local release checklist:

```bash
git status --short --branch
python -m pytest tests/test_api_prediction_contract.py tests/test_streamlit_ui_payload.py tests/test_streamlit_api_client.py tests/test_static_audit_requirements.py tests/test_docker_build_contract.py -q --basetemp output/pytest-tmp -o cache_dir=output/pytest-cache
python -m ruff check services/streamlit/app.py tests/test_streamlit_ui_payload.py tests/test_docker_build_contract.py
git diff --check
```

After merge, confirm:

```bash
git checkout main
git pull --ff-only origin main
git log -1 --oneline
```

Only then export a fresh runtime bundle and deploy through Termius.

## 1. Server baseline

Recommended VPS for the final demo:

- Ubuntu LTS;
- at least `2 vCPU / 2 GB RAM / 60 GB disk`;
- `2 vCPU / 4 GB RAM` is safer for Docker builds;
- SSH key authentication.

Install Docker:

```bash
apt update
apt upgrade -y
apt install -y ca-certificates curl git ufw
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc
. /etc/os-release
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu ${VERSION_CODENAME} stable" > /etc/apt/sources.list.d/docker.list
apt update
apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
docker version
docker compose version
```

Firewall:

```bash
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable
ufw status
```

## 2. Clone the project

```bash
mkdir -p /opt
cd /opt
git clone https://github.com/goluflqh/RealtyScope.git realtyscope
cd /opt/realtyscope
git checkout main
```

## 3. Configure production environment

```bash
cp .env.production.example .env
nano .env
```

Required values:

```text
POSTGRES_USER=realtyscope
POSTGRES_PASSWORD=<strong-random-password>
POSTGRES_DB=realtyscope
APP_DOMAIN=realtyscope.bond
API_DOMAIN=api.realtyscope.bond
ACME_EMAIL=<your-email>
ACTIVE_MODEL_NAME=realtyscope-price-model
ACTIVE_MODEL_ARTIFACT_PATH=data/processed/models/phase5/selected_price_model_v1_non_leaky.joblib
DOMCLICK_SOURCE_PATH=data/raw/domclick/current
DOMCLICK_MAX_RECORDS=2000
DOMCLICK_MIN_NORMALIZED_RECORDS=1000
```

Never commit `.env`.

## 4. Configure DNS / Cloudflare

Create A records pointing to the VPS IPv4:

| Type | Name | Content |
| --- | --- | --- |
| A | `@` | `<VPS_IP>` |
| A | `www` | `<VPS_IP>` |
| A | `api` | `<VPS_IP>` |

SSL/TLS mode should be `Full` or `Full (strict)` once Caddy obtains a valid certificate.

## 5. Build and start production Compose

```bash
cd /opt/realtyscope
docker compose -f docker-compose.prod.yml --env-file .env build
docker compose -f docker-compose.prod.yml --env-file .env up -d
docker compose -f docker-compose.prod.yml --env-file .env ps
```

Check logs:

```bash
docker compose -f docker-compose.prod.yml --env-file .env logs --tail=120 api
docker compose -f docker-compose.prod.yml --env-file .env logs --tail=120 streamlit
docker compose -f docker-compose.prod.yml --env-file .env logs --tail=120 caddy
```

## 6. Restore runtime data and model artifacts

Git stores code and small tracked assets only. The demo also needs runtime bundles:

- PostgreSQL database dump;
- model artifact archive containing `phase5/*.joblib`.

Create the local transfer bundle after local verification:

```bash
cd /mnt/e/Магистр/2-курс/python/RealtyScope-stitch-hybrid-redesign-20260623
bash scripts/deployment/export_local_runtime_bundle.sh ../realtyscope-vps-transfer
```

Expected files:

```text
realtyscope-db-YYYYMMDD.dump
realtyscope-model-artifacts-YYYYMMDD.tar.gz
```

Copy both files to `/opt/realtyscope` on the VPS, then restore:

```bash
cd /opt/realtyscope
bash scripts/deployment/restore_vps_runtime_bundle.sh
```

The restore script:

1. stops API/UI while keeping the database container available;
2. restores the PostgreSQL dump;
3. unpacks model artifacts into the Docker volume `realtyscope_model_artifacts`;
4. restarts `api`, `streamlit`, and `caddy`;
5. performs smoke checks.

## 7. Verify local/VPS parity

Model and asset mounts:

```bash
docker compose -f docker-compose.prod.yml --env-file .env exec -T streamlit test -f /app/data/external/moscow_district_boundaries.geojson
docker compose -f docker-compose.prod.yml --env-file .env exec -T streamlit test -f /app/data/processed/models/phase5/selected_price_model_v1_non_leaky.joblib
docker compose -f docker-compose.prod.yml --env-file .env exec -T api test -f /app/data/processed/models/phase5/selected_price_model_v1_non_leaky.joblib
```

API smoke checks from the VPS:

```bash
curl -fsS http://localhost:8000/health
curl -fsS http://localhost:8000/model/metadata | python3 -m json.tool | head -120
curl -fsS http://localhost:8501/_stcore/health
```

Public smoke checks:

```bash
curl -fsS https://realtyscope.bond/ >/dev/null
curl -fsS https://api.realtyscope.bond/health
curl -fsS https://api.realtyscope.bond/model/metadata | python3 -m json.tool | head -120
```

Prediction smoke:

```bash
curl -fsS -X POST https://api.realtyscope.bond/predict \
  -H 'Content-Type: application/json' \
  -d '{"features":{"building_year":2018,"building_year_missing":0,"coordinates_missing":1,"floor":5,"floor_missing":0,"floors_total":20,"floors_total_missing":0,"healthcare_count_1000m":0,"latitude":55.75,"longitude":37.61,"nearest_transport_m":0,"nearest_transport_m_missing":1,"observation_count":1,"observation_missing":0,"osm_missing":1,"parks_count_1000m":0,"property_type_apartment":1,"rooms":2,"schools_count_1000m":0,"shops_count_1000m":0,"total_area_m2":60,"transport_count_1000m":0,"transport_count_500m":0}}' \
  | python3 -m json.tool
```

Expected model metadata after the final restore:

```text
selected_candidate = hist_gradient_boosting
target_variable = price_per_m2
rows_total = 17287
r2 ≈ 0.9314
mae ≈ 4.81M RUB
```

## 8. Updating the release

Use this block in Termius after the local branch has been merged and pushed:

```bash
cd /opt/realtyscope
git fetch origin
git checkout main
git pull --ff-only origin main
docker compose -f docker-compose.prod.yml --env-file .env build
docker compose -f docker-compose.prod.yml --env-file .env up -d
docker compose -f docker-compose.prod.yml --env-file .env ps
```

If a release changes model artifacts or database state, repeat the bundle restore after pulling the code.

Full Termius redeploy sequence:

1. Open the VPS SSH session in Termius.
2. Run the `git fetch` / `git pull --ff-only` block above.
3. Upload the fresh local files `realtyscope-db-YYYYMMDD.dump` and `realtyscope-model-artifacts-YYYYMMDD.tar.gz` into `/opt/realtyscope`.
4. Run `bash scripts/deployment/restore_vps_runtime_bundle.sh`.
5. Run the parity smoke checks in section 7.
6. Check logs with `docker compose -f docker-compose.prod.yml --env-file .env logs --tail=120 api streamlit caddy`.

## 9. Backup before ingestion or risky updates

```bash
mkdir -p /opt/realtyscope/backups
docker compose -f docker-compose.prod.yml --env-file .env exec -T db \
  pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" \
  > /opt/realtyscope/backups/realtyscope-$(date +%F-%H%M).sql
```

## 10. Dockerized scheduled ingestion on VPS

The production Compose file includes an `ingestor` service under the `jobs` profile. It is not started by normal `up -d`; it is a one-shot job for systemd timers or manual runs.

Check ingestion status from Termius:

```bash
cd /opt/realtyscope
docker compose -f docker-compose.prod.yml --env-file .env --profile jobs run --rm \
  ingestor sh -lc 'python -m realtyscope.ingestion.domclick_scheduled_batch status \
  --database-url "$DATABASE_URL" --json'
```

Run one commit batch from the configured snapshot path:

```bash
cd /opt/realtyscope
docker compose -f docker-compose.prod.yml --env-file .env --profile jobs run --rm ingestor
```

The default path is `DOMCLICK_SOURCE_PATH=data/raw/domclick/current`. Keep this as a symlink or copied directory pointing at the latest bounded Domclick snapshot, for example:

```bash
mkdir -p /opt/realtyscope/data/raw/domclick
ln -sfn 2026-06-27-bulk /opt/realtyscope/data/raw/domclick/current
```

Example systemd service:

```ini
[Unit]
Description=RealtyScope Dockerized Domclick ingestion batch
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
WorkingDirectory=/opt/realtyscope
EnvironmentFile=/opt/realtyscope/.env
ExecStartPre=/usr/bin/docker compose -f docker-compose.prod.yml --env-file .env up -d db
ExecStart=/usr/bin/docker compose -f docker-compose.prod.yml --env-file .env --profile jobs run --rm ingestor
```

Example timer:

```ini
[Unit]
Description=Run RealtyScope Domclick ingestion daily

[Timer]
OnCalendar=*-*-* 00:20:00
Persistent=true

[Install]
WantedBy=timers.target
```

Install through Termius:

```bash
nano /etc/systemd/system/realtyscope-domclick-ingestor.service
nano /etc/systemd/system/realtyscope-domclick-ingestor.timer
systemctl daemon-reload
systemctl enable --now realtyscope-domclick-ingestor.timer
systemctl list-timers | grep realtyscope
```

Important parsing boundary: this Docker job ingests and commits an already available bounded snapshot. Live Domclick Chrome/CDP capture still depends on a Chrome-capable host, source accessibility, and QRATOR/CAPTCHA behavior. If the VPS itself must do live capture, install and validate Chrome/headless access first or add a managed browser sidecar; do not claim full live scraping parity until that smoke test passes on the VPS.

## 11. Known boundaries

- Docker Compose does not solve Domclick QRATOR/CAPTCHA access.
- The selected model is a validated snapshot; automatic retraining is not enabled.
- The model should be presented with temporal/spatial validation caveats.
- PostgreSQL, Redis, and MLflow must not be publicly exposed.
