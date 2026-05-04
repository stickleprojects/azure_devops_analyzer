# Copilot Agent Prompt — Plan 025 Phase 1a: React Admin UI MVP

> **Usage**: Paste the contents of the **Prompt** section below into GitHub
> Copilot agent (or Copilot Workspace). Everything above the horizontal rule
> is meta-context for you; everything below it is the agent instruction.

**Branch to create**: `feature/025-phase1a-admin-ui`
**PR target**: `main`
**PR title**: `Plan 025 Phase 1a: React admin UI MVP`

---

## Prompt

You are implementing Phase 1a of Plan 025 for the `azure_devops_analyzer`
repository: a small React admin UI that lives alongside an existing Python /
Grafana stack. This is **greenfield work in a new directory** — do NOT touch
anything under `src/`, `tests/`, or `dashboards/`.

---

### What to build

A React + Vite + TypeScript single-page app in `web/admin-ui/` with three
pages reachable from a persistent nav bar:

#### 1. Home (`/`)

Tiles linking to every Grafana dashboard. Grafana runs on
`http://localhost:3000`. All tiles open in a **new tab**.

| Tile title | Grafana URL |
|---|---|
| Home | `/d/dashboard-home` |
| Repositories | `/d/repo-overview` |
| Security | `/d/security-dashboard` |
| Technology | `/d/technology-landscape` |
| Admin | `/d/admin-dashboard` |
| Library Deep Dive | `/d/library-detail-deep-dive` |
| Repository Deep Dive | `/d/repo-deep-dive` |
| Dependency Vulnerabilities | `/d/dep-vuln-portfolio` |
| Pull Requests | `/d/pull-requests` |
| Teams | `/d/team-overview` |
| Services | `/d/service-overview` |
| Contributors | `/d/contributor-analytics` |
| Extraction Health | `/d/extraction-health` |

#### 2. Extraction Control (`/extraction`)

Two buttons:

- **Trigger GitHub Rescan** → `POST /api/rescan/github`
- **Trigger Azure DevOps Rescan** → `POST /api/rescan/azure-devops`

Both use TanStack Query mutations. On **success**: show an in-page toast with
the returned `task_id`. On **error**: show a toast with the error message. The
button must **not** open a new browser tab — all feedback is in-page. Buttons
show a loading/disabled state while the request is in flight.

#### 3. System Health (`/health`)

Fetches `GET /health` (auto-refreshes every 30 s) and renders the response as
a key/value table. Includes two outbound links (both open in a new tab):

- **Open Flower** → `http://localhost:5555`
- **Grafana Admin Dashboard** → `http://localhost:3000/d/admin-dashboard`

---

### Tech stack (locked — do not substitute)

| Concern | Choice |
|---|---|
| Framework | React 18 + Vite 5 + TypeScript (strict) |
| Styling | Tailwind CSS v3 — utility classes only, no component library |
| Data fetching | TanStack Query v5 (`@tanstack/react-query`) |
| Routing | React Router v6 |
| Testing | Vitest + `@testing-library/react` |

---

### File manifest — create every file listed

```
web/admin-ui/
  index.html
  package.json
  tsconfig.json
  tsconfig.node.json
  vite.config.ts
  tailwind.config.ts
  postcss.config.js
  Dockerfile
  nginx.conf
  src/
    main.tsx
    App.tsx
    pages/
      HomePage.tsx
      HomePage.test.tsx
      ExtractionPage.tsx
      ExtractionPage.test.tsx
      HealthPage.tsx
      HealthPage.test.tsx
    components/
      Layout.tsx        ← persistent nav with links to the three pages
      Toast.tsx         ← dismissible success/error toast
      ApiButton.tsx     ← button with loading state for mutations
    api/
      client.ts         ← typed fetch wrappers (see below)
      types.ts          ← TypeScript interfaces for API responses
      client.test.ts
```

Also modify (do not recreate):

```
docker-compose.yml        ← add admin-ui service (append only)
.github/workflows/        ← add frontend.yml (new file)
```

---

### API client (`src/api/client.ts`)

Export exactly these three typed functions:

```typescript
// POST /api/rescan/github → { task_id: string }
export async function triggerGithubRescan(): Promise<{ task_id: string }>

// POST /api/rescan/azure-devops → { task_id: string }
export async function triggerAzureDevOpsRescan(): Promise<{ task_id: string }>

// GET /health → arbitrary object
export async function getHealth(): Promise<Record<string, unknown>>
```

