# Dashboard Screenshots

_Last reviewed: 2026-04-30_

This directory holds PNG screenshots of each Grafana dashboard, embedded in `docs/03-operations/visualization.md`.

## How to Capture Screenshots

1. Start the full stack:

   ```bash
   docker compose up -d
   ```

2. Wait for Grafana to finish provisioning (usually 10–20 seconds), then open `http://localhost:3000`.

3. For each dashboard, navigate to it, set a representative time range (e.g. last 30 days), and use your browser's screenshot tool or Grafana's built-in renderer to save a PNG.

4. Save the file here using the naming convention below and commit it.

## File Naming

| Dashboard              | Filename                        |
| ---------------------- | ------------------------------- |
| Dashboard Home         | `dashboard-home.png`            |
| Team Overview          | `team-overview.png`             |
| Repository Overview    | `repository-overview.png`       |
| Repository Deep-Dive   | `repository-deep-dive.png`      |
| Service Overview       | `service-overview.png`          |
| Pull Request Analysis  | `pull-requests.png`             |
| Contributor Analytics  | `contributor-analytics.png`     |
| Security Dashboard     | `security-dashboard.png`        |
| Administration         | `admin-dashboard.png`           |

## Grafana Image Renderer (optional)

If the Grafana image renderer plugin is installed, you can export screenshots via the API:

```bash
curl -o docs/images/screenshots/team-overview.png \
  "http://admin:admin@localhost:3000/render/d/team-overview?width=1400&height=900&from=now-30d&to=now"
```

Repeat for each dashboard UID listed in `docs/03-operations/visualization.md`.
