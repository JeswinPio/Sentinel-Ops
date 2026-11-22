from typing import TypedDict, Optional, Any
from langgraph.graph import StateGraph, START, END
from langgraph.types import interrupt
from langgraph.checkpoint.memory import InMemorySaver


class AgentState(TypedDict, total=False):
    active_incident: Optional[dict]
    severity: str
    playbook: Optional[dict]
    mitigation_plan: Optional[str]
    risk_level: str
    status: str
    current_node: str
    human_approval: Optional[str]
    messages: list[str]


# ============================================================
# NODE 1: INGEST
# ============================================================

def ingest_node(state: AgentState) -> dict:
    """
    Reads the incident already enriched by FastAPI (app/main.py).
    """

    incident = state.get("active_incident")

    if not incident:
        return {
            "current_node": "INGEST_NODE",
            "status": "NO_INCIDENT",
            "messages": ["No active incident supplied to workflow."]
        }

    return {
        "active_incident": incident,
        "severity": incident.get("severity", "INFO").upper(),
        "current_node": "INGEST_NODE",
        "status": "INGESTED",
        "messages": [
            f"Incident received from {incident.get('service_name', 'unknown service')}"
        ]
    }


# ============================================================
# NODE 2: TRIAGE
# ============================================================

def triage_node(state: AgentState) -> dict:
    severity = state.get("severity", "INFO").upper()

    if severity == "CRITICAL":
        risk = "HIGH"
    elif severity == "WARNING":
        risk = "MEDIUM"
    else:
        risk = "LOW"

    return {
        "severity": severity,
        "risk_level": risk,
        "current_node": "TRIAGE_NODE",
        "status": "TRIAGED",
        "messages": [
            f"Triage classified incident as {severity}",
            f"Risk level determined as {risk}"
        ]
    }


# ============================================================
# NODE 3: ANALYSIS
# ============================================================

def analysis_node(state: AgentState) -> dict:
    incident = state.get("active_incident") or {}

    playbook = {
        "topic": incident.get("playbook_topic", "Triage Needed"),
        "solution": incident.get(
            "solution",
            "No mitigation playbook available."
        )
    }

    severity = state.get("severity", "INFO")

    if severity == "CRITICAL":
        mitigation_plan = (
            "CRITICAL mitigation requires human approval before execution."
        )
    elif severity == "WARNING":
        mitigation_plan = (
            "Low-risk simulated mitigation may execute autonomously."
        )
    else:
        mitigation_plan = (
            "No infrastructure mutation required."
        )

    return {
        "playbook": playbook,
        "mitigation_plan": mitigation_plan,
        "current_node": "ANALYSIS_NODE",
        "status": "ANALYZED",
        "messages": [
            f"Playbook selected: {playbook['topic']}",
            "Analysis completed."
        ]
    }


# ============================================================
# ROUTER
# ============================================================

def risk_router(state: AgentState) -> str:
    severity = state.get("severity", "INFO").upper()

    if severity == "CRITICAL":
        return "critical"

    if severity == "WARNING":
        return "warning"

    return "info"


# ============================================================
# INFO PATH
# ============================================================

def safe_resolution_node(state: AgentState) -> dict:
    return {
        "current_node": "SAFE_RESOLUTION_NODE",
        "status": "RESOLVED",
        "messages": [
            "INFO incident resolved without infrastructure mutation."
        ]
    }


# ============================================================
# WARNING PATH
# ============================================================

def autonomous_low_risk_node(state: AgentState) -> dict:
    return {
        "current_node": "AUTONOMOUS_LOW_RISK_NODE",
        "status": "EXECUTED_SIMULATION",
        "messages": [
            "WARNING classified as low risk.",
            "Simulated low-risk mitigation executed."
        ]
    }


# ============================================================
# CRITICAL HITL CHECKPOINT
# ============================================================

def hitl_checkpoint_node(state: AgentState) -> dict:
    """
    This node executes ONLY AFTER the interrupt_before checkpoint
    has been passed.

    IMPORTANT:
    The graph is compiled with:

        interrupt_before=["HITL_CHECKPOINT"]

    Therefore this function is NEVER reached automatically for a
    CRITICAL incident.

    Human approval is written into the checkpointed state before
    resuming the graph.
    """

    approval = state.get("human_approval")

    if approval == "APPROVED":
        return {
            "current_node": "HITL_CHECKPOINT",
            "status": "APPROVED",
            "messages": [
                "Human approval received.",
                "CRITICAL execution is now authorized."
            ]
        }

    if approval == "DENIED":
        return {
            "current_node": "HITL_CHECKPOINT",
            "status": "DENIED",
            "messages": [
                "Human approval denied.",
                "CRITICAL mitigation will not execute."
            ]
        }

    return {
        "current_node": "HITL_CHECKPOINT",
        "status": "WAITING_FOR_APPROVAL",
        "messages": [
            "Waiting for human approval."
        ]
    }


# ============================================================
# AFTER HITL ROUTER
# ============================================================

def approval_router(state: AgentState) -> str:
    approval = state.get("human_approval")

    if approval == "APPROVED":
        return "approved"

    return "denied"


# ============================================================
# SIMULATED EXECUTION
# ============================================================

