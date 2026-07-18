# EktaAI — GenAI Stadium Operations Twin (FIFA World Cup 2026)

EktaAI is a GenAI-powered stadium operations assistant designed for the FIFA World Cup 2026. Built with a FastAPI backend and a Vite/React frontend, the system is designed to solve real-world challenges across navigation, crowd dynamics, accessibility, multilingual fan engagement, and staff decision support. A single app ships two dedicated, sidebar-driven portals behind a shared landing page: a **Fan Portal** (live map, match schedule & bracket, player/team stats, ticket, profile, and a multilingual voice/chat assistant) and a **Staff Portal** (live crowd & alerts, the Operations Copilot, and an operations chat) — both fed by the same real-time digital twin.

---

## Chosen Vertical

**Primary: Operational Intelligence & Real-Time Decision Support.**
EktaAI treats the stadium as a live *digital twin* and puts a GenAI layer on top of it that not only answers questions but **proactively forecasts congestion and recommends actions** to venue staff before bottlenecks form (the Operations Copilot).

This primary vertical is reinforced by supporting ones, all delivered through the same twin + GenAI core:

- **Navigation** — accessible, step-free shortest-path routing between gates, concourses, and seating (Dijkstra over a live graph), rendered live on the Fan Portal's interactive map.
- **Crowd Management** — real-time zone density telemetry pushed over Server-Sent Events, gate congestion, and auto-generated plain-language alerts.
- **Accessibility** — step-free route filtering plus a fully accessible UI (semantic HTML, high-contrast mode, large-text, keyboard nav, voice in/out).
- **Transportation** — live transit lines (metro, shuttle, BRT) are part of the digital twin: the Fan Portal's "Getting Here" view shows next departures and crowding, with a GenAI departure advisory steering fans to the least-loaded line.
- **Sustainability** — the same advisory carries per-mode CO2-savings nudges, and the Copilot's transit-aware egress plan drains the stadium through public transit in staggered waves instead of surging private-car pickups.
- **Multilingual Assistance** — first-class English, Spanish, and French for fans (chat + voice), with the LLM matching any language it is addressed in.
- **Fan Engagement** — match schedule and knockout bracket, player and team stats with radar-chart comparisons, and a digital ticket view, so the twin is also a fan's day-of companion, not just an ops tool.

### Problem-Statement Coverage

| Vertical in the brief | Feature that delivers it |
|---|---|
| Navigation | Dijkstra routing over the live `nodes`/`edges` graph; routes rendered on the fan map via chat |
| Crowd management | Simulated IoT telemetry, SSE live feeds, GenAI plain-language alerts |
| Accessibility | `accessible_only` step-free routing; high-contrast/large-text/keyboard/voice UI |
| Transportation | `transit_lines` in the twin; "Getting Here" fan view; `GET /api/v1/transit` with GenAI departure advisory |
| Sustainability | Per-mode CO2-savings nudges; transit-aware staggered egress in the Copilot |
| Multilingual assistance | EN/ES/FR UI + chat + voice; LLM matches any language it is addressed in |
| Operational intelligence | Staff portal: live crowd, alerts, data history, deterministic tool briefs |
| Real-time decision support | Operations Copilot: 5-minute congestion forecasts, prioritized actions, egress staggering plan |

## Approach & Logic

The design follows one principle: **the LLM orchestrates, the digital twin is the source of truth.**

1. **A SQLite digital twin is the single source of truth.** Zones, gates, and a `nodes`/`edges` routing graph model the venue. A background simulator evolves crowd levels with a *momentum model* (slowly-varying ingress/egress pressure) so trends are sustained and genuinely forecastable — closer to real IoT telemetry than random noise.
2. **The LLM never invents facts — it decides which tool to call.** User queries go through a Groq-hosted model using OpenAI-style function calling. It picks `get_route`, `get_crowd_density`, or `get_gate_status`; the tools query the twin, and the real data is returned. This keeps answers grounded and auditable.
3. **RAG handles the static knowledge.** Non-live questions (facilities, transit, rules, sustainability) are answered from a `sentence-transformers` + `FAISS` semantic index over a curated stadium-facts file, injected as context.
4. **The Operations Copilot makes it proactive, not just reactive.** It fits a short-horizon trend to each zone's recent telemetry, projects density ~5 minutes ahead (with ETA-to-critical and the feeding gate), and asks the LLM to synthesize an executive summary + prioritized actions — moving from "answer on demand" to "predict and prescribe."
5. **Reliability is designed in.** Every GenAI path has a deterministic fallback (mock mode, offline RAG, rule-based alerts/Copilot), a retry + circuit breaker guards the Groq calls, and staff tool-queries render deterministically to cut latency. The app stays fully functional even with no API key or no network.
6. **One twin, two live portals.** A shared landing page (with a lightweight demo login) routes fans and staff into purpose-built, sidebar-navigated workspaces — both subscribed to the same SQLite twin over a Server-Sent Events stream, so gate/zone status updates push to the UI in real time instead of being polled.

