# Admin UI — TechOps FAQ

This guide covers the most common issues the operations team encounters when
running and maintaining the **Azure DevOps Analyzer Admin UI**.  It is written
for people who may not be familiar with the underlying technology — no coding
knowledge is required to follow any procedure here.

---

## Table of contents

1. [Where is the Admin UI?](#where-is-the-admin-ui)
2. [The page won't load / "This site can't be reached"](#the-page-wont-load)
3. [Dashboard tiles do nothing / Grafana opens to a blank page](#dashboard-tiles-do-nothing)
4. [Rescan button spins forever or shows an error](#rescan-button-errors)
5. [System Health page shows an error or is empty](#health-page-errors)
6. [How to restart a specific component](#restarting-components)
7. [How to trigger a database migration manually](#running-migrations)
8. [How to check which background tasks are running (Flower)](#checking-tasks-in-flower)
9. [Log locations — where to look when something goes wrong](#log-locations)
10. [Who to escalate to if self-service steps don't work](#escalation)

---

## Where is the Admin UI? {#where-is-the-admin-ui}

Once the stack is running, the Admin UI is at:

```
http://<your-server>:8080
```

If you are running locally (developer machine):

```
http://localhost:8080
```

The Admin UI has four sections reachable from the top navigation bar:

| Section | URL | Purpose |
|---|---|---|
| **Home** | `/` | Links to every Grafana analytics dashboard |
| **Extraction Control** | `/extraction` | Trigger re-scans of GitHub and Azure DevOps, compute service metrics |
| **Repositories** | `/repositories` | Browse, filter, rescan, or remove individual repositories |
| **System Health** | `/health` | Live status of the extraction API and its dependencies |

---

## The page won't load {#the-page-wont-load}

**Symptom**: Browser shows "This site can't be reached", "Connection refused", or a blank page on port 8080.

**Cause**: The `admin-ui` Docker container is not running.

**Steps**:

1. Open a terminal on the server.
2. Check if the container is running:
   ```
   docker ps | grep admin-ui
   ```
3. If it is **not listed**, start it:
   ```
   docker compose up -d admin-ui
   ```
4. If it is listed but shows **"Restarting"**, there is a crash-loop. Get the last 50 log lines:
   ```
   docker logs analyzer-admin-ui --tail 50
   ```
5. If you see `nginx: [emerg]` errors, the nginx configuration is invalid — escalate to the dev team.

---

## Dashboard tiles do nothing / Grafana opens to a blank page {#dashboard-tiles-do-nothing}

**Symptom**: Clicking a tile on the Home page opens a new tab but Grafana shows "Dashboard not found" or takes you to the Grafana login screen.

**Possible causes and fixes**:

| Cause | Fix |
|---|---|
| Grafana container is not running | `docker compose up -d grafana` |
| Grafana is running on a different port | Check `GRAFANA_BASE` in `web/admin-ui/src/config.ts` — default is `http://localhost:3000` |
| Dashboard was deleted or renamed in Grafana | Re-provision dashboards: `docker compose restart grafana` |
| Browser blocked a pop-up | Allow pop-ups for the Admin UI in your browser settings |

---

## Rescan button errors {#rescan-button-errors}

### "HTTP 5xx" error toast

**Symptom**: Clicking "Trigger GitHub Rescan" or "Trigger Azure DevOps Rescan" shows a red toast with a message like `HTTP 500: ...` or `HTTP 503: Service Unavailable`.

**Steps**:

1. The error message in the toast contains the HTTP status code and a description — read it carefully.
2. Check the extraction API logs:
   ```
   docker logs analyzer-extraction-api --tail 100
   ```
3. Common causes:

| Error | Likely cause | Fix |
|---|---|---|
| `HTTP 500: Worker queue full` | RabbitMQ queue is at capacity | Restart RabbitMQ and the Celery worker (see [Restarting components](#restarting-components)) |
| `HTTP 503: Service Unavailable` | Extraction API is starting up | Wait 30 seconds and retry |
| `HTTP 500: Database connection failed` | TimescaleDB is down | `docker compose up -d timescaledb` |
| `HTTP 401` or `HTTP 403` | API token expired | Rotate the `AZURE_DEVOPS_PAT` or `REPO_ANALYZER_GITHUB_TOKEN` in your `.env` file, then restart the API |

### Button stays greyed-out after clicking

**Symptom**: The button shows a spinner and never re-enables; no toast appears.

**Steps**:

1. Open your browser's developer tools (F12 → Network tab) and look for a failed request to `/api/rescan/github` or `/api/rescan/azure-devops`.
2. Check the extraction API logs for any Python traceback.
3. Restart the extraction API: `docker compose restart extraction-api`.

---

## System Health page shows an error or is empty {#health-page-errors}

**Symptom**: The health page shows "Failed to load health data: HTTP 5xx: ..." or a loading spinner that never resolves.

**Cause**: The extraction API (`/health` endpoint) is not responding.

**Steps**:

1. Check if the extraction API container is running:
   ```
   docker ps | grep extraction-api
   ```
2. If not running:
   ```
   docker compose up -d extraction-api
   ```
3. Test the health endpoint directly:
   ```
   curl http://localhost:5000/health
   ```
   Expected output: `{"status": "ok", ...}`.  
   If you get `Connection refused`, the container is down.  
   If you get a JSON error object, read the `detail` field for the specific failure.

4. Check logs:
   ```
   docker logs analyzer-extraction-api --tail 100
   ```

---

## How to restart a specific component {#restarting-components}

Run these commands from the directory that contains `docker-compose.yml`:

| Component | Restart command |
|---|---|
| Admin UI (nginx) | `docker compose restart admin-ui` |
| Extraction API (Flask) | `docker compose restart extraction-api` |
| Celery worker | `docker compose restart celery-worker` |
| RabbitMQ message broker | `docker compose restart rabbitmq` |
| TimescaleDB database | `docker compose restart timescaledb` |
| Grafana dashboards | `docker compose restart grafana` |

To restart everything at once:
```
docker compose down && docker compose up -d
```

> ⚠️ Restarting TimescaleDB disconnects active database connections — plan for
> a 30–60 second outage when doing this.

---

## How to trigger a database migration manually {#running-migrations}

Migrations are run automatically when the stack starts.  If you need to run
them manually (e.g. after a hot-patching session):

```
docker compose exec timescaledb bash /docker-entrypoint-initdb.d/run_migrations.sh
```

Or using the dedicated migration runner script:

```
docker compose run --rm extraction-api python -m alembic upgrade head
```

Check which migrations have been applied:

```
docker compose exec timescaledb psql -U <POSTGRES_USER> -d <POSTGRES_DB> \
  -c "SELECT version, applied_at FROM schema_migrations ORDER BY applied_at;"
```

If `schema_migrations` does not exist yet, no migrations have been applied — run the manual step above.

---

## How to check which background tasks are running (Flower) {#checking-tasks-in-flower}

**Flower** is the Celery task monitor. It shows which extraction tasks are
queued, running, or have failed.

Access it at:
```
http://<your-server>:5555
```

The **System Health** page in the Admin UI also has an "Open Flower ↗" link.

Useful views inside Flower:

| View | Purpose |
|---|---|
| **Tasks** tab | See all tasks and their current state |
| **Workers** tab | Confirm at least one `celery-worker` is online |
| **Brokers** tab | Check RabbitMQ connection status |

If a task shows **FAILURE**:
1. Click on the task ID to see the full Python traceback.
2. Check `docker logs analyzer-celery-worker --tail 100` for context.
3. If it's a transient network error, the task will be retried automatically.
4. If the error is `OperationalError: could not connect to database`, restart TimescaleDB.

---

## Log locations {#log-locations}

| Component | How to view logs |
|---|---|
| Admin UI | `docker logs analyzer-admin-ui --tail 100 -f` |
| Extraction API | `docker logs analyzer-extraction-api --tail 100 -f` |
| Celery worker | `docker logs analyzer-celery-worker --tail 100 -f` |
| RabbitMQ | `docker logs analyzer-rabbitmq --tail 100 -f` |
| TimescaleDB | `docker logs analyzer-timescaledb --tail 100 -f` |
| Grafana | `docker logs analyzer-grafana --tail 100 -f` |

The `-f` flag keeps the log stream open (like `tail -f`). Press `Ctrl+C` to stop.

Log levels: `ERROR` and `CRITICAL` messages always indicate something needs
attention.  `WARNING` messages are informational.  `INFO` messages are normal
operational chatter.

---

## Escalation {#escalation}

If the self-service steps above do not resolve the issue, gather the following
before raising a ticket:

1. **Error message** — exact text from the toast, browser console, or terminal.
2. **Last 200 log lines** from the relevant container(s):
   ```
   docker logs analyzer-extraction-api --tail 200 > extraction-api.log
   ```
3. **Docker status**:
   ```
   docker ps -a > docker-status.txt
   ```
4. **Time of the failure** (UTC preferred).

Attach these files to the ticket so the dev team can diagnose without needing
direct server access.