def simulated_execution_node(state: AgentState) -> dict:
    """
    SAFE DEMO ONLY.

    This does NOT execute database/cloud mutation commands.
    """

    return {
        "current_node": "SIMULATED_EXECUTION_NODE",
        "status": "EXECUTED_SIMULATION",
        "messages": [
            "Human approved CRITICAL mitigation.",
            "Simulated execution completed.",
            "No real infrastructure mutation was performed."
        ]
    }


# ============================================================
# DENIED / ESCALATION
# ============================================================

def escalation_node(state: AgentState) -> dict:
    return {
        "current_node": "ESCALATION_NODE",
        "status": "ESCALATED",
        "messages": [
            "Human rejected CRITICAL mitigation.",
            "Incident escalated without executing mutation."
        ]
    }


# ============================================================
# GRAPH CONSTRUCTION
# ============================================================

def build_graph():

    builder = StateGraph(AgentState)

    # Nodes
    builder.add_node("INGEST_NODE", ingest_node)
    builder.add_node("TRIAGE_NODE", triage_node)
    builder.add_node("ANALYSIS_NODE", analysis_node)

    builder.add_node("SAFE_RESOLUTION_NODE", safe_resolution_node)
    builder.add_node(
        "AUTONOMOUS_LOW_RISK_NODE",
        autonomous_low_risk_node
    )

    builder.add_node(
        "HITL_CHECKPOINT",
        hitl_checkpoint_node
    )

    builder.add_node(
        "SIMULATED_EXECUTION_NODE",
        simulated_execution_node
    )

    builder.add_node(
        "ESCALATION_NODE",
        escalation_node
    )

    # Main pipeline
    builder.add_edge(START, "INGEST_NODE")
    builder.add_edge("INGEST_NODE", "TRIAGE_NODE")
    builder.add_edge("TRIAGE_NODE", "ANALYSIS_NODE")

    # Risk router
    builder.add_conditional_edges(
        "ANALYSIS_NODE",
        risk_router,
        {
            "info": "SAFE_RESOLUTION_NODE",
            "warning": "AUTONOMOUS_LOW_RISK_NODE",
            "critical": "HITL_CHECKPOINT",
        }
    )

    # Normal paths
    builder.add_edge("SAFE_RESOLUTION_NODE", END)
    builder.add_edge("AUTONOMOUS_LOW_RISK_NODE", END)

    # HITL paths
    builder.add_conditional_edges(
        "HITL_CHECKPOINT",
        approval_router,
        {
            "approved": "SIMULATED_EXECUTION_NODE",
            "denied": "ESCALATION_NODE",
        }
    )

    builder.add_edge("SIMULATED_EXECUTION_NODE", END)
    builder.add_edge("ESCALATION_NODE", END)

    # Persistent checkpoint memory
    checkpointer = InMemorySaver()

    # REAL HITL MECHANISM
    graph = builder.compile(
        checkpointer=checkpointer,
        interrupt_before=["HITL_CHECKPOINT"]
    )

    return graph


# ============================================================
# PUBLIC GRAPH INSTANCE
# ============================================================

graph = build_graph()


# ============================================================
# DEMO HELPERS
# ============================================================

def start_incident(incident: dict, thread_id: str = "sentinel-demo"):
    """
    Start a workflow.

    For CRITICAL incidents this returns with the graph paused
    immediately before HITL_CHECKPOINT.
    """

    config = {
        "configurable": {
            "thread_id": thread_id
        }
    }

    result = graph.invoke(
        {
            "active_incident": incident,
            "messages": []
        },
        config=config
    )

    return result, config


def approve_incident(
    thread_id: str = "sentinel-demo"
):
    """
    Resume a paused CRITICAL workflow after human approval.
    """

    config = {
        "configurable": {
            "thread_id": thread_id
        }
    }

    graph.update_state(
        config,
        {
            "human_approval": "APPROVED"
        }
    )

    return graph.invoke(
        None,
        config=config
    )


def deny_incident(
    thread_id: str = "sentinel-demo"
):
    """
    Resume a paused CRITICAL workflow after human rejection.
    """

    config = {
        "configurable": {
            "thread_id": thread_id
        }
    }

    graph.update_state(
        config,
        {
            "human_approval": "DENIED"
        }
    )

    return graph.invoke(
        None,
        config=config
    )


# ============================================================
# DIRECT TEST
# ============================================================

if __name__ == "__main__":

    incident = {
        "timestamp": "2026-08-24T12:00:00",
        "service_name": "postgresql-db-01",
        "severity": "CRITICAL",
        "message": "disk_utilization_percent > 95%",
        "infrastructure_id": "postgresql-db-01",
        "playbook_topic": "Database Disk Capacity Exhaustion",
        "solution": (
            "1. Check database disk usage and identify the largest log files.\n"
            "2. Verify that the identified logs are safe to remove before deletion.\n"
            "3. Remove only eligible old log files to recover disk space.\n"
            "4. Recheck disk utilization and confirm the database has returned to a safe level."
        )
    }

    print("\n" + "=" * 70)
    print("SENTINEL-OPS LANGGRAPH HITL TEST")
    print("=" * 70)

    result, config = start_incident(
        incident,
        thread_id="critical-demo"
    )

    print("\nGRAPH PAUSED:")
    print(result)

    print("\nHuman approval is now required.")
    print("Run approve_incident() or deny_incident() to continue.")