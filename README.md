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
