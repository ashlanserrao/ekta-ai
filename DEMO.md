# 60-Second Judge Quickstart & Demo Guide

Follow these instructions to launch both backend and frontend applications, view live features, and try specific prompts.

---

## 🚀 60-Second Quickstart

### 1. Run the Backend
From the project root (`PromptWars`), run the following command to start the FastAPI server:
```bash
uvicorn backend.app.main:app --reload --port 8000
```
*(The database `stadium_twin.db` is initialized automatically. To start fresh, you can safely delete it; it will be regenerated on the next request or run).*

### 2. Run the Frontend
Open a new terminal window or tab, navigate to the `frontend` folder, and launch the Vite development server:
```bash
cd frontend
npm install
npm run dev
```
Open your browser to [http://localhost:5173](http://localhost:5173).

---

## 💬 Example Prompts to Copy-Paste

Test the features immediately inside the web interface:

### 📢 Fan Assistant Tab (Multilingual + Accessible Routing + RAG Context)
Try pasting these exact messages into the Fan Assistant chat box:

1. **Multilingual (Spanish) Query**:
   ```text
   ¿Dónde están los baños accesibles?
   ```
   *Expected Response:* Responds in Spanish listing accessible sections (104, 112, 205, etc.) using built-in translation RAG facts.

2. **Accessible Routing Query**:
   ```text
   How do I get from Gate 2 to Section 204 with a wheelchair?
   ```
   *Expected Response:* Triggers the `get_route` tool, returns a step-free path utilizing the East elevator block, and updates the interactive map.

3. **General Stadium RAG Fact**:
   ```text
   Where is the Lost and Found office?
   ```
   *Expected Response:* Answers that the Lost and Found is located in Concourse B, Room 204, drawing directly from the stadium guidelines database.

---

### 📊 Staff Dashboard Tab (Operational Intelligence & Real-time Twin Queries)
Switch to the **Staff Dashboard** view in the top navigation and query the staff intelligence portal:

1. **Crowd Capacity Operational Query**:
   ```text
   What is the crowd density at Zone-C?
   ```
   *Expected Response:* Automatically invokes `get_crowd_density` on the SQLite database, checks capacity (90%), and formats a structured operational brief.

2. **Gate Live Status Query**:
   ```text
   Is Gate 2 open or closed right now?
   ```
   *Expected Response:* Calls the `get_gate_status` tool and outputs a detailed list of gate states and congestion levels.

---

## 🏗️ Architecture at a Glance
- **SQLite Digital Twin**: Holds the real-time truth database for stadium zones, gates, and nodes. An active simulation thread oscillates crowd levels to mimic IoT sensors.
- **FastAPI Backend Router**: Orchestrates responses, parses system parameters, sanitizes inputs, and handles rate limiting.
- **Gemini SDK Orchestrator**: Uses function calling to map user intentions dynamically to Python operations (Dijkstra routing, twin database queries).
- **Vite & React Frontend**: Combines an interactive SVG map renderer, Fan Voice Assistant, and live Staff Monitoring console.

*(For a comprehensive layout diagram and additional options, refer to the main [README.md](file:///h:/PromptWars/README.md) file).*

---

## 💾 Database Operations
- **`stadium_twin.db`**: This SQLite database is pre-seeded with nodes, zones, gates, and routes.
- **Regeneration**: You can delete `stadium_twin.db` at any time to clean up or reset simulation state. It will be recreated and re-seeded automatically by `init_db()` upon starting the FastAPI application.

---

## 🔒 Security & Demo Limitations Note
- **Staff Portal Authentication**: The Staff Dashboard and staff chat endpoints do not require authentication or rate limiting in this version. This is a deliberate demo design decision to ensure judges can easily evaluate operational intelligence and mock workflows without managing staff credentials or encountering rate limit blockages.