---

## System Architecture

```text
               +-------------------------------------------+
               |             React Frontend (Vite)          |
               |   Landing (demo auth) -> Fan Portal /       |
               |   Staff Portal (sidebar workspaces)         |
               +--------------------+----------------------+
                                    |
                    REST HTTP Requests + SSE streams
                                    v
+-----------------------------------+-----------------------------------+
|                            FastAPI Backend                            |
|                                                                       |
|  +--------------------+   +-----------------------+   +------------+  |
|  |     Rate Limiter   |   |   Groq Orchestrator   |   | RAG Engine |  |
|  |  (Token/IP Bucket) |   |    (Tool Caller)      |   |  (FAISS)   |  |
|  +---------+----------+   +-----------+-----------+   +-----+------+  |
|            |                          |                     |         |
|            |                          |                     |         |
|            v                          v                     v         |
|  +--------------------+   +-----------+-----------+   +-----+------+  |
|  |   Stadium Status   |   |   Python Tools:       |   | Stadium    |  |
|  |   & Alerts REST    |   |   - get_route()       |   | Facts      |  |
|  |   API Endpoints    |   |   - get_crowd_density()|  | JSON DB    |  |
|  +---------+----------+   |   - get_gate_status() |   +------------+  |
|            |              +-----------+-----------+                   |
|            |                          |                               |
+------------+--------------------------+-------------------------------+
             |                          |
             | SQLite Queries           | SQLite Queries
             v                          v
+---------------------------------------+-------------------------------+
|                       SQLite Digital Twin                             |
|         (Simulated Crowd Density Background dynamics Thread)          |
+-----------------------------------------------------------------------+
```

### Components