Throw an `Error` with the response body text when HTTP status is not 2xx.

---

### Vite proxy config (`vite.config.ts`)

```typescript
server: {
  proxy: {
    '/api': 'http://localhost:5000',
    '/health': 'http://localhost:5000',
  }
}
```

This means CORS is never needed in dev.

---

### Dockerfile (multi-stage)

```dockerfile
# Stage 1 — build
FROM node:20-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

# Stage 2 — serve
FROM nginx:1.25-alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 8080
```

---

### nginx.conf

- Listen on port **8080**
- Serve `/usr/share/nginx/html` for all routes
- `try_files $uri $uri/ /index.html;` so React Router works on hard reload
- Proxy `/api/` → `http://extraction-api:5000` (the Flask service name in docker-compose)
- Proxy `/health` → `http://extraction-api:5000`

---

### docker-compose.yml — append this service

The existing `docker-compose.yml` already has services including `extraction-api`
(Flask API on port 5000) and `grafana` (on port 3000). **Append** the following
service; do not modify any existing service:

```yaml
  # ===========================================
  # Admin UI - React frontend for admin & operational workflows
  # ===========================================
  admin-ui:
    build:
      context: web/admin-ui
      dockerfile: Dockerfile
    container_name: analyzer-admin-ui
    restart: unless-stopped
    ports:
      - "8080:8080"
    depends_on:
      extraction-api:
        condition: service_started
    networks:
      - analyzer-network
```

---

### CI workflow (`.github/workflows/frontend.yml`)

```yaml
name: Frontend CI

on:
  push:
    paths:
      - 'web/admin-ui/**'
  pull_request:
    paths:
      - 'web/admin-ui/**'

jobs:
  frontend:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: web/admin-ui
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
          cache-dependency-path: web/admin-ui/package-lock.json
      - run: npm ci
      - run: npm run typecheck
      - run: npm run test -- --run
      - run: npm run build
```

Add these scripts to `package.json`:

```json
"scripts": {
  "dev": "vite",
  "build": "vite build",
  "typecheck": "tsc --noEmit",
  "test": "vitest",
  "preview": "vite preview"
}
```

---

### Tests

**`api/client.test.ts`** — for each function: mock `fetch`, assert the right
URL and HTTP method were used, assert the parsed response is returned. Also
assert that a non-2xx response throws an `Error` containing the body text.

**`pages/ExtractionPage.test.tsx`** — mock `api/client.ts`. Render the page
inside `QueryClientProvider`. Assert both buttons are visible. Click "Trigger
GitHub Rescan", assert `triggerGithubRescan` was called, then assert the
success toast contains a `task_id`. Simulate an API error and assert the error
toast appears.

**`pages/HealthPage.test.tsx`** — mock `getHealth` to return a sample object.
Assert the key/value pairs are rendered. Assert the "Open Flower" link has the
correct `href`.

**`pages/HomePage.test.tsx`** — assert all 13 dashboard tiles are rendered and
each links to the correct Grafana URL.

---

### Architecture constraint

`web/admin-ui` code must **never** import from `src/`, `tests/`, or
`dashboards/`. It only communicates with the Flask API over HTTP. If you find
yourself reaching outside `web/admin-ui/`, stop — that is wrong.

---

### Out of scope for this PR

- Phase 1b: Repository List page, Compute Service Metrics trigger
- Phase 1c: Tech Radar viewer (depends on Plan 022 Track C)
- Phase 1d: Library detail page (depends on Plan 021)
- Authentication of any kind
- Dark mode, i18n, mobile-first layout

---

### Acceptance checklist (reviewer will verify)

- [ ] `docker compose up admin-ui` serves the UI at `http://localhost:8080`
- [ ] Home page renders all 13 dashboard tiles; each opens Grafana in a new tab
- [ ] "Trigger GitHub Rescan" calls `POST /api/rescan/github`, shows in-page toast with `task_id`
- [ ] "Trigger Azure DevOps Rescan" calls `POST /api/rescan/azure-devops`, same behaviour
- [ ] System Health page shows `/health` output; "Open Flower" link works
- [ ] `npm run typecheck` exits 0
- [ ] `npm run test -- --run` exits 0
- [ ] `npm run build` exits 0
- [ ] CI workflow runs on PRs touching `web/admin-ui/**`
- [ ] No files changed under `src/`, `tests/`, or `dashboards/`
