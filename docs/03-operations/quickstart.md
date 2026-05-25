# Quickstart

## Starting the stack

Use the helper script to bootstrap the Docker stack, create `.env`, initialize the schema, and start extraction:

```bash
./Start-RepoAnalysis.sh --regenerate-env
```

What happens:

1. Prompts for GitHub/Azure DevOps credentials and writes `.env`
2. Starts Docker services (TimescaleDB, RabbitMQ, workers, scheduler)
3. Initializes the database schema
4. Submits an extraction task to Celery (background mode)

### Starting manually (without the helper)

1. Copy and edit `.env` from `.env.example`
2. Resolve environment variable references: `bash ./scripts/resolve_env.sh > .env.resolved`
3. Start services: `docker compose --env-file .env.resolved up -d`
4. Submit a run: `docker compose --env-file .env.resolved run --rm scheduler python /app/scripts/submit_extraction_task.py`

### How to know it is running

- Scheduler logs show `Enqueuing task=...`
- Worker logs show tasks executing
- Flower UI at `http://localhost:5555`
- Grafana dashboards at `http://localhost:3000` (admin/admin)
- Admin UI at `http://localhost:8080` (rescan triggers, system health)

See [Start-RepoAnalysis.sh](../../Start-RepoAnalysis.sh) for all parameters and examples.

## First-launch checklist (new user)

After the stack starts and the first extraction completes:

1. **Grafana Home** — `http://localhost:3000/d/dashboard-home` — confirm summary stats are non-zero (Repositories, Contributors, Commits).
2. **Repository Overview** — verify your repos appear with correct metadata.
3. **Security dashboard** — confirm dependency vulnerabilities are populated. If empty, the enrichment worker may still be running; check Flower.
4. **Extraction Health** — `http://localhost:3000/d/extraction-health` — any invariant violations appear here within minutes of extraction finishing.
5. **Admin UI** — `http://localhost:8080` — trigger a rescan, confirm a toast appears with a `task_id` and the task shows in Flower.

If Grafana dashboards show "No data": check `docker compose logs worker` for errors. The most common cause is a missing or expired PAT — re-run `./Start-RepoAnalysis.sh --regenerate-env` to refresh credentials.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| All Grafana panels blank | Credentials missing/expired | Re-run `Start-RepoAnalysis.sh --regenerate-env`; check PAT scopes |
| Extraction stuck in Flower | Worker container crashed | `docker compose restart worker` |
| `psql` connection refused | TimescaleDB not ready | `docker compose up -d timescaledb && sleep 10` |
| Admin UI 502 / not reachable | nginx can't reach Flask API | `docker compose up -d api`; check port 5000 |
| Security dashboard empty | Enrichment worker still running | Wait 5–10 min; watch `docker compose logs enrichment-worker` |
| Grafana data source error | Wrong DB credentials in provisioning | Check `provisioning/datasources/` matches `.env.resolved` |
| `classify_extraction_error` function missing | Migration 020 not applied | `bash scripts/run-tests-docker.sh tests/contract/database/test_migration_tracking.py` |