1. **Vite/React Frontend**:
   - **Landing & Auth**: A bento-grid marketing landing page (solid-color icon tiles, subtle glassmorphism via a shared `.glass-panel` treatment, [Lucide](https://lucide.dev) icons throughout — no emoji) with a guided, multi-step onboarding wizard whose in-progress draft persists to `sessionStorage`; entry is gated by a demo `test`/`test` login — the fan side needs no backend account, while the staff side exchanges the passcode for a real signed JWT via the staff-auth endpoint.
   - **Fan Portal**: Sidebar workspace with a Live Stadium Map (SSE-fed gate/zone status plus accessible route rendering), a Stats view (player and team stats with radar-chart comparisons), My Ticket, Match Schedule (fixtures and knockout bracket), a "Getting Here" transit view (live line crowding, next departures, GenAI departure advisory, CO2-savings nudges), Profile (incl. dietary preference), and Settings (accessibility toggles) — plus a floating multilingual chat widget with voice input/output.
   - **Staff Portal**: Sidebar workspace with Live Crowd View, Live Alerts, the Operations Copilot panel, a Stadium Map view, a Data History view (see below), and a dedicated Staff Chat, all behind passcode-gated JWT auth.
   - **Session persistence**: the active workspace (fan/staff) survives a page refresh via `sessionStorage`, and an idle timer automatically logs the user out after 30 minutes of inactivity.

2. **FastAPI REST API**:
   - Clean endpoints for real-time status feeds, alerts, and LLM queries, plus a Server-Sent Events stream (`GET /api/v1/stadium/stream`) that pushes gate/zone updates to the frontend; fan and staff chat can also stream token-by-token over SSE.
   - Implements input sanitization and token/IP rate limiting.
   
3. **SQLite Digital Twin & Simulator**:
   - Holds state data for stadium gates, zones, the `nodes`/`edges` routing graph, and `transit_lines` (metro/shuttle/BRT links with live passenger loads), plus an `interaction_events` table (see **Data Collection & Privacy** below).
   - Run by a background loop that evolves crowd levels *and transit-line loads* via a momentum model to mimic live IoT sensor telemetry, recording per-zone history for the Copilot's forecasts.

4. **Dijkstra Routing Graph (routing.py)**:
   - Computes shortest paths dynamically between gates, concourses, stairs, elevators, and seating sections using a dynamic `nodes` and `edges` graph in SQLite. Features an `accessible_only` filter to construct step-free routes for limited-mobility fans.
   
5. **Groq Tool Orchestration**:
   - Automatically decides when to call Python tools to query the SQLite twin database for routing, gate status, or zone density details.
   
6. **Semantic RAG Store**:
   - Indexes static stadium details (FAQs, amenities, transit links) using `sentence-transformers` (`all-MiniLM-L6-v2`) and `FAISS` to inject context for general queries.

7. **Operations Copilot (Proactive Decision Support)**:
   - Unlike the reactive chat assistant, the Copilot continuously reads the digital twin, fits a short-horizon trend to each zone's recent density telemetry, and **forecasts congestion ~5 minutes ahead** (projected density, ETA-to-critical, and the gate feeding each zone).
   - A GenAI pass then synthesizes an executive **situation summary** and a **prioritized list of specific recommended actions** (e.g. "halt inflow at Gate 3, open overflow routing"), with a fully deterministic fallback when offline. Exposed at `GET /api/v1/staff/copilot` and surfaced as the centerpiece panel of the Staff Dashboard.
   - The twin's simulator uses a **momentum model** (slowly-varying ingress/egress pressure) rather than white noise, so trends are sustained and genuinely forecastable.
   - The report also carries a **transit-aware egress staggering plan**: the densest zones are released first in 5-minute waves, each wave routed toward the currently least-loaded transit line, with the twin's spare passengers/minute capacity and a sustainability note attached.

8. **Transit & Sustainable Travel (Transportation vertical)**:
   - `GET /api/v1/transit` (public) serves the live `transit_lines` state — per-line next-departure countdowns, crowding labels, and per-mode CO2-savings estimates — plus a cached **GenAI departure advisory** that steers fans toward the least-crowded, greenest way home (deterministic fallback offline, like every other GenAI path).
   - Surfaced in the Fan Portal as the "Getting Here" view (EN/ES/FR) and consumed by the Copilot's egress planner on the staff side.

---

## Data Collection & Privacy

The Staff Portal includes a **Data History** view (`GET /api/v1/interactions`, staff-JWT-gated) that surfaces exactly what interaction data the app collects, as a transparency/demo feature rather than a hidden analytics pipe:

- Each event is a row in the `interaction_events` SQLite table: a **random per-browser-session id** (not tied to any name, email, or login), a coarse `event_type` (`login`, `logout`, `chat_message`, `page_view`), the `view`/screen name, and a small `meta` JSON blob (e.g. message character count, selected language).
- **No raw chat message text, names, emails, or other personal identifiers are ever stored.** Logging is fire-and-forget from the frontend (`logInteraction()` in `frontend/src/lib/api.js`) and never blocks or fails the user-facing action it's attached to.
- The Data History tab renders these events plus per-type counts directly from the table, so the claim above is independently checkable rather than just asserted.

---

## Non-Functional Qualities

- **Security**: Tightened CORS (allowed origins, and methods/headers enumerated explicitly — only GET/POST with Authorization/Content-Type), a full security-header set on every response (nosniff, frame-deny, HSTS, Referrer-Policy, Permissions-Policy, and a `default-src 'none'` Content-Security-Policy on all API routes), strict Pydantic inputs validation, sanitizes HTML to prevent injections, rate-limits fan chat endpoints (5 requests per 10 seconds per IP), and reads API keys strictly via environment variables. The Staff Portal is secured with passcode-gated JWT authentication (4 hours expiration, token stored in sessionStorage) and a higher burst rate limit of 30 requests per 10 seconds per IP. The frontend additionally enforces its own 30-minute idle-timeout auto-logout independent of the JWT's own expiry.
- **Accessibility**: Built with semantic HTML (headers, buttons, main, labels), high-contrast accessibility mode, text size optimization, keyboard navigation support, and voice recognition/synthesis.
- **Testing**: Backend unit tests for API, routing graph, simulator, auth, circuit-breaker, conversation history, multilingual (French) routing, the Operations Copilot (forecast + endpoint), the transit endpoint/advisory/egress plan, and the interaction-logging endpoints; frontend component tests (Vitest + React Testing Library) for the map, fan chat/prompt-chips, the transit view, and staff Copilot panel; plus an automated eval script verifying 15 bilingual/tool-calling prompts. CI runs the full suite on every push.
- **Latency**: Staff operational queries return in a single LLM round-trip — the structured tool result is rendered deterministically instead of paying for a second "phrasing" call — while fan replies keep an LLM pass for natural, language-matched prose. Both fan and staff chat additionally support SSE streaming, so replies render token-by-token instead of waiting on the full response.

---

## Setup & Running Instructions

### Prerequisites
- Node.js & npm (v20+)
- Python 3.10+
- A valid `GROQ_API_KEY` (Optional. If not supplied, the backend falls back to Mock Mode matching queries, executing database tools, and serving RAG content).

### Environment Configuration
1. Copy the template `.env.example` file to `.env`:
   ```bash
   cp .env.example .env
   ```
2. Open `.env` and fill in your `GROQ_API_KEY` (optional) and other settings.

### 1. Install & Run Backend
1. Open a terminal in the root directory:
   ```bash
   pip install -r backend/requirements.txt
   ```
2. Run the FastAPI development server:
   ```bash
   uvicorn backend.app.main:app --reload --port 8000
   ```

### 2. Install & Run Frontend
1. Open another terminal in the `frontend` folder:
   ```bash
   npm install
   npm run dev
   ```
2. Access the application in your browser at `http://localhost:5173`.

### 3. Run Tests
- Run backend unit tests:
  ```bash
  pytest tests/
  ```
- Run frontend component tests:
  ```bash
  cd frontend && npm test
  ```
- Run LLM evaluation prompts:
  ```bash
  python tests/eval_script.py
  ```

---

## Assumptions Made

- **Simulated telemetry, real logic.** With no access to a live stadium's IoT sensors, crowd density is generated by an in-process simulator (momentum-based). The forecasting, routing, alerting, and decision logic are production-shaped and would work unchanged against a real sensor feed — only the data source would swap.
- **Single seeded venue.** One representative stadium is modeled (5 zones, 4 gates, and a concourse/section routing graph), seeded automatically on first run. The schema and graph generalize to other venues without code changes.
- **Static facts are curated.** The RAG knowledge base (`backend/data/stadium_facts.json`) is a hand-authored, representative set of stadium information (gates, transit, dining, accessibility, rules, family services, sustainability) rather than a live CMS feed.
- **Language scope.** English, Spanish, and French are first-class (UI, voice, and offline mock). The live LLM will still respond in other languages it is addressed in; only the offline fallback and UI chrome are limited to these three.
- **GenAI provider is optional.** Groq is the live LLM. If `GROQ_API_KEY` is absent, rate-limited, or unreachable, the system transparently falls back to deterministic mock responses, offline RAG, and rule-based alerts/Copilot — so the demo never hard-fails.
- **Demo-grade auth.** The landing page uses a hardcoded `test`/`test` credential gate for a fast hackathon login flow. On the fan side this is UI-only (no backend account system); on the staff side it still exchanges the shared passcode for a real signed JWT via the existing staff-auth endpoint, so protected staff APIs stay properly gated. Production would integrate real identity (SSO/role-based access) end-to-end; the code refuses to boot in `ENV=production` with default/weak secrets.
- **Single-process deployment.** The digital-twin simulator and in-memory rate limiter assume one backend process for the demo (see scaling notes below).

---

## Known Limitations for Scaling

### Rate Limiting
The current `IPBasedRateLimiter` implementation is entirely **in-memory** and **per-process** (stored inside a Python dictionary on the running FastAPI application instance). 
While this is optimal and highly efficient for local development, hackathon demos, or single-process testing, it has the following known limitations at scale:
*   **Worker Process Isolation:** In a multi-worker production environment (e.g. uvicorn with `--workers` or running behind Gunicorn), each worker process maintains its own independent in-memory rate limiter dictionary. A client's requests would be routed across workers, effectively multiplying their rate limit threshold by the number of active worker processes.
*   **Multi-Instance Deployment:** If the backend is scaled horizontally across multiple servers or container pods (e.g. in Kubernetes), the rate limiter state is not shared, rendering the rate limiting inconsistent.

### Recommended Mitigation
For production-grade deployments, this in-memory rate limiter should be replaced with a distributed rate-limiting solution:
*   **SlowAPI:** Integrate `slowapi`, a FastAPI port of `limits` that provides decorator-based rate limiting.
*   **Redis Backend:** Configure SlowAPI (or a custom middleware) to store rate limit counters in a shared **Redis** instance. This ensures that rate-limit states are synchronized in real-time across all worker processes and horizontal container instances.
