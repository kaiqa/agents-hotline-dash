# Agent Hotline

A modern, production-ready dashboard and API for managing AI agent configurations. Built with FastAPI, SQLAlchemy Async, and vanilla JavaScript.

The Agent Hotline serves as the central host for agent data — storing configurations (token, endpoint, script, category, language, name, info, assets) and exposing them via a REST API and interactive dashboard. The dashboard supports full agent lifecycle management: create, edit, activate/deactivate, delete, duplicate, download, and export.

## Features

- 🧠 **Agent Management Dashboard** — Manage all agent configurations from a clean, responsive UI
- ⚡ **Status Toggle** — Activate/deactivate agents instantly
- 🔄 **Duplicate** — Clone agents with updated names
- ✏️ **Edit Details** — Modify token, endpoint, script, category, language, name, info, and image paths
- ⬇️ **Download** — Export individual agents as JSON or bulk as CSV
- 📊 **Analytics** — View agent statistics (active/inactive, categories, languages)
- 🔌 **WebSocket Updates** — Real-time updates when agents are created, updated, deleted, or duplicated
- 🌙 **Dark/Light Theme** — Automatic theme detection with manual toggle
- 🐳 **Docker Ready** — Production-ready Docker Compose deployment
- 📥 **Seed Data** — Includes 12 pre-configured agents from the original dataset
- 🌐 **CORS Enabled** — Allow all origins for client application consumption

## Architecture

```
Client / Browser
      │
      ▼
┌──────────────┐     ┌───────────────┐     ┌─────────────┐
│  Dashboard   │◄────│  REST API     │◄────│   MySQL     │
│ (Vanilla JS) │     │  /api/agents  │     │  agents     │
└──────┬───────┘     └───────┬───────┘     └─────────────┘
       │                     │
       ▼                     ▼
┌──────────────┐     ┌───────────────┐
│  WebSocket   │     │  WebSocket    │
│  /ws         │     │  Broadcast    │
└──────────────┘     └───────────────┘
```

## Agent Data Model

Each agent contains:

| Field | Type | Description |
|-------|------|-------------|
| `token` | string | Embedding/token identifier |
| `endpoint` | string | API endpoint URL |
| `environment` | string | `local`, `production`, etc. |
| `js_source` | string | JavaScript embed URL |
| `script` | string | Script identifier (e.g., `dograh-widget`) |
| `category` | string | Agent category (e.g., `fitness`, `language`, `career`, `tech`) |
| `language` | string | Language code (`en`, `es`, `de`) |
| `name` | string | Human-readable agent name |
| `finger_hole` | string (optional) | Image path (e.g., `assets/fear.png`) |
| `scrollable_agent_card` | string (optional) | Image path |
| `info` | text (optional) | Agent description |
| `is_active` | boolean | Active (`true`) or inactive (`false`) |
| `created_at` | datetime | Record creation timestamp |
| `updated_at` | datetime | Last update timestamp |

> Note: Image assets are stored as named paths (text), not uploaded files.

## Quick Start

### Using Docker Compose (Recommended)

```bash
# Clone and navigate
cd agents-hotline

# Start services
docker compose up -d

# View logs
docker compose logs -f app
```

The dashboard will be available at `http://localhost:5686` (API on port 5686, MySQL on 3309).

Before starting the app, set `LOGIN_USERNAME`, `LOGIN_PASSWORD`, and a strong random `SESSION_SECRET` in `.env`. Generate the session secret with `openssl rand -hex 32`. The dashboard, API, and WebSocket require a successful login. Set `SESSION_COOKIE_SECURE=true` when serving over HTTPS; leave it `false` for local HTTP development.

For a separate read-only integration identity, set `AGENTS_API_USERNAME` and `AGENTS_API_PASSWORD`. These credentials use HTTP Basic authentication and are accepted only for `GET /api/agents?is_active=true`; they cannot access the dashboard or any other API route.

### Initialize Default Agents

After the app starts, seed the included agent configurations:

```bash
# Copy files to container and run
docker cp seed_agents.json agents-hotline-app:/app/seed_agents.json
docker cp seed_agents_db.py agents-hotline-app:/app/seed_agents_db.py
docker compose exec app python seed_agents_db.py
```

Or use `curl` to create agents directly:

```bash
curl -X POST http://localhost:5686/api/agents \
  -H "Content-Type: application/json" \
  -d '{"token":"test","endpoint":"https://example.com","name":"test agent","category":"test","language":"en","js_source":"https://example.com/script.js","script":"widget","is_active":true}'
```

### Local Development

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env with your database configuration

# Initialize database (tables created automatically on startup)
uvicorn app.main:app --reload --host 0.0.0.0 --port 5687
```

## API Endpoints

### Agent Management

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/agents` | GET | List agents (paginated, filterable, searchable, sortable) |
| `/api/agents` | POST | Create new agent |
| `/api/agents/{id}` | GET | Get single agent by ID |
| `/api/agents/{id}` | PATCH | Update agent (partial update) |
| `/api/agents/{id}/status` | PATCH | Toggle active/inactive status |
| `/api/agents/{id}/duplicate` | POST | Duplicate agent with `(copy)` suffix |
| `/api/agents/{id}` | DELETE | Delete agent |

