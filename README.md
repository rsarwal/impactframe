# ImpactFrame 🏥

**AI-powered Resource Allocation Intelligence for Community Health Clinics**

ImpactFrame is a multi-agent system built with Google ADK that ingests messy, 
multi-format health program data and produces evidence-based budget allocation 
recommendations — with conflicts flagged for human review.

## Architecture

```
Inputs → Ingestion Agent → Evidence Extraction Agent → Conflict Detection Agent
      → Confidence Scoring Agent → Allocation Agent → Web UI Report
```

## Quick Start

1. Clone the repo
2. `pip install -r requirements.txt`
3. Copy `.env.example` to `.env` and add your Google API key
4. `python mcp_server/server.py` (in one terminal)
5. `python web/app.py` (in another terminal)
6. Open http://localhost:5000

## Key Concepts Demonstrated
- Multi-agent system (Google ADK)
- MCP Server (local data access layer)
- Security features (input sanitization, no PII logging)
- Deployability (Flask web server, environment-based config)
