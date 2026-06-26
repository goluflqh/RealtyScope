# Развертывание RealtyScope на VPS

Этот runbook описывает минимальный production-путь для учебного релиза RealtyScope: DigitalOcean Droplet, Docker Compose, Caddy, Cloudflare DNS и домен `realtyscope.bond`.

## Целевая схема

```text
Пользователь
  |
  v
Cloudflare DNS
  |
  v
DigitalOcean VPS :80/:443
  |
  v
Caddy reverse proxy
  |                 |
  v                 v
Streamlit UI        FastAPI
  |                 |
  +------ Docker network ------+
          |        |           |
          v        v           v
       PostgreSQL Redis      MLflow
```

Публичные endpoints:

- `https://realtyscope.bond` -> Streamlit dashboard.
- `https://api.realtyscope.bond` -> FastAPI `/health`, `/docs`, `/data`, `/predict`, `/monitoring/status`.

Непубличные сервисы:

- PostgreSQL, Redis и MLflow не публикуются наружу.
- MLflow остается доступен только внутри Docker network. Открывать его публично без auth нельзя.

## 1. Создать Droplet

Рекомендуемая конфигурация для демонстрационного деплоя:

- Ubuntu LTS.
- Basic Droplet.
- Минимум `2 vCPU / 2 GB RAM / 60 GB Disk`; если credit позволяет, `2 vCPU / 4 GB RAM` безопаснее для Docker build.
- Datacenter ближе к основной аудитории или доступный в аккаунте. Для учебного demo Singapore допустим, но для Москвы задержка будет выше.
- Добавить SSH key до создания Droplet.

После создания сохранить публичный IPv4. До появления IPv4 DNS в Cloudflare не настраивать.

## 2. Подключиться через Termius

В Termius создать host:

- Address: публичный IPv4 Droplet.
- Username: `root` или отдельный sudo-пользователь, если он создан.
- Authentication: SSH key.

Проверить подключение:

```bash
ssh root@<VPS_IP>
```

## 3. Подготовить сервер

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

## 4. Склонировать проект

```bash
mkdir -p /opt/realtyscope
cd /opt
git clone https://github.com/goluflqh/RealtyScope.git realtyscope
cd /opt/realtyscope
git checkout main
```

## 5. Создать production `.env`

```bash
cp .env.production.example .env
nano .env
```

Минимально заменить:

- `POSTGRES_PASSWORD` на длинный случайный пароль.
- `ACME_EMAIL` на реальный email для Let's Encrypt.
- `APP_DOMAIN=realtyscope.bond`.
- `API_DOMAIN=api.realtyscope.bond`.

Не коммитить `.env`.

## 6. Настроить Cloudflare

В Cloudflare добавить site `realtyscope.bond`, затем скопировать выданные Cloudflare nameservers.

В панели nicnames заменить текущие nameservers:

- `ns10.nicnames.com`
- `ns11.nicnames.com`
- `ns12.nicnames.com`

на пару nameservers, которую выдаст Cloudflare.

После появления публичного IPv4 Droplet создать DNS records:

| Type | Name | Content | Proxy |
| --- | --- | --- | --- |
| A | `@` | `<VPS_IP>` | Proxied или DNS only |
| A | `www` | `<VPS_IP>` | Proxied или DNS only |
| A | `api` | `<VPS_IP>` | Proxied или DNS only |

SSL/TLS mode: `Full` или `Full (strict)`. Для Caddy с публичным доменом предпочтительно `Full (strict)`, когда сертификат Let's Encrypt уже успешно выпущен на VPS.

## 7. Запустить production Compose

```bash
cd /opt/realtyscope
docker compose -f docker-compose.prod.yml --env-file .env build
docker compose -f docker-compose.prod.yml --env-file .env up -d
docker compose -f docker-compose.prod.yml --env-file .env ps
```

Проверить логи:

```bash
docker compose -f docker-compose.prod.yml --env-file .env logs --tail=120 caddy
docker compose -f docker-compose.prod.yml --env-file .env logs --tail=120 api
docker compose -f docker-compose.prod.yml --env-file .env logs --tail=120 streamlit
```

## 8. Восстановить runtime bundle

GitHub хранит код, Docker configuration и tracked reference assets, включая `data/external/moscow_district_boundaries.geojson`. Полное состояние demo также зависит от runtime artifacts, которые не должны коммититься:

