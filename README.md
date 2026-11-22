# Sentinel-Ops
**Verifiable and Injection-Resilient Agentic Incident Remediation** · Domain: Cybersecurity · B.Tech final-year research project

Sentinel-Ops is a cloud-native, security-hardened multi-agent incident response framework. A LangGraph agent fleet triages infrastructure alerts, retrieves verified playbooks via RAG over Qdrant, and executes only **contract-permitted**, **human-approved** remediations. Every fix is **verified against post-conditions**, with automatic rollback if recovery is not proven, and every action is recorded in a **tamper-evident audit trail**.

## Research contributions
1. **Injection-resilient pipeline:** layered defences against prompt and command injection hidden in logs and alerts, measured on an adversarial benchmark.
2. **Contract-guarded remediation:** each playbook is a machine-checkable contract (preconditions, allowed actions, post-conditions, rollback). Recovery is verified, not assumed.
3. **Safety-regression CI gate:** a benchmark of 30+ attack and failure scenarios runs in GitHub Actions. Merges are blocked if the approval-bypass rate is above 0% or if safety metrics get worse.

## Stack
Python 3.12 · FastAPI · LangGraph/LangChain · Qdrant · PostgreSQL · Langfuse · HTML/Tailwind/JS dashboard · Docker · GitHub Actions · Cloud Run / ECS Fargate / Azure Container Apps

## Documents
- [RESEARCH_PLAN.md](RESEARCH_PLAN.md): **master plan** (brief, threat model, contracts, evaluation, phases, timeline, acceptance criteria)
- `Sentinel-Ops Production Implementation Specification.docx`: base system spec (RESEARCH_PLAN.md overrides it where they conflict)
- [GEMINI_CONTEXT.md](GEMINI_CONTEXT.md): AI-assistant anchor context and invariants
- [MLops_dev.txt](MLops_dev.txt): week-by-week timeline
- [docs/SESSION_CONTEXT_phase0-1.md](docs/SESSION_CONTEXT_phase0-1.md): what was built in Phase 0/1

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
```

### Dependencies (PostgreSQL + Qdrant)

With Docker: `docker compose up -d` starts both with the credentials in `.env.example`.

With a native PostgreSQL install instead, create the role and database once (as the `postgres` superuser):

```sql
CREATE ROLE sentinel LOGIN PASSWORD 'sentinel';
CREATE DATABASE sentinel_ops OWNER sentinel;
```

Then apply the schema:

```bash
alembic upgrade head
```

### Start

```bash
python -m uvicorn app.main:app --reload
python scripts/generate_alerts.py --scenario database_disk --count 1
pytest                          # uses a temporary SQLite DB; no services needed
```

- Dashboard: http://127.0.0.1:8000/dashboard
- Liveness: `/health` · Readiness (checks PostgreSQL + Qdrant): `/ready`
- `/ingest` returns 503 when PostgreSQL is unreachable, so no alert is silently dropped.
