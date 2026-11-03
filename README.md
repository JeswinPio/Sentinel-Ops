# Sentinel-Ops
Build a self-healing, cloud-native operations platform where a stateful agent fleet (LangGraph) triages system alerts, queries standard troubleshooting manuals (RAG over Vector DB), and executes human-approved mitigations with complete cost, trace, and evaluation guardrails.

## Layout

```
app/
  main.py            FastAPI gateway (/ingest, /logs, /dashboard, /ui)
  config.py          Environment-based settings (see .env.example)
  agents/graph.py    LangGraph workflow with interrupt_before HITL checkpoint
  rag/mock_store.py  Keyword playbook store (replaced by Qdrant in Phase 2)
frontend/            Static control-center UI served at /ui
scripts/
  generate_alerts.py     Mock alert stream
  agent_supervisor_cli.py  Terminal supervisor demo
tests/               pytest suite (unit, agent, api)
```

## Run locally

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows; use source .venv/bin/activate elsewhere
pip install -r requirements-dev.txt
copy .env.example .env          # then fill in values

python -m uvicorn app.main:app --reload
python scripts/generate_alerts.py --scenario database_disk --count 1
pytest
```

Dashboard: http://127.0.0.1:8000/dashboard