### Filter & Export

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/agents/filters` | GET | Get all unique categories & languages for filter dropdowns |
| `/api/agents/export/all` | GET | Export all agents as JSON array |
| `/api/agents/export/csv` | GET | Export all agents as CSV download |
| `/api/agents/stats/summary` | GET | Statistics: total/active/inactive + counts by category/language |

### System

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check with WebSocket connection count |
| `/ws` | WS | WebSocket for real-time dashboard updates |

## Query Parameters (List Agents)

```
GET /api/agents?page=1&page_size=20&search=&is_active=&category=&language=&sort=created_at:desc
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | int | 1 | Page number (≥1) |
| `page_size` | int | 20 | Items per page (1-100) |
| `search` | string | - | Search in name, category, language, info, **token** |
| `is_active` | bool | - | Filter by active status (`true`/`false`) |
| `category` | string | - | Filter by category (exact match) |
| `language` | string | - | Filter by language (exact match) |
| `sort` | string | `created_at:desc` | Sort field:direction (name, category, language, created_at, updated_at) |

### Example Requests

```bash
# All active agents
curl "http://localhost:5686/api/agents?is_active=true"

# Filter by category
curl "http://localhost:5686/api/agents?category=fitness"

# Search token
curl "http://localhost:5686/api/agents?search=emb_g2h"

# Filter + sort + pagination
curl "http://localhost:5686/api/agents?is_active=true&category=fitness&sort=name:asc&page=1&page_size=10"

# Get filter options for dropdowns
curl "http://localhost:5686/api/agents/filters"
# Returns: {"categories":["career","fitness","language","tech"],"languages":["de","en","es"]}
```

## WebSocket Events

Connect to `ws://localhost:5686/ws` for real-time updates.

### Server → Client Messages

| Type | Payload | Description |
|------|---------|-------------|
| `agent_created` | Agent object | New agent created |
| `agent_updated` | Agent object | Agent updated (fields or status) |
| `agent_deleted` | `{id}` | Agent deleted |
| `agent_duplicated` | Agent object | Agent duplicated |

### Client → Server

- Send any text to receive `pong` echo (heartbeat)

## Dashboard Features

### Dashboard Page
- **Statistics Cards** — Total Agents, Active, Inactive counts
- **Search & Filtering** — Filter by status, category, language; search name, category, info, **token**
- **Sorting** — Sort by name, category, language, environment, created date (click column headers)
- **Table** — Agent configurations with inline actions per row
  - 👁 View Details — Opens editable modal with all fields
  - ↻ Toggle Status — Switch active/inactive
  - ⬇ Download JSON — Individual agent export
  - 🗑 Delete — Permanent removal (with confirmation)
  - ⧉ Duplicate — Create a copy with `(copy)` suffix
- **Pagination** — Navigate through results
- **Bulk Export** — Download all agents as JSON or CSV

### Status Workflow
- Agents are created `is_active: true` by default
- Click the status badge to instantly toggle: Active ↔ Inactive
- Updates broadcast via WebSocket in real-time

### Settings Page
- Application info (version, environment, database)

## CORS Configuration

CORS is configured to allow all origins (`*`), all methods, and all headers — ready for consumption by any client application.

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Testing

```bash
pytest tests/ -v
```

### Test Coverage
- `tests/test_agents.py` — 7 tests covering CRUD + duplicate + status toggle
- `tests/conftest.py` — Async fixtures, sample agent factory

## Project Structure

```
agent-hotline/
├── app/
│   ├── main.py              # FastAPI entry point, CORS, routers, WebSocket
│   ├── config.py            # Settings (Pydantic Settings)
│   ├── database.py          # Async SQLAlchemy engine/session
│   ├── models/
│   │   ├── agent.py         # Agent SQLAlchemy model (composite indexes)
│   │   ├── setting.py       # Settings model
│   │   └── meeting.py       # Legacy model (retained)
│   ├── schemas/
│   │   └── agent.py         # Pydantic schemas (Create, Update, Response, Export)
│   ├── api/
│   │   ├── agents.py        # Agent REST endpoints (full CRUD + filters/export/stats)
│   │   ├── settings.py      # Settings endpoints
│   │   └── webhook.py       # Legacy webhook (health only)
│   ├── services/
│   │   └── websocket.py     # WebSocket connection manager & broadcast
│   └── static/
│       ├── index.html       # Dashboard HTML
│       ├── style.css        # Modern CSS with CSS custom properties
│       └── app.js           # Vanilla JS dashboard (state, rendering, WS)
├── seed_agents.json         # 12 default agent configurations
├── seed_agents_db.py        # Database seeding script
├── tests/
│   ├── test_agents.py       # Agent API tests
│   └── conftest.py          # Pytest fixtures
├── init-db.sql              # MySQL schema (agents + settings tables)
├── Dockerfile               # Multi-stage build
├── docker-compose.yml       # App + MySQL (ports 5686/3309)
├── requirements.txt
└── README.md                # This file
```

## Docker Compose Ports

| Service | Container Port | Host Port | Description |
|---------|---------------|-----------|-------------|
| app | 5687 | 5686 | FastAPI application |
| mysql | 3306 | 3309 | MySQL database |

Container names: `agents-hotline-app`, `agents-hotline-mysql`
Network: `agents-hotline-network`

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_ENV` | production | Environment name |
| `APP_HOST` | 0.0.0.0 | Bind address |
| `APP_PORT` | 5687 | Internal port |
| `DB_HOST` | mysql | Database host |
| `DB_PORT` | 3306 | Database port |
| `DB_USER` | agents_hotline_user | Database user |
| `DB_PASSWORD` | agents_hotline_password | Database password |
| `DB_NAME` | agents_hotline_db | Database name |
| `LOG_LEVEL` | INFO | Log level |

## License

MIT License — Feel free to use and modify for your needs.