# SimCity AI — Autonomous Digital Twin for Policy Testing

An autonomous multi-agent system that creates a living digital twin of **Kochi, India** to simulate, test, and optimize public policy decisions before real-world implementation.

## Architecture

```
User Input (Policy Description)
        │
        ▼
┌─────────────────────────────────────┐
│     LangGraph Multi-Agent Pipeline  │
│                                     │
│  1. Data Ingestion Agent            │  ← OpenStreetMap via OSMnx
│  2. Simulation Engine Agent         │  ← NetworkX traffic model
│  3. Citizen Proxy Agent             │  ← Claude LLM (5 demographics)
│  4. Policy Testing Agent            │  ← Claude LLM + graph mutation
│  5. Impact Analysis Agent           │  ← Quantified before/after metrics
│  6. Recommendation Agent            │  ← Claude LLM policy report
└─────────────────────────────────────┘
        │
        ▼
FastAPI + SSE → Next.js Dashboard
```

## Tech Stack

| Component                 | Technology                           |
| ------------------------- | ------------------------------------ |
| Multi-agent orchestration | LangGraph                            |
| LLM                       | Anthropic Claude (claude-sonnet-4-6) |
| City data                 | OSMnx (OpenStreetMap)                |
| Traffic simulation        | NetworkX                             |
| Backend API               | FastAPI + Server-Sent Events         |
| Frontend                  | Next.js 14 + Tailwind CSS            |
| Map                       | Leaflet.js                           |

## Quick Start

### 1. Clone & configure environment

```bash
cp .env.example backend/.env
# Edit backend/.env and add your ANTHROPIC_API_KEY
```

### 2. Start the backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

The first run will fetch Kochi's road network from OpenStreetMap (~30 seconds). Subsequent runs use the local cache.

### 3. Start the frontend

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000)

## Policy Scenarios (Demo Presets)

| Preset                 | Type          | Description                                               |
| ---------------------- | ------------- | --------------------------------------------------------- |
| Pedestrianize MG Road  | Road Closure  | Convert Mahatma Gandhi Road to car-free pedestrian zone   |
| Add BRT on NH-66       | New Route     | Bus Rapid Transit corridor from Edappally to Tripunithura |
| AI Signal Optimization | Signal Timing | Adaptive signals at 15 key intersections                  |
| Expand Water Taxi      | Transit Add   | 8 new ferry routes across Vembanad backwaters             |

## How It Works

1. **Enter a policy** — select a preset or describe any traffic/mobility policy in plain English
2. **Watch agents run** — 6 agents execute sequentially with real-time status updates via SSE
3. **See the impact** — color-coded map shows before/after congestion levels
4. **Read the report** — Claude generates a structured Go/No-Go policy recommendation

## Application Images

![Application Screenshot 1](image_1.png)
![Application Screenshot 2](image_2.png)
![Application Screenshot 3](Image_3.png)
![Application Screenshot 4](image_4.png)

## API Endpoints

| Method | Endpoint                    | Description                        |
| ------ | --------------------------- | ---------------------------------- |
| `GET`  | `/api/city/kochi`           | Kochi road network as GeoJSON      |
| `GET`  | `/api/city/kochi/metrics`   | Baseline traffic metrics           |
| `GET`  | `/api/presets`              | Pre-built policy presets           |
| `POST` | `/api/simulate`             | Start simulation, returns `job_id` |
| `GET`  | `/api/simulate/{id}/stream` | SSE stream of agent updates        |
| `GET`  | `/api/simulate/{id}/result` | Final simulation result            |

## Project Structure

```
simcity-ai/
├── backend/
│   ├── agents/          # 6 LangGraph agent nodes
│   ├── core/            # City model, state schema
│   ├── workflow/        # LangGraph graph definition
│   ├── api/             # FastAPI routes + SSE
│   ├── data/            # Cached OSM graph (auto-generated)
│   └── main.py
├── frontend/
│   ├── app/             # Next.js App Router pages
│   ├── components/      # UI components
│   └── lib/             # API client + TypeScript types
└── .env.example
```
