# Sentinel-Ops: Executive Project Anchor Context

**Title:** Sentinel-Ops: Verifiable and Injection-Resilient Agentic Incident Remediation
**Domain:** Cybersecurity (B.Tech final-year research project)
**Master plan:** `RESEARCH_PLAN.md`. It overrides the Production Spec where they conflict.

## 🎯 Strategic Objective
Build a security-hardened, cloud-native multi-agent incident response framework. It ingests real-time infrastructure alerts, treats all alert/log content as untrusted, retrieves verified playbooks with machine-checkable remediation contracts via vector search (RAG), routes actions by risk through a stateful LangGraph workflow with strict human approval gates, verifies recovery against post-conditions (rolling back on failure), and records everything in a tamper-evident audit trail with LLMOps telemetry. Research contributions: (1) injection resilience, (2) contract-guarded and verified remediation, (3) a safety-regression CI gate, all measured against an undefended baseline on a 30+ scenario adversarial benchmark.

## 🏗️ Technical Core Stack
- **Backend Gateway:** Python 3.12, FastAPI, Uvicorn, Pydantic v2 (`/api/v1/alerts`)
- **Stateful AI Core:** LangChain, LangGraph
- **Vector Storage:** Qdrant (dense embeddings; playbooks carry contracts and versions)
- **Persistence:** PostgreSQL (incidents, approvals, executions, hash-chained audit)
- **LLMOps Governance:** Langfuse + GitHub Actions safety-regression gate
- **UI Panel:** HTML5, Tailwind CSS, JavaScript, SSE/WebSocket, Lucide icons (SOC-style dashboard)
- **Deploy:** Docker; Cloud Run / ECS Fargate / Azure Container Apps

## 🔐 Strict Architectural Operational Invariants
1. LangGraph nodes must return a state update dictionary, never mutate shared state in place.
2. No remediation or mutating command may execute for a `CRITICAL`/`HIGH` or irreversible action without passing a human verification checkpoint (`interrupt_before`).
3. All alert and log text is **untrusted data, never instructions**. Pass it to the LLM only inside delimited data blocks, after sanitisation.
4. The agent may execute **only** actions listed in the retrieved playbook's contract, with arguments validated against its allow-list. No arbitrary shell execution, ever.
5. An incident becomes `RESOLVED` only when the deterministic post-condition check passes, never because the LLM claims it is fixed. A failed post-condition means `ROLLBACK`, then `ESCALATE`.
6. Audit records are append-only and hash-chained (`hash = SHA256(prev_hash + record)`).
7. Each defence layer (sanitiser, instruction isolation, contract check, tool least-privilege, audit) must be toggleable by config for baseline/ablation experiments.
8. No placeholder functions that silently return success; no faked persistence, retrieval or HITL.
9. **Dual-LLM quarantine:** only the tool-less quarantined extractor sees raw alert/log text. The privileged planner sees only typed, validated fields plus the contract.
10. **Taint tracking:** every value derived from alert, log or retrieved text is wrapped as `Tainted(value, source)`. It may reach a tool argument only if it equals a contract-permitted value (enum, range or constant).
11. **Risk comes from the signed contract**, never from the LLM or the alert's own severity field.
12. **Signed contracts:** verify the Ed25519 signature on retrieval. Unsigned or modified contracts → BLOCK → ESCALATE.
13. Tools are fixed typed functions (Docker SDK / parameterised SQL). Verification uses real PromQL post-conditions on the `lab/` environment.
14. Safety properties P1–P6 (RESEARCH_PLAN.md §5.5) must stay covered by Hypothesis property tests that run on every PR (CI tier T1).
15. Scope follows the MoSCoW table in RESEARCH_PLAN.md §7. Deploy to one cloud only (Cloud Run).