- PostgreSQL database volume с реальными объявлениями и ingestion history.
- Model artifacts в `data/processed/models/phase5`.
- Redis/MLflow volumes создаются Compose; для учебного demo их можно оставить как persistent runtime state.

На локальной машине с уже проверенным Docker stack экспортировать bundle:

```bash
cd /mnt/e/Магистр/2-курс/python/RealtyScope-stitch-hybrid-redesign-20260623
bash scripts/deployment/export_local_runtime_bundle.sh ../realtyscope-vps-transfer
```

Скопировать два созданных файла на VPS в `/opt/realtyscope`. В Termius это можно сделать через SFTP panel или drag-and-drop в директорию проекта:

```text
realtyscope-db-YYYYMMDD.dump
realtyscope-model-artifacts-YYYYMMDD.tar.gz
```

На VPS восстановить bundle и выполнить smoke checks:

```bash
cd /opt/realtyscope
bash scripts/deployment/restore_vps_runtime_bundle.sh
```

Скрипт останавливает API/UI на время восстановления, пересоздает database внутри PostgreSQL container, распаковывает model artifacts в Docker volume `realtyscope_model_artifacts`, затем снова запускает `api`, `streamlit` и `caddy`.

После восстановления дополнительно проверить mount parity:

```bash
docker compose -f docker-compose.prod.yml --env-file .env exec -T streamlit test -f /app/data/external/moscow_district_boundaries.geojson
docker compose -f docker-compose.prod.yml --env-file .env exec -T streamlit test -f /app/data/processed/models/phase5/selected_price_model_v1_non_leaky.joblib
docker compose -f docker-compose.prod.yml --env-file .env exec -T streamlit ls -lh /app/data/external
docker compose -f docker-compose.prod.yml --env-file .env exec -T streamlit ls -lh /app/data/processed/models/phase5
```

Это важно: Streamlit UI читает district boundaries и local model metadata напрямую из filesystem. Если эти mount points отсутствуют, dashboard может показывать частичную готовность district/model blocks даже при рабочем API.

## 9. Smoke test

С сервера:

```bash
curl -fsS http://localhost/ >/dev/null
curl -fsS http://api.realtyscope.bond/health
curl -fsS http://api.realtyscope.bond/monitoring/status | python3 -m json.tool | head -80
```

С локального компьютера:

```bash
curl -fsS https://realtyscope.bond/
curl -fsS https://api.realtyscope.bond/health
curl -fsS https://realtyscope.bond/robots.txt
curl -fsS https://api.realtyscope.bond/robots.txt
```

Открыть в браузере:

- `https://realtyscope.bond`
- `https://realtyscope.bond/robots.txt`
- `https://api.realtyscope.bond/docs`

## 10. Обновление релиза

```bash
cd /opt/realtyscope
git fetch origin
git checkout main
git pull --ff-only origin main
docker compose -f docker-compose.prod.yml --env-file .env build
docker compose -f docker-compose.prod.yml --env-file .env up -d
docker compose -f docker-compose.prod.yml --env-file .env ps
```

Если обновление меняет runtime mounts или restore scripts, после `git pull` перезапустить Streamlit/Caddy и повторить mount parity checks:

```bash
docker compose -f docker-compose.prod.yml --env-file .env up -d streamlit caddy
docker compose -f docker-compose.prod.yml --env-file .env exec -T streamlit test -f /app/data/external/moscow_district_boundaries.geojson
docker compose -f docker-compose.prod.yml --env-file .env exec -T streamlit test -f /app/data/processed/models/phase5/selected_price_model_v1_non_leaky.joblib
```

## 11. Backup перед ingestion

Перед включением регулярного ingestion настроить резервную копию PostgreSQL:

```bash
mkdir -p /opt/realtyscope/backups
docker compose -f docker-compose.prod.yml --env-file .env exec -T db pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" > /opt/realtyscope/backups/realtyscope-$(date +%F-%H%M).sql
```

Для учебного demo сначала достаточно ручного backup перед обновлениями. Автоматический cron/systemd timer лучше добавить после первого успешного VPS smoke test.

## Ограничения

- Production Compose не решает QRATOR/CAPTCHA для Domclick; это отдельная operational dependency источника.
- Модель не переобучается автоматически после каждого ingestion. Переобучение должно идти через candidate comparison и promotion gate.
- Terminal sale/removal lifecycle rows отсутствуют; exposure forecast является inferred по observation gaps.
- Не открывать PostgreSQL, Redis и MLflow в публичный интернет.
