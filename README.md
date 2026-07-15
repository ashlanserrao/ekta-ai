# EktaAI — GenAI Stadium Operations Twin (FIFA World Cup 2026)

EktaAI is a GenAI-powered stadium operations assistant designed for the FIFA World Cup 2026. Built with a FastAPI backend and a Vite/React frontend, the system is designed to solve real-world challenges across navigation, crowd dynamics, accessibility, multilingual fan engagement, and staff decision support.

---

## System Architecture

```text
               +-------------------------------------------+
               |             React Frontend                |
               |  (Fan Assistant & Staff Operations View)  |
               +--------------------+----------------------+
                                    |
                           REST HTTP Requests
                                    v
+-----------------------------------+-----------------------------------+
|                            FastAPI Backend                            |
|                                                                       |
|  +--------------------+   +-----------------------+   +------------+  |
|  |     Rate Limiter   |   |   Gemini Orchestrator |   | RAG Engine |  |
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
   - **Fan Assistant**: Multilingual chat widget with voice support (Web Speech API input/output text-to-speech) and an interactive SVG layout mapping real-time route directions and gate congestion.
   - **Staff Dashboard**: A digital twin status monitoring control panel, presenting real-time zone crowd volumes, auto-generated operations alerts, and a chat window querying congestion mitigations.
   
2. **FastAPI REST API**:
   - Clean endpoints for real-time status feeds, alerts, and LLM queries.
   - Implements input sanitization and token/IP rate limiting.
   
3. **SQLite Digital Twin & Simulator**:
   - Holds state data for stadium gates, zones, and routes.
   - Run by an scheduling background loop fluctuating crowd levels to mimic live IoT sensor telemetry.

4. **Dijkstra Routing Graph (routing.py)**:
   - Computes shortest paths dynamically between gates, concourses, stairs, elevators, and seating sections using a dynamic `nodes` and `edges` graph in SQLite. Features an `accessible_only` filter to construct step-free routes for limited-mobility fans.
   
5. **Gemini Tool Orchestration**:
   - Automatically decides when to call Python tools to query the SQLite twin database for routing, gate status, or zone density details.
   
6. **Semantic RAG Store**:
   - Indexes static stadium details (FAQs, amenities, transit links) using `sentence-transformers` (`all-MiniLM-L6-v2`) and `FAISS` to inject context for general queries.

---

## Non-Functional Qualities

- **Security**: Tightened CORS configurations restricting origins to `http://localhost:5173`, strict Pydantic inputs validation, sanitizes HTML to prevent injections, rate-limits chat endpoints (5 requests per 10 seconds per IP), and reads API keys strictly via environment variables.
- **Accessibility**: Built with semantic HTML (headers, buttons, main, labels), high-contrast accessibility mode, text size optimization, keyboard navigation support, and voice recognition/synthesis.
- **Testing**: Includes full unit tests for API, routing graph, and simulator routines, plus an automated eval script verifying 15 bilingual/tool-calling prompts.

---

## Setup & Running Instructions

### Prerequisites
- Node.js & npm (v18+)
- Python 3.10+
- A valid `GEMINI_API_KEY` (Optional. If not supplied, the backend falls back to Mock Mode matching queries, executing database tools, and serving RAG content).

### Environment Configuration
1. Copy the template `.env.example` file to `.env`:
   ```bash
   cp .env.example .env
   ```
2. Open `.env` and fill in your `GEMINI_API_KEY` (optional) and other settings.

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
- Run unit tests:
  ```bash
  pytest tests/
  ```
- Run LLM evaluation prompts:
  ```bash
  python tests/eval_script.py
  ```
