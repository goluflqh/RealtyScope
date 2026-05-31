# Domclick Daily Snapshot Collection

Date: 2026-05-31
Audience: technical agents and operators running RealtyScope Phase 3.5.

## Purpose

Domclick access can depend on geography and anti-bot controls. RealtyScope therefore separates the daily collection host from the offline parser and database ingestion path.

The collection host is any machine that can legitimately access Domclick from the required network, for example a local Windows machine with a Russian IP route or a Russian VPS. The RealtyScope repository then ingests saved snapshots offline. Codex does not need live Domclick access to validate parser, persistence, EDA, API, or dashboard code.

## Non-Negotiable Rules

- Do not scrape `/search` while `robots.txt` disallows it.
- Do not bypass QRATOR, CAPTCHA, login walls, or other anti-bot challenges.
- Keep limits, timeouts, and delays explicit.
- Commit code and docs only. Do not commit raw snapshots, database dumps, `.env` files, or generated artifacts.
- Store enough manifest metadata to audit what was collected and to replay ingestion later.

## Snapshot Layout

Use a gitignored landing zone:

```text
data/raw/domclick/YYYY-MM-DD/
  manifest.json
  pages/
    listing-001.html
    listing-002.html
  payloads/
    listings-001.json
```

`manifest.json` should contain at least:

```json
{
  "source_name": "domclick",
  "collection_date": "2026-05-31",
  "collector_version": "manual-or-script-name",
  "network_note": "RU IP route used by operator",
  "entries": [
    {
      "source_url": "https://domclick.ru/...",
      "source_type": "domclick_html",
      "path": "pages/listing-001.html",
      "fetched_at": "2026-05-31T12:00:00Z",
      "http_status": 200,
      "content_sha256": "..."
    }
  ]
}
```

The current offline ingestor ignores `manifest.json` as data input and scans supported files recursively.

## Daily Operator Flow

1. Prepare a URL file with one allowed Domclick URL per line. Use listing/detail/card or other allowed public URLs. Do not include `/search` URLs.
2. Run the collector on the RU-accessible host:

```powershell
python -m realtyscope.ingestion.domclick_snapshot_collector `
  --url-file data/raw/domclick-urls.txt `
  --output-root data/raw/domclick `
  --collection-date 2026-05-31 `
  --delay-seconds 2 `
  --json
```

The collector checks `robots.txt`, rejects disallowed URLs before fetching, refuses QRATOR challenge pages, writes HTML snapshots under `pages/`, writes JSON snapshots under `payloads/`, and writes `manifest.json`.

3. If the collector cannot access Domclick from the current machine, run the same command on the RU-IP host and copy the resulting day directory back to the RealtyScope machine.
4. Inspect the snapshot before writing to PostgreSQL:

```powershell
python -m realtyscope.database.real_data_ingestion `
  --source-type domclick_snapshot_dir `
  --source-path data/raw/domclick/2026-05-31 `
  --inspect-only `
  --json
```

The inspect step parses the same files as persistence and reports `records_seen`, normalized rows, rejected rows, and ML-ready rows. It does not require a database connection and writes nothing.

5. Run Alembic against the target database.
6. Ingest the daily directory:

```powershell
python -m realtyscope.database.real_data_ingestion `
  --source-type domclick_snapshot_dir `
  --source-path data/raw/domclick/2026-05-31 `
  --database-url $env:DATABASE_URL `
  --json
```

7. Build the EDA summary from the same persisted database:

```powershell
python -m realtyscope.analysis.eda_summary `
  --database-url $env:DATABASE_URL `
  --output docs/data/phase3_5_eda_summary.vi.md `
  --json
```

8. Record the ingestion JSON output, database row counts, and EDA summary path in the Phase 3.5 checkpoint.

## Scheduling Options

- Windows Task Scheduler on the RU-IP machine.
- `cron` or `systemd timer` on a Linux VPS.
- A Docker container on the RU-IP host, provided secrets and raw data stay outside git.

The scheduled job should fail loudly when it collects zero records, gets blocked, or writes no parseable snapshots.

## Quality Checks

Each daily run should report:

- files collected;
- records seen;
- raw rows inserted or reused;
- listings created or updated;
- rejected rows and top rejection reasons;
- coordinate coverage;
- ML-ready count;
- last successful run timestamp.

Phase 3.5 is not complete until real Domclick rows are persisted, counts are recorded, EDA conclusions are computed from those rows, and at least one DB-backed API read path exists.
